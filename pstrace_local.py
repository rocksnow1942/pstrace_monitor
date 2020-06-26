import time
import os
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pathlib import Path
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import matplotlib
from collections import deque
from itertools import zip_longest
import json
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
import re
from myfit import myfitpeak
import numpy as np

matplotlib.use('TKAgg')

def timeseries_to_axis(timeseries):
    "convert datetime series to time series in minutes"
    return [(d-timeseries[0]).seconds/60  for d in timeseries ]


def plot_experiment(dataset,interval,savepath):
    """
    plot data into grid axes, 
    dataset should be the format of mongodb datapack.
    {
        name:,
        desc:,
        exp:,
        dtype: 'covid=trace',
        data:{
            time: [datetime(),...]
            rawdata: [[v,a]...]
            fit:[ {'fx': , 'fy': , 'pc': , 'pv': , 'err': 0}...]
        }
    }
    interval: the interval for timepoints to be plotted. 
    savepath: folder to save the file. 
    """
    name = dataset['name']
    times = timeseries_to_axis(dataset['data']['time'][::interval])
    raw = dataset['data']['rawdata'][::interval]
    fit = dataset['data']['fit'][::interval]
    
    rows = int(np.ceil(np.sqrt(len(times))))
    cols = int( np.ceil( len(times) / rows) )
    
    fig = Figure(figsize=( 1.5*cols, 1.5*rows ))
    axes = fig.subplots(rows,cols)
    axes = np.ravel([axes]) 

    for ax in axes:
        ax.axis('off')
    
    for t,r,f,ax in zip(times,raw,fit,axes):
        x1,x2 = f['fx']
        y1,y2 = f['fy']
        peakvoltage = f['pv']
        peakcurrent = f['pc']
        k = (y2-y1)/(x2-x1)
        b = -k*x2 + y2
        baselineatpeak = k* f['pv'] + b
        v,a = r
        color = 'r' if f['err'] else 'b'
        ax.plot(v, a,  f['fx'], f['fy'],
                [peakvoltage, peakvoltage], [baselineatpeak, baselineatpeak+peakcurrent])
        ax.set_title("{:.1f}m {:.2f}nA".format(t, peakcurrent),
                     fontsize=10, color=color)
        ax.axis('on') 
        
    fig.set_tight_layout(True)
    
    tosave = os.path.join(savepath, f"{name}_i{interval}.png") 
    while os.path.exists(tosave):
        tosave = tosave.rsplit('.',1)[0]+'+'+'.png'
    fig.savefig(tosave)



class PSS_Handler(PatternMatchingEventHandler):
    """
    watchdog event listner.
    """

    def __init__(self, logger):
        super().__init__(patterns=["*100hz*.csv", ], ignore_patterns=["*~$*", "*Conflict*"],
                         ignore_directories=False, case_sensitive=True)
        self.logger = logger
        self.info = logger.info

    def on_created(self, event):
        self.info(f"Watchdog: Create {event.src_path}")
        self.logger.create(event.src_path)

    def on_deleted(self, event):
        pass

    def on_modified(self, event):
        pass

    def on_moved(self, event):
        pass


class PSS_Logger():
    def debug(self,x): return 0
    def info(self,x): return 0
    def warning(self,x): return 0
    def error(self,x): return 0
    def critical(self,x): return 0

    def __init__(self, target_folder="", ploter=None, loglevel='INFO'):
        "target_folder: the folder to watch, "
        self.pstraces = {}
        self.files = []
        self.target_folder = target_folder
        # self.ploter = ploter
        self.queue = deque()
        self.added = []
        self.load_pstraces()

        level = getattr(logging, loglevel.upper(), 20)
        logger = logging.getLogger('Monitor')
        logger.setLevel(level)
        fh = RotatingFileHandler(os.path.join(
            target_folder, 'pss_monitor_log.log'), maxBytes=10240000000, backupCount=2)
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s: %(message)s', datefmt='%Y/%m/%d %I:%M:%S %p'
        ))
        logger.addHandler(fh)
        self.logger = logger

        def wrapper(func):
            def wrap(msg):
                print(msg)
                return func(msg)
            return wrap

        _log_level = ['debug', 'info', 'warning', 'error', 'critical']
        _log_index = _log_level.index(loglevel.lower())

        for i in _log_level:
            setattr(self, i, getattr(self.logger, i))

        if PRINT_MESSAGES:  # if print message, only print for info above that level.
            for i in _log_level[_log_index:]:
                setattr(self, i, wrapper(getattr(self.logger, i)))

    def load_pstraces(self):
        folder = self.target_folder
        pstrace = os.path.join(folder, 'pstracelog_DONT_TOUCH.json')
        if os.path.exists(pstrace):
            with open(pstrace, 'rt') as f:
                alldata = json.load(f)
                
            self.files = alldata['files']
            data = alldata['pstraces']
            for _, chaneldata in data.items():
                for entry in chaneldata:
                    entry['data']['time'] = [ datetime.strptime(i, '%Y-%m-%d %H:%M:%S') for i in  entry['data']['time']]
            self.pstraces = data

    def save_pstraces(self):
        pstrace = os.path.join(
            self.target_folder, 'pstracelog_DONT_TOUCH.json')
        tosave = {'pstraces':self.pstraces,'files':self.files}
        with open(pstrace, 'wt') as f:
            json.dump(tosave, f, separators=(',', ':'),
                      default=lambda x: datetime.strftime(x, '%Y-%m-%d %H:%M:%S'))

    def init(self):
        pattern = re.compile('100hz.*\.csv')
        for root, dirs, files in os.walk(self.target_folder):
            files = [os.path.join(root, file)
                     for file in files if pattern.match(file)]
            files = sorted(files, key=lambda x: os.path.getmtime(x))
            for file in files:
                if file not in self.files:
                    self.add(file)

    def create(self, file):
        "add file to queue with time stamp"
        self.queue.append((datetime.now(), file))
        self.debug(f'Create - {file} queue length: {len(self.queue)}.')
        return

    def sync(self, delay=3):
        "sync files in queue, delay seconds in delay"
        while self.queue:
            t, f = self.queue[0]
            currentdelay = (datetime.now()-t).seconds
            if currentdelay >= delay:
                t, f = self.queue.popleft()
                self.debug(f'Add - {f} delayed: {currentdelay} seconds.')
                self.add(f)
                    
            else:
                return

    def finalsync(self,):
        "sync all files in queue"
        while self.queue:
            self.sync()
            time.sleep(0.1)

    def parse_file(self,file):
        """
        specific way to parse the file and return information:
        folder is the chanel, 
        v, a, is voltage and current, 
        time, is the datetime returned
        """
         # self.debug(f"PS traces: {str(self.pstraces)}")
        filepath = Path(file)

        chanel = filepath.parts[-2]

        with open(file, 'rt', encoding='utf-16') as f:
            data = f.read()

        # if this csv is irrelevant
        if data[0:15] != 'Date and time:,':
            return None

        data = data.strip().split('\n')
        timestring = data[4].split(',')[1]
        time = datetime.strptime(timestring, '%Y-%m-%d %H:%M:%S')
 
        voltage = [float(i.split(',')[0]) for i in data[6:-1]]
        amp = [float(i.split(',')[1]) for i in data[6:-1]]
        return chanel, voltage, amp, time

    def add(self, file):
        """
        add file locally format:
        {  
            chanel: [
                {
                    name:,
                    desc:,
                    exp:,
                    dtype: 'covid=trace',
                    data:{
                        time: [datetime(),...]
                        rawdata: [[v,a]...]
                        fit:[ {'fx': , 'fy': , 'pc': , 'pv': , 'err': 0}...]
                    }
                }
            ]
            ...
        }
        """
        parseresult = self.parse_file(file)
        if not parseresult:
            return 
        chanel, voltage,amp,t = parseresult 
        fitres = myfitpeak(voltage,amp)
        self.files.append(file)
        if chanel not in self.pstraces:
            self.pstraces[chanel] = [{
                'name': f"{chanel}-1",
                'desc':'',
                'exp':'',
                'dtype': 'covid-trace',
                'data':{
                    'time':[t],
                    'rawdata':[[voltage,amp]],
                    'fit':[fitres],
                }
            }]
            self.debug(f"Channel {chanel} new data: time: {t}, file:{file}")
            return 
        else:
            # insert the data in to datas
            for dataset in self.pstraces[chanel][::-1]:
                if (t - dataset['data']['time'][-1]).seconds > MAX_SCAN_GAP:
                    # if the t is much larger than the latest dataset in pstrace: add to a new dataset and break. 
                    new_name = f'{chanel}-{int(dataset["name"].split("-")[1])+1}'
                    self.pstraces[chanel].append({
                        'name': new_name,
                        'desc': '',
                        'exp': '',
                        'dtype': 'covid-trace',
                        'data': {
                            'time': [t],
                            'rawdata': [[voltage, amp]],
                            'fit': [fitres],
                        }
                    })
                    self.debug(
                        f"Channel {chanel} new data: time: {t}, file:{file}")
                    return  
                elif (t - dataset['data']['time'][0]).seconds > -10: 
                    # if the timepoint is later than first time point in the dataset, insert. 
                    for k,i in enumerate(dataset['data']['time'][::-1]):
                        if (t - i).seconds>=0:
                            # need to insert
                            break
                    currentlength = len(dataset['data']['time'])
                    index = currentlength - k
                    dataset['data']['time'].insert( index , t)
                    dataset['data']['rawdata'].insert(index,[voltage,amp])
                    dataset['data']['fit'].insert(index,fitres)
                    self.debug(
                        f"Channel {chanel} append {index}th data, last-length{currentlength}: time: {t}, file:{file}")
                    return 
        self.error(f'Data cannot be added: channel: {chanel}, time: {t}, file: {file}')
        self.files.pop()
        return 1
                
    def write_csv(self):
        datatowrite = []
        timetowrite = []
        
        folder = Path(self.target_folder) 
        
        csvname = os.path.join(self.target_folder, f'{folder.stem}_data_summary.csv')

        chanels = list(self.pstraces.keys())
        chanels.sort()

        for chanel in chanels:
            dataset = self.pstraces[chanel]
            for exp in dataset:
                name = exp['name']
                time = timeseries_to_axis(exp['data']['time'])
                signal = [i['pc'] for i in exp['data']['fit']]
                timetowrite.append(
                    ['Time', "minutes"] + [str(i) for i in time])
                datatowrite.append(
                    [chanel, name] + [str(i) for i in signal])
        if timetowrite:
            maxtime = max(timetowrite, key=lambda x: len(x))
            with open(csvname, 'wt') as f:
                for i in zip_longest(*([maxtime]+datatowrite), fillvalue=""):
                    f.write(','.join(i))
                    f.write('\n')

    def plot_trace(self, interval, ):
        "plot all traces"
        savepath = os.path.join(self.target_folder,'curve_fit_output')
        for c,datasets in self.pstraces.items():
            for dataset in datasets:
                name = dataset['name'] 
                tosave = os.path.join(savepath, f"{name}_i{interval}.png") 
                if not os.path.exists(tosave):
                    plot_experiment(dataset, interval, savepath)
                    yield name
                    
class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.target_folder = TARGET_FOLDER
        self.pack()
        self.create_menus()
        self.create_widgets()
        self.create_figure()
        self.MONITORING = False
        self.logger = None

    def create_menus(self):
        menu = tk.Menu(self.master)
        self.master.config(menu=menu)
        filemenu = tk.Menu(menu)
        menu.add_cascade(label='File', menu=filemenu)
        filemenu.add_command(label='New Monitor Folder',
                             command=self.new_folder)
        filemenu.add_command(label='Quit', command=self.master.destroy)

        # plot menu
        plotmenu = tk.Menu(menu)
        menu.add_cascade(label='Plot', menu=plotmenu)
        plotmenu.add_command(label='Plot Curve Fit', command= self.plot_curve_fit)



    def new_folder(self):
        global TARGET_FOLDER
        self.target_folder = tk.filedialog.askdirectory(
            initialdir=str(Path(self.target_folder).parent))
        self.folderinput.delete(0, tk.END)
        self.folderinput.insert(tk.END, self.target_folder)
        TARGET_FOLDER = self.target_folder
        save_settings()

    def plot_curve_fit(self):
        interval = tk.simpledialog.askinteger("Input","wowo testing",
                    parent=self.master,minvalue=1,maxvalue=100,initialvalue=10)
        if interval and self.logger and (not self.MONITORING):
            for m in self.logger.plot_trace(interval):
                self.msg.set(f"Plotting {m}......") 
            self.msg.set('Plotting curve fit done.')

    def create_figure(self):
        global Matlabfig
        canvas = FigureCanvasTkAgg(Matlabfig, self)
        canvas.draw()
        tkwidget = canvas.get_tk_widget()
        tkwidget.grid(column=0, row=2, columnspan=6, rowspan=3, sticky=tk.E)
        # tkwidget.pack(side=tk.TOP, fill=tk.BOTH, expand=False)

    def create_widgets(self):
        self.master.title("PSS monitor")
        self.pack(fill=tk.BOTH, expand=True)

        # self.grid_columnconfigure()
        self.folderbutton = tk.Button(
            self, text='Folder', command=self.new_folder)
        self.folderbutton.grid(row=0, column=0, padx=10, pady=10, sticky=tk.E)
        self.folderinput = tk.Entry(self, width=50)
        self.folderinput.insert(tk.END, self.target_folder)
        self.folderinput.grid(row=0, column=1, sticky=tk.W)

        self.msg = tk.StringVar()
        self.msg.set('PSS MONITOR READY')
        self.msglabel = tk.Label(self, textvariable=self.msg, bg='cyan')
        # self.msg.config(bg='green', width=50)
        self.msglabel.grid(row=6, column=0, columnspan=10)
        # self.msg.pack()

        self.start_monitor_button = tk.Button(
            self, text="Start Monitor", command=self.start_monitor)
        self.start_monitor_button.grid(row=0, column=2,)
        # self.start_monitor_button.pack(side="top")

        self.stop_monitor_button = tk.Button(self, text="Stop Monitor", fg="red", state='disabled',
                                             command=self.stop_monitor)
        self.stop_monitor_button.grid(row=0, column=3, )
        # self.stop_monitor_button.pack(side='bottom')

        self.save_csv_button = tk.Button(self, text="Save CSV", fg="green", state='disabled',
                                         command=self.save_csv)
        self.save_csv_button.grid(row=0, column=4, )

    def save_csv(self):
        self.msg.set(f"Saving CSV .... Please wait!")
        self.logger.write_csv()
        self.msg.set(f"CSV Saved To {self.logger.target_folder}!")

    def stop_monitor(self):
        # self.appPipe.send('stop')
        self.msg.set(f"Stopping Monitor Process .... Please wait!")
        self.msglabel.config(bg='red')
        self.MONITORING = False

    def start_monitor(self, ):
        self.target_folder = self.folderinput.get()

        if not os.path.exists(self.target_folder):
            self.msg.set(f"'{self.target_folder}' is not a valid folder.")
            self.msglabel.config(bg='red')
            return

        self.start_monitor_button['state'] = 'disabled'
        self.folderinput['state'] = 'disabled'
        self.stop_monitor_button['state'] = 'normal'
        self.save_csv_button['state'] = 'disabled'
        self.folderbutton['state'] = 'disabled'

        self.msg.set(f"Starting......")
        self.msglabel.config(bg='yellow')

        observer = Observer()
        logger = PSS_Logger(
            target_folder=self.target_folder, loglevel=LOG_LEVEL)
        logger.info('*****PSS monitor started*****')
        logger.info('****Start initiation.****')
        logger.init()
        logger.info('****Init Done.****')
        observer.schedule(PSS_Handler(logger=logger),
                          self.target_folder, recursive=True)
        observer.start()
        logger.info(f'****Monitor Started <{self.target_folder}>.****')
        self.msg.set(f"Monitoring......")
        self.logger = logger
        self.observer = observer
        self.MONITORING = True
        self.after(1000, self.syncLogger)

    def syncLogger(self):
         
        if self.MONITORING:
            self.logger.sync()
            self.after(1000, self.syncLogger)
        else:
            try:
                self.logger.info("Stopping monitor...")
                self.logger.finalsync()
                self.logger.save_pstraces()
                self.logger.info("Logger saved pstrace record.")
                self.observer.stop()
                self.observer.join()
                self.logger.info("Monitor stopped.")
            except Exception as e:
                self.logger.error(f'STOP monitor error {e}')
                
            self.logger.info('Monitor Stopped.')
            self.start_monitor_button['state'] = 'normal'
            self.folderinput['state'] = 'normal'
            self.save_csv_button['state'] = 'normal'
            self.stop_monitor_button['state'] = 'disabled'
            self.folderbutton['state'] = 'normal'
            self.msg.set(f"Monitoring Stopped!")
            self.msglabel.config(bg='cyan')


# load savings
def load_settings():
    pp = (Path(__file__).parent / '.pssconfig').absolute()
    if os.path.exists(pp):
        results = json.load(open(pp, 'rt'))
    else:
        results = {}
    return results


def save_settings():
    data = {
        "TARGET_FOLDER": TARGET_FOLDER,
        'MAX_SCAN_GAP': MAX_SCAN_GAP,
        'LOG_LEVEL': LOG_LEVEL,
        'PRINT_MESSAGES': PRINT_MESSAGES,
    }
    pp = (Path(__file__).parent / '.pssconfig').absolute()
    with open(pp, 'wt') as f:
        json.dump(data, f, indent=2)
        # f.write(self.target_folder)


# default settings
MAX_SCAN_GAP = 8  # mas interval to be considerred as two traces in seconds
PRINT_MESSAGES = True  # whether print message
LOG_LEVEL = 'INFO'
TARGET_FOLDER = str((Path(__file__).parent / '.pssconfig').absolute())

settings = load_settings()
for k, i in settings.items():
    globals()[k] = i


global Matlabfig
matplotlib.rc('font', **{'size': 8})
Matlabfig = Figure(figsize=(8, 3), dpi=100)
axes = Matlabfig.subplots(2, 4, )
axes = [i for j in axes for i in j]
Matlabfig.set_tight_layout(True)



root = tk.Tk()
root.geometry('840x400')
app = Application(master=root)


def animate_figure(s):
    logger = app.logger 
    if logger and app.MONITORING:
        chanels = list(logger.pstraces.keys())
        chanels.sort()
        for chanel, ax in zip(chanels , axes): 
            data = logger.pstraces[chanel][-1]['data']
            c = [i['pc'] for i in data['fit']]
            s = timeseries_to_axis(data['time'])
            lasttime = data['time'][-1] 
            if (datetime.now() - lasttime).seconds > MAX_SCAN_GAP:
                color = 'grey'
            else:
                color = 'green'

            ax.clear()
            ax.plot(c, s, color=color, marker='o', linestyle='',
                    markersize=3, markerfacecolor='w')
            ax.set_title(f'{k}-{chanel}',color = color)
           

ani = animation.FuncAnimation(Matlabfig, animate_figure, interval=5000)
app.mainloop()

import time
import os
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pathlib import Path
from datetime import datetime
import requests
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
matplotlib.use('TKAgg')

class PSS_Handler(PatternMatchingEventHandler):
    """
    watchdog event listner.
    """
    def __init__(self, logger):
        super().__init__(patterns=["*100hz*.csv",], ignore_patterns=["*~$*", "*Conflict*"],
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
    debug= lambda x: 0
    info= lambda x: 0
    warning=lambda x: 0
    error = lambda x: 0
    critical = lambda x: 0
    def __init__(self, target_folder="", ploter=None, loglevel='INFO'):
        "target_folder: the folder to watch, "
        self.pstraces = {}
        self.target_folder = target_folder
        # self.ploter = ploter
        self.queue = deque()
        self.plotqueue = deque(maxlen=12)
        self.added = []
        self.load_pstraces()

        level = getattr(logging, loglevel.upper(), 20)
        logger = logging.getLogger('Monitor')
        logger.setLevel(level)
        fh = RotatingFileHandler(os.path.join(target_folder,'pss_monitor_log.log'), maxBytes=10240000000, backupCount=2)
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
            setattr(self, i,getattr(self.logger, i))

        if PRINT_MESSAGES: # if print message, only print for info above that level.
            for i in _log_level[_log_index:]:
                setattr(self, i, wrapper(getattr(self.logger, i)))

    def load_pstraces(self):
        folder = self.target_folder
        pstrace = os.path.join(folder,'pstracelog_DONT_TOUCH.json')
        if os.path.exists(pstrace):
            with open(pstrace,'rt') as f:
                data = json.load(f)
            for k,i in data.items():
                for entry in i:
                    entry[2] = datetime.strptime(entry[2],'%Y-%m-%d %H:%M:%S')
            self.pstraces = data

    def save_pstraces(self):
        pstrace = os.path.join(self.target_folder,'pstracelog_DONT_TOUCH.json')
        data = {}
        for k,i in self.pstraces.items():
            data[k] = [[e[0],e[1],datetime.strftime(e[2],'%Y-%m-%d %H:%M:%S'), e[3]] for e in i]

        with open(pstrace,'wt') as f:
            json.dump(data,f,indent=2)



    def init(self):
        pattern = re.compile('100hz.*\.csv')
        addedfiles = [i[0] for k,j in self.pstraces.items() for i in j]
        for root,dirs,files in os.walk(self.target_folder):
            files = [os.path.join(root,file) for file in files if pattern.match(file)]
            files = sorted(files,key = lambda x: os.path.getmtime(x))
            for file in files:
                if file not in addedfiles:
                    self.create(file)

    def create(self,file):
        "add file to queue with time stamp"
        self.queue.append((datetime.now(),file))
        self.debug(f'Create - {file} queue length: {len(self.queue)}.')
        return

    def sync(self,delay=10):
        "sync files in queue, delay seconds in delay"
        while self.queue:
            t,f = self.queue[0]
            currentdelay = (datetime.now()-t).seconds
            if  currentdelay >=delay:
                t,f = self.queue.popleft()
                self.debug(f'Add - {f} delayed: {currentdelay} seconds.')
                self.add(f)
            else:
                return
    def finalsync(self,):
        "sync all files in queue"
        while self.queue:
            self.sync()
            time.sleep(0.1)

    def add(self,file):
        """
        self.pstrace is a log for tracking syncing.
        self.pstrace: {
            folder: [
                [file, amskey, time, thistimepoint],
                [file, amskey, time, thistimepoint],
                ...
            ]
        }
        folder is the sub folder name of monitoring parent folder.
        file is the file path,
        amskey is the ams key in plojo
        time is the time stamp of this pss file.
        thistimepoint is the time point of this pss in the whole trace in minutes.
        """
        # self.debug(f"PS traces: {str(self.pstraces)}")
        filepath = Path(file)
        folder = str(filepath.parent)

        if folder not in self.pstraces:
            self.pstraces[folder] = []
            # strucutre: [[file1, amskey, datetime, timepoint]]

        psmethod = file[0:-1] + 'method'
        if self.pstraces[folder]:
            lasttime = self.pstraces[folder][-1][2]
        else:
            lasttime = datetime(2000,1,1)

        chanel = filepath.parts[-2]


        with open(file,'rt',encoding='utf-16') as f:
            data = f.read()

        # if this csv is irrelevant
        if data[0:15] != 'Date and time:,':
            return

        data = data.strip().split('\n')
        timestring = data[4].split(',')[1]
        time = datetime.strptime(timestring, '%Y-%m-%d %H:%M:%S')

        # read pss data
        # with open(file,'rt') as f:
        #     pssdata =f.read()

        # data = pssdata.strip().split('\n')
        voltage = [float(i.split(',')[0]) for i in data[6:-1]]
        amp =  [float(i.split(',')[1]) for i in data[6:-1]]

        data_tosend = dict(potential=voltage, amp=amp,project = PROJECT_FOLDER,
                           filename=file, date=timestring, chanel=chanel)

        # determine if the data is a new scan or is continued from pervious and handle it.
        if (time - lasttime).seconds > MAX_SCAN_GAP:
            self.debug(f'MAX_SCAN_GAP reached, {(time - lasttime).seconds} seconds.')
            thistimepoint = 0
            amskey = ""
        else:
            thistimepoint = self.pstraces[folder][-1][3] + (time-lasttime).seconds/60
            amskey = self.pstraces[folder][-1][1]
            self.debug(f'Continuous from previous scan {amskey}, after {thistimepoint} seconds.')

        data_tosend.update(time=thistimepoint,key=amskey )

        try:
            response = requests.post(url=SERVER_POST_URL, json=data_tosend)
            if response.status_code == 200:
                result = response.text
                self.debug(f'Response {result} datapack: Filename: {data_tosend["filename"]} Key: {data_tosend.get("key",None)}')
            else:
                self.error(f"Post Data Error - respons code: {response.status_code}, datapacket: {data_tosend}")
                return
        except Exception as e:
            self.error(f"Error - {e}")
            return

        result = result.split('-')
        # depend on the response from server, handle result differently

        if result[0] == 'Add': # if it is starting a new trace
            amskey = result[1]

            self.info(f'Added - {result[1]} {file}')
        elif result[0] == 'OK':  # if it's continue from a known trace.
            self.info(f"OK - {amskey} {file}")
        else:
            self.error(f"API-Error - {'-'.join(result)}")
            return

        self.pstraces[folder].append( [file, amskey, time, thistimepoint ] )
        if (amskey,chanel) not in self.plotqueue:
            self.plotqueue.appendleft((amskey, chanel))

    def write_csv(self):
        datatowrite = []
        timetowrite = []
        csvname = os.path.join( self.target_folder , 'data_summary.csv')
        for folder,item in self.pstraces.items():
            keys = list(set([i[1] for i in item]))
            keys.sort(key=lambda x: int(x.replace('ams','')))
            self.debug(f"Write CSV for {folder}, keys={','.join(keys)}")
            try:
                # only read the data that was generated at least 10 seconds ago.
                response = requests.get(
                    url=SERVER_GET_URL, json={'keys':keys })
                if response.status_code == 200:
                    result = response.json()
                else:
                    raise ValueError(f"Error Get data - respons code: {response.status_code}, datapacket: {keys}")

                for key in keys:
                    if key in result:
                        time = result[key].get('concentration', None)
                        signal = result[key].get('signal', None)
                        name = result[key].get('name','No Name')
                        if time and signal:
                            self.debug(f"write time and signal for {key}, time length = {len(time)}, signal length = {len(signal)}")
                            timetowrite.append(['Time', "minutes"] + [str(i) for i in time])
                            datatowrite.append([key + '_signal',name] + [str(i) for i in signal])
                        else:
                            self.warning(
                                f"No time or signal in {key},time={time},signal ={signal}")
                    else:
                        self.error(f"Error Write CSV - Key missing {key}")

            except Exception as e:
                self.error(f"Error Write CSV- {e}")


        maxtime = max(timetowrite,key=lambda x:len(x))
        with open(csvname, 'wt') as f:
            for i in zip_longest(*([maxtime]+datatowrite),fillvalue=""):
                f.write(','.join(i))
                f.write('\n')

a = max([1,2,3])

matplotlib.rc('font',**{'size':8})
f = Figure(figsize=(8, 5), dpi=100)
axes = f.subplots(3, 4, )
axes = [i for j in axes for i in j]
f.set_tight_layout(True)

global TODRAW
TODRAW = [ ]

def animate_figure(s):
    global TODRAW
    data = requests.get(url=SERVER_GET_URL, json={
                        'keys': [i[0] for i in TODRAW]}).json()
    for (k, chanel), ax in zip(TODRAW, axes):
        ax.clear()
        c = data.get(k, {}).get('concentration', [0])
        s = data.get(k, {}).get('signal', [0])
        ax.plot(c, s, color='b', marker='o', linestyle='',
                markersize=3, markerfacecolor='w')
        ax.set_title(f'{k}-{chanel}')
        # ax.set_xlabel('Time/min',fontsize=6)
        # ax.set_ylabel('Signal/nA', fontsize=6)



def load_settings():
    pp = (Path(__file__).parent / '.pssconfig').absolute()
    if os.path.exists(pp):
        results = json.load(open(pp, 'rt'))
    else:
        results = {}
    return results

def save_settings():
    data = {
        "TARGET_FOLDER":TARGET_FOLDER ,
        'MAX_SCAN_GAP' : MAX_SCAN_GAP,
        'LOG_LEVEL': LOG_LEVEL,
        'PROJECT_FOLDER': PROJECT_FOLDER,
        'SERVER_GET_URL': SERVER_GET_URL,
        'SERVER_POST_URL': SERVER_POST_URL,
    }
    pp = (Path(__file__).parent / '.pssconfig').absolute()
    with open(pp,'wt') as f:
        json.dump(data,f,indent=2)
        # f.write(self.target_folder)



# default settings
MAX_SCAN_GAP = 8  # mas interval to be considerred as two traces in seconds
PRINT_MESSAGES = True  # whether print message
LOG_LEVEL = 'INFO'
PROJECT_FOLDER = 'Echem_Scan'
SERVER_POST_URL = 'http://127.0.0.1:5000/api/add_echem_pstrace'
SERVER_GET_URL = "http://127.0.0.1:5000/api/get_plojo_data"
TARGET_FOLDER = str((Path(__file__).parent / '.pssconfig').absolute())


settings = load_settings()
for k,i in settings.items():
    globals()[k] = i


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.target_folder = TARGET_FOLDER
        self.pack()
        self.create_menus()
        self.create_widgets()
        self.create_figure()
        self.MONITORING = True


    def create_menus(self):
        menu = tk.Menu(self.master)
        self.master.config(menu=menu)
        filemenu = tk.Menu(menu)
        menu.add_cascade(label='File',menu=filemenu)
        filemenu.add_command(label='New Monitor Folder',command=self.new_folder)
        filemenu.add_command(label='Quit',command=self.master.destroy)

    def new_folder(self):
        global TARGET_FOLDER
        self.target_folder = tk.filedialog.askdirectory(
            initialdir=str(Path(self.target_folder).parent))
        self.folderinput.delete(0,tk.END)
        self.folderinput.insert(tk.END,self.target_folder)
        TARGET_FOLDER = self.target_folder
        save_settings()

    def create_figure(self):
        canvas = FigureCanvasTkAgg(f, self)
        canvas.draw()
        tkwidget = canvas.get_tk_widget()
        tkwidget.grid(column=0,row=2,columnspan=6,rowspan=4,sticky=tk.E)
        # tkwidget.pack(side=tk.TOP, fill=tk.BOTH, expand=False)

    def create_widgets(self):
        self.master.title("PSS monitor")
        self.pack(fill=tk.BOTH,expand=True)

        # self.grid_columnconfigure()
        self.folderbutton = tk.Button(self,text='Folder',command=self.new_folder)
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

        self.start_monitor_button = tk.Button(self, text="Start Monitor", command=self.start_monitor)
        self.start_monitor_button.grid(row=0,column=2,)
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
        logger = PSS_Logger(target_folder=self.target_folder, loglevel=LOG_LEVEL)
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
        global TODRAW
        if self.MONITORING:
            TODRAW = self.logger.plotqueue
            self.logger.sync()
            self.after(1000,self.syncLogger)
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

# 
# root = tk.Tk()
# root.geometry('840x600')
# app = Application(master=root)
# ani = animation.FuncAnimation(f, animate_figure, interval=5000)
# app.mainloop()

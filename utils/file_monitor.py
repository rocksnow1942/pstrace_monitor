from watchdog.events import PatternMatchingEventHandler
from collections import deque
import logging
from logging.handlers import RotatingFileHandler
from utils.myfit import myfitpeak
import re
import json
import pickle
import os
from datetime import datetime
import time
from itertools import zip_longest
from utils._util import timeseries_to_axis, plot_experiment,calc_peak_baseline
from pathlib import Path
from watchdog.observers import Observer
import time
from compress_pickle import dump, load

MAX_PSTRACE_SAVE_GAP = 901 # 15minutes

class PlotDeque(deque):
    def add(self,x):
        if x not in self:
            self.appendleft(x)

class PSS_Handler(PatternMatchingEventHandler):
    """
    watchdog event listner.
    """

    def __init__(self, logger):
        super().__init__(patterns=["*100hz*.csv", ], ignore_patterns=["*~$*", "*Conflict*"],
                         ignore_directories=False, case_sensitive=True)
        self.logger = logger

    def on_created(self, event):
        self.logger.debug(f"Watchdog: Create {event.src_path}")
        self.logger.create(event.src_path)

    def on_deleted(self, event):
        pass

    def on_modified(self, event):
        pass

    def on_moved(self, event):
        pass

class PSS_Logger():
    def debug(self, x): return 0
    def info(self, x): return 0
    def warning(self, x): return 0
    def error(self, x): return 0
    def critical(self, x): return 0

    def __init__(self, TARGET_FOLDER="", LOG_LEVEL='INFO', PRINT_MESSAGES=True, MAX_SCAN_GAP=30, **kwargs):
        "target_folder: the folder to watch, "
        self.pstraces = {}
        self.MAX_SCAN_GAP = MAX_SCAN_GAP
        self.plotdeque = PlotDeque(maxlen=12)
        self.files = []
        self.target_folder = TARGET_FOLDER
        self.folderstem = Path(self.target_folder).stem
        # file location for pstraces file.
        self.pstraces_loc = os.path.join(self.target_folder,f"{self.folderstem}_Monitor_pstraces.picklez")
        self.queue = deque()
        self.LOG_LEVEL = LOG_LEVEL
        self.PRINT_MESSAGES = PRINT_MESSAGES
        self.load_pstraces()
        self.init_logger()


    def init_logger(self,logfileName = 'pss_monitor_log.log'):
        PRINT_MESSAGES = self.PRINT_MESSAGES
        LOG_LEVEL = self.LOG_LEVEL
        level = getattr(logging, LOG_LEVEL.upper(), 20)
        logger = logging.getLogger('Monitor')
        logger.setLevel(level)
        # fh = RotatingFileHandler(os.path.join(
        #     TARGET_FOLDER, 'pss_monitor_log.log'), maxBytes=10240000000, backupCount=2)
        fh = RotatingFileHandler(Path(__file__).parent.parent / logfileName, maxBytes=10240000000, backupCount=2)
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
        _log_index = _log_level.index(LOG_LEVEL.lower())

        for i in _log_level:
            setattr(self, i, getattr(self.logger, i))

        if PRINT_MESSAGES:  # if print message, only print for info above that level.
            for i in _log_level[_log_index:]:
                setattr(self, i, wrapper(getattr(self.logger, i)))

    def load_pstraces_JSON(self):
        pstrace = self.pstraces_loc
        if os.path.exists(pstrace):
            with open(pstrace, 'rt') as f:
                alldata = json.load(f)

            self.files = alldata['files']
            data = alldata['pstraces']
            for _, chaneldata in data.items():
                for entry in chaneldata:
                    entry['data']['time'] = [datetime.strptime(
                        i, '%Y-%m-%d %H:%M:%S') for i in entry['data']['time']]
            self.pstraces = data

    def load_pstraces(self):
        pstrace = self.pstraces_loc
        if os.path.exists(pstrace):
            with open(pstrace, 'rb') as f:
                # alldata = pickle.load(f)
                alldata = load(f,compression='gzip')

            self.files = alldata['files']
            self.pstraces = alldata['pstraces']

    def save_pstraces(self):
        pstrace = self.pstraces_loc
        tosave = {'pstraces': self.pstraces, 'files': self.files}
        with open(pstrace, 'wb') as f:
            # pickle.dump(tosave, f)
            dump(tosave, f,compression='gzip')

    def save_pstraces_JSON(self):
        pstrace = os.path.join(
            self.target_folder, 'pstracelog_DONT_TOUCH_local.json')
        tosave = {'pstraces': self.pstraces, 'files': self.files}
        with open(pstrace, 'wt') as f:
            json.dump(tosave, f, separators=(',', ':'),
                      default=lambda x: datetime.strftime(x, '%Y-%m-%d %H:%M:%S'))

    def init(self):
        pattern = re.compile(r'100hz.*\.csv')
        queuefiles = [i[1] for i in self.queue]
        t = datetime(2010,1,1)
        for root, _, files in os.walk(self.target_folder):
            files = [os.path.join(root, file)
                     for file in files if pattern.match(file)]
            files = sorted(files, key=lambda x: os.path.getmtime(x) , reverse=True)
            for file in files:
                if (file not in self.files) and (file not in queuefiles) :
                    self.queue.appendleft( ( t ,file) )
                    self.debug(f'Initiate add files - {file} queue length: {len(self.queue)}.')
                    # self.create(file,datetime(2010,1,1))
    def create(self, file,t=None):
        "add file to queue with time stamp"
        t = t or datetime.now()
        self.queue.append((t, file))
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

    def parse_file(self, file):
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
        
        #  if voltage is from positive to negative reverse amp.
        reverseAmp = -1 if voltage[-1]< voltage[0] else 1
        amp = [float(i.split(',')[1]) * reverseAmp for i in data[6:-1]]
        return chanel, voltage, amp, time

    def timesub(self,t1,t2):
        ""
        return (t1-t2).days * 86400 + (t1-t2).seconds

    def add(self, file):
        """
        add file locally format:
        {
            chanel: [
                {
                    name:,
                    desc:,
                    exp:,
                    dtype: 'covid-trace',
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
        self.files.append(file)
        if self.add_result(parseresult,file):
            return
        self.files.pop()
        return 1

    def fitData(self,vol,amp):
        return myfitpeak(vol,amp)

    def add_result(self,parseresult,file=None):
        chanel, voltage, amp, t = parseresult
        fitres = self.fitData(voltage,amp)
        if chanel not in self.pstraces:
            self.pstraces[chanel] = [{
                'name': f"{chanel}-1",
                'desc': '',
                'exp': '',
                'dtype': 'covid-trace',
                'data': {
                    'time': [t],
                    'rawdata':[[voltage, amp]],
                    'fit':[fitres],
                }
            }]
            self.plotdeque.add( ( chanel, 0 ) )
            self.debug(f"Create New Channel {chanel}, add first new data: time: {t}, file:{file}")
            return True
        else:
            # insert the data in to datas
            for dataset in self.pstraces[chanel][::-1]:
                if self.timesub(t, dataset['data']['time'][-1]) > self.MAX_SCAN_GAP:
                    # if the t is much larger than the latest dataset in pstrace: add to a new dataset and break.
                    newindex = len(self.pstraces[chanel]) + 1
                    new_name = f'{chanel}-{newindex}'
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
                    self.plotdeque.add((chanel, len(self.pstraces[chanel]) -1 ))
                    self.debug(
                        f"Channel {chanel} start a new dataset {new_name}: time: {t}, file:{file}")
                    return True
                elif self.timesub(t , dataset['data']['time'][0]) > - self.MAX_SCAN_GAP//2:
                    # if the timepoint is later than first time point in the dataset, insert.
                    for k, i in enumerate(dataset['data']['time'][::-1]):
                        if (t - i).seconds >= 0:
                            # need to insert
                            break
                    currentlength = len(dataset['data']['time'])
                    index = currentlength - k
                    dataset['data']['time'].insert(index, t)
                    dataset['data']['rawdata'].insert(index, [voltage, amp])
                    dataset['data']['fit'].insert(index, fitres)
                    self.plotdeque.add((chanel, len(self.pstraces[chanel]) -1 ))
                    self.debug(
                        f"Channel {chanel}, dataset {dataset['name']} append {index+1}th data, last-length {currentlength}: time: {t}, file:{file}")
                    return True
        self.error(
            f'Data cannot be added: channel: {chanel}, time: {t}, file: {file}')
        return False

    def write_csv(self):
        csvname = os.path.join(
            self.target_folder, f'{self.folderstem}_data_summary.csv')

        data_to_csv(self.pstraces,csvname)

    def plot_curve_fit(self, interval, ):
        "plot all traces"
        savepath = os.path.join(self.target_folder, 'curve_fit_output')
        if not os.path.exists(savepath):
            os.mkdir(savepath)
        for _, datasets in self.pstraces.items():
            for dataset in datasets:
                name = dataset['name']
                tosave = os.path.join(savepath, f"{name}_i{interval}.png")
                if not os.path.exists(tosave):
                    plot_experiment(dataset, interval, savepath)

def plot_curve_fit(target_folder,interval,pipe):
    "plot the pstraces file in target folder with interval. "
    tf = Path(target_folder)
    pstraces_loc = tf / f'{tf.stem}_pstraces.pickle'
    pstraces = None
    if pipe:
        pstraces = pipe.recv()
    else:
        if os.path.exists(pstraces_loc):
            with open(pstraces_loc, 'rb') as f:
                alldata = pickle.load(f)
            pstraces = alldata['pstraces']
    if pstraces:
        savepath =  tf / 'curve_fit_output'
        if not os.path.exists(savepath):
            os.mkdir(savepath)
        for _, datasets in pstraces.items():
            for dataset in datasets:
                name = dataset['name']
                tosave = savepath / f"{name}_i{interval}.png"
                if not os.path.exists(tosave):
                    plot_experiment(dataset, interval, tosave)

def datasets_to_csv(data,csvloc):
    datatowrite = []
    for exp in data:
        name = exp['name']
        time = timeseries_to_axis(exp['data']['time'])
        length = len(time)
        signal = [str(i['pc']) for i in exp['data']['fit']]
        avg_pv = sum(i['pv'] for i in exp['data']['fit']) / length
        avg_pbaseline =  sum(map(calc_peak_baseline,exp['data']['fit'])) / length
        datatowrite.append(
            ['P.Voltage','P.Baseline','Time'] + [str(i) for i in time])
        datatowrite.append(
            [ str(avg_pv), str(avg_pbaseline) , name] + signal)

    if datatowrite:
        # maxtime = max(timetowrite, key=lambda x: len(x))
        with open(csvloc, 'wt') as f:
            for i in zip_longest(*datatowrite, fillvalue=""):
                f.write(','.join(i))
                f.write('\n')

def datasets_to_pickle(data,pickleloc):
    t = datetime.now().strftime("%m%d:%H%ME")
    tosave = {'pstraces':{t:data}}
    with open(pickleloc, 'wb') as f:
        dump(tosave, f,compression='gzip')


def data_to_csv(pstraces, csvloc):
    "save pstraces dictionary to csv"
    datasets = []
    chanels = list(pstraces.keys())
    chanels.sort()
    for chanel in chanels:
        datasets.extend(pstraces[chanel])

    datasets_to_csv(datasets,csvloc)

def save_csv(target_folder):
    "convenient function to call in tikinter app with only folder."
    tf = Path(target_folder)
    pstraces_loc = tf / f'{tf.stem}_pstraces.pickle'
    csvname = tf / f'{tf.stem}_data_summary.csv'
    if os.path.exists(pstraces_loc):
        with open(pstraces_loc, 'rb') as f:
            alldata = pickle.load(f)
        pstraces = alldata['pstraces']
        data_to_csv(pstraces,csvname)
        return True
    else:
        return None

def StartMonitor(settings,pipe,ViewerQueue):
    observer = Observer()
    logger = PSS_Logger(**settings)
    logger.info(f"*****PSS monitor started on <{settings['TARGET_FOLDER']}>*****")
    observer.schedule(PSS_Handler(logger=logger),
                      settings['TARGET_FOLDER'], recursive=True)
    observer.start()
    logger.info('****Start initiation.****')
    logger.init()
    logger.info('****Init Done.****')
    logger.info(f"****Monitor Started on <{settings['TARGET_FOLDER']}>.****")

    lastSave = datetime.now() # to track pstrace save
    CYCLETIME = 2
    while True:
        STOP_MONITOR = False
        time.sleep(CYCLETIME)
        logger.sync()
        now = datetime.now()
        # send out plot deque and data

        # dummpy code
        # if i< 8:
        #     dummy.appendleft(dummylist[i])
        #     i+=1
        # dummpy code

        data_to_plot = [{'chanel': chanel,
                         'idx': idx,
                         'color': 'grey' if (now - logger.pstraces[chanel][idx]['data']['time'][-1]).seconds > logger.MAX_SCAN_GAP + CYCLETIME + 1 else 'green',
                         'name': logger.pstraces[chanel][idx]['name'],
                         'exp': logger.pstraces[chanel][idx]['exp'],
                         'time': timeseries_to_axis(logger.pstraces[chanel][idx]['data']['time']),
                         'pc': [i['pc'] for i in logger.pstraces[chanel][idx]['data']['fit']],
                        #  'deleted': logger.pstraces[chanel][idx].get('deleted',False)
                         } for chanel, idx in logger.plotdeque if not logger.pstraces[chanel][idx].get('deleted',False)]  # logger.plotdeque ## dummy code
        # reorder here
        data_to_plot.sort(key=lambda x: x['color']=='grey')
        while pipe.poll():
            # deal with stop or edit events.
            msg = pipe.recv()

            action = msg.pop('action')
            logger.debug(f'Received message <{action}>.')
            if action == 'stop':
                STOP_MONITOR = True
                break
            elif action=='edit':
                chanel = msg.pop('chanel')
                idx = msg.pop('idx')
                logger.pstraces[chanel][idx].update(msg)
            elif action == 'delete':
                chanel = msg['chanel']
                idx = msg['idx']
                logger.pstraces[chanel][idx]['deleted']=True
            elif action == 'senddata':
                msg.pop('pipe').put(logger.pstraces)
            elif action == 'savecsv':
                logger.write_csv()
            elif action == 'setlogger':
                for k,i in msg.items():
                    setattr(logger,k,i)
            elif action == 'sendDataToViewer':
                ViewerQueue.put({'source':'monitorMemory','pstraces':logger.pstraces})
            elif action == 'savePSTraceEdit':
                memorySave = msg['data']
                # sync data
                for channel, datasets in logger.pstraces.items():
                    modifiedDatasets = memorySave.get(channel,[])
                    for mod,ori in zip(modifiedDatasets,datasets):
                        for field in ['name','desc','exp','dtype','_uploaded','deleted']:
                            if mod.get(field,'__NonExist!') != '__NonExist!':
                                ori[field] = mod[field]

        if STOP_MONITOR:
            observer.stop()
            observer.join()
            break

        pipe.send(data_to_plot)

        # if need to save pstraces
        if (now - lastSave).seconds > MAX_PSTRACE_SAVE_GAP:
            logger.save_pstraces()
            lastSave = now


    logger.info("Stopping monitor...")
    logger.finalsync()
    logger.save_pstraces()
    logger.info("Logger saved pstrace record.")
    logger.info("Monitor stopped.")
    return 0

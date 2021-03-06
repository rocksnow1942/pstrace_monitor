import time
from datetime import datetime
from utils.file_monitor import PSS_Logger
import heapq
from utils.picoLibrary import Flush,GetResults,GetValueMatrix,openSerialPort,convert_voltage,ValConverter
from utils._util import timeseries_to_axis
import os
from threading import Thread

# TODO"
# Recover from pico error by flush and reconnect.

def timeClassFunction(attr=None,show=False):
    """
    To report the run time of a class method,
    Also set avgTime and runCount, for reporting task queue occupancy.
    """
    def decorator(func):
        def wrap(self,*args,**kwargs):
            t0 = time.perf_counter()
            res = func(self,*args,**kwargs)
            dt = time.perf_counter() - t0
            self.avgTime = (self.avgTime * min(self.runCount,4) + dt) / (min(self.runCount,4) + 1)
            self.runCount += 1
            if show:
                text = getattr(self,attr) if attr else ""
                print(f"{self.__class__.__name__} {text} took {dt:.3f}s, Last 5 average: {self.avgTime:.3f}s")
            return res
        return wrap
    return decorator


class PicoLogger(PSS_Logger):
    """
    subclassed from regular PS trace logger, excpet the following changes:
    needToSave property : to indicate if the logger was updated and need to save.
    status property: a dictionary to indicate if a channel's tatus is 'done' or 'update' or 'reported'.
    files, plotdeque is nolonger used. files is pertained because of it's used in save_pstraces
    """
    def __init__(self,port=None ,TARGET_FOLDER="", LOG_LEVEL='INFO', PRINT_MESSAGES=True, **kwargs):
        "target_folder: the folder to save files, "
        self.pstraces = {}
        self.files = []
        self.target_folder = TARGET_FOLDER
        # file location for pstraces file.
        self.pstraces_loc = os.path.join(self.target_folder,f"{datetime.now().strftime('%Y%m%d')}_Pico_{port}_pstraces.picklez")
        self.LOG_LEVEL = LOG_LEVEL
        self.PRINT_MESSAGES = PRINT_MESSAGES
        self.load_pstraces()
        self.init_logger(logfileName=f'Pico_{port}_log.log')
        self.needToSave = False
        self.status={}

    def save_pstraces(self):
        if self.needToSave:
            self.debug(f'Save pstraces picklez to {self.pstraces_loc}')
            super().save_pstraces()
        self.needToSave = False
    def add_result(self,*args,**kwargs,):
        dtype = kwargs.pop('dtype',None)
        if dtype == 'covid-trace':
            return self.add_covid_trace_result(*args,**kwargs)
        elif dtype == 'covid-trace-manualScript':
            return self.add_covid_trace_manualScript_result(*args,**kwargs)

    def add_covid_trace_manualScript_result(self,chanel,index,voltage,amp,packetName,scriptIndex,t,createNew):
        "manual script "
        self.needToSave = True
        fitres = self.fitData(voltage,amp)
        if chanel not in self.pstraces:
            self.pstraces[chanel] = []
            self.debug(f"Create New Channel {chanel}.")
        if createNew:
            newindex = len(self.pstraces[chanel]) + 1
            new_name = f'{chanel}-{newindex}-Sc{scriptIndex+1}-{packetName}'
            self.pstraces[chanel].append({
                'name': new_name,
                'desc': '',
                'exp': '',
                'dtype': 'covid-trace', #this dtype still set to covid=trace because for uploading, this is the same format.
                'data': {
                    'time': [t],
                    'rawdata': [[voltage, amp]],
                    'fit': [fitres],
                }
            })
            self.markUpdate(chanel)
            self.debug(f"Channel {chanel} start a new dataset {new_name}: time: {t}")
            return fitres
        else:
            # if the timepoint is later than first time point in the dataset, insert.
            dataset = self.pstraces[chanel][index]
            dataset['data']['time'].append(t)
            dataset['data']['rawdata'].append([voltage, amp])
            dataset['data']['fit'].append(fitres)
            self.debug(
                f"Channel {chanel}, dataset {dataset['name']} append data, time: {t}, ")
            self.markUpdate(chanel)
            return fitres
        return False


    def add_covid_trace_result(self,parseresult,count,):
        "currently, covid-trace is the default dtype. "
        self.needToSave = True
        chanel, voltage, amp, t = parseresult
        fitres = self.fitData(voltage,amp)
        if chanel not in self.pstraces:
            self.pstraces[chanel] = []
            self.debug(f"Create New Channel {chanel}.")
        # insert the data in to datas
        if count==0:
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
            self.markUpdate(chanel)
            self.debug(f"Channel {chanel} start a new dataset {new_name}: time: {t}, count:{count+1}")
            return fitres
        else:
            # if the timepoint is later than first time point in the dataset, insert.
            dataset = self.pstraces[chanel][-1]
            dataset['data']['time'].append(t)
            dataset['data']['rawdata'].append([voltage, amp])
            dataset['data']['fit'].append(fitres)
            self.debug(
                f"Channel {chanel}, dataset {dataset['name']} append {count+1}th data, time: {t}, ")
            self.markUpdate(chanel)
            return fitres
        return False
    def markUpdate(self,channel):
        self.status[channel]='update'
    def markDone(self,channel):
        self.status[channel]='done'

class TaskQueue(list):
    """

    """
    def put(self,x):
        heapq.heappush(self,x)
    def peek(self):
        return self[0]
    def get(self,):
        return heapq.heappop(self)
    def empty(self):
        return len(self)==0
    def cancelTask(self,channel):
        'remove a measurement task'
        for i,t in enumerate(self):
            if getattr(t,'channel',None) == channel:
                self[i].done()
                del self[i]
                break
        heapq.heapify(self)
    def getTask(self,channel):
        for t in self:
            if getattr(t,'channel',None) == channel:
                return t
    def nextTime(self):
        if self.empty(): return 999
        return self.peek().nextExec - time.monotonic()

    def updateTask(self,channel,method,dtype):
        "update a running Covid task on channel with new method and dtype"
        for t in self:
            if getattr(t,'channel',None) == channel:
                if t.dtype != dtype:
                    t.pipe.send({'action':'inform','msg':f"Can't update {channel} to {dtype}",'color':'red'})
                    return
                t.update(method)
                t.pipe.send({'action':'inform','msg':f"{channel} method updated.",'color':'cyan'})

    def newTask(self,msg, scheduler):
        "add a measurement task "
        dtype = msg['dtype']
        if dtype in ('covid-trace',):
            newtask = CovidTask(channel=msg['channel'],method=msg['method'],ser=scheduler.ser,logger=scheduler.logger,pipe=scheduler.pipe,dtype=dtype)
        elif dtype == 'covid-trace-manualScript':
            newtask = CovidTaskManualScript(channel=msg['channel'],method=msg['method'],ser=scheduler.ser,logger=scheduler.logger,pipe=scheduler.pipe,dtype=dtype)

        self.put(newtask)

    def getOccupancy(self):
        'return occupancy of the taskqueue'
        return sum([t.avgTime/t.interval for t in self])

class Task():
    "measurement task"
    def __init__(self,delay=0):
        "init a measurement task"
        self.nextExec = time.monotonic() + delay
        self.runCount = 0
        self.avgTime = 0
    def __repr__(self):
        return f"{self.__class__.__name__} in {(self.nextExec-time.monotonic()):.3f}s"
    def __gt__(self,b):
        return self.nextExec > b.nextExec

    def __lt__(self,b):
        return self.nextExec < b.nextExec

    def __eq__(self,b):
        return self.nextExec == b.nextExec
    def cancelRun(self):
        self.nextExec = None
    def run(self,*args,**kwargs):
        self.nextExec = None
        res = self.task(*args,**kwargs)
        return res
    def task(self,*args,**kwargs):
        return ""
    def nextRun(self,delay=1):
        self.nextExec = time.monotonic() + delay

class CovidTask(Task):
    def __init__(self,channel,method,ser,logger,pipe,dtype):
        """
        method: {
        script: text to send  # musht have
        interval: seconds interval # must have
        repeats: how many repeat to run # have either repeats or duration.
        duration: how long in total seconds to run.
        }
        """
        super().__init__(delay=0.05)
        self.channel = channel
        self.method = method
        self.ser = ser
        self.logger = logger
        self.startTime = time.monotonic()
        self.pipe = pipe
        self.dtype = dtype
        self.interval = method['interval']
        self.lastFit = None

    def update(self,method):
        self.method = method
        self.interval = method['interval']

    def parse(self,valmatrix):
        voltage = [i[0] for i in valmatrix[0]]
        amp = [i[1] * 1e6 for i in valmatrix[0]] # convert to uA
        return self.channel, voltage, amp, datetime.now()

    def getScript(self):
        "Update script based on last fitresult if needed."
        script = self.method['script']
        if self.method['autoERange']:
            E_begin = convert_voltage(self.method['E_begin'])
            E_end = convert_voltage(self.method['E_end'])
            if self.lastFit and (not self.lastFit.get('err')):
                peakvoltage = self.lastFit.get('pv')
                gap = (self.method['E_end'] - self.method['E_begin'])/2
                estart = peakvoltage - gap
                eend =peakvoltage + gap
                if estart >= -1.61 and eend<= 1.81:
                    E_begin = convert_voltage(estart)
                    E_end = convert_voltage(eend)
            return script.format(E_begin=E_begin,E_end=E_end)
        else:
            return script


    def getRemainingTime(self):
        interval = self.method['interval']
        remaincount = self.method.get('repeats',999999)-self.runCount
        timeByCount = interval * remaincount
        timeByTime = self.method.get('duration',9999999) - (time.monotonic() - self.startTime)
        return min(timeByCount,timeByTime)

    @timeClassFunction(attr='channel',show=True)
    def task(self):
        " run measurement,set its nextExec to a time "
        remainingTime = self.getRemainingTime()
        self.pipe.send({'action':'updateCovidTaskProgress','channel':self.channel,'remainingTime':remainingTime/60})
        if remainingTime<=0:
            self.done()
            return
        self.nextRun(delay=self.method['interval'])

        try:
            Flush(self.ser)
            self.ser.write(self.getScript().encode('ascii'))
            results = GetResults(self.ser)
            valMatrix = GetValueMatrix(results)
            parseresult = self.parse(valMatrix)
            self.lastFit = self.logger.add_result(parseresult,self.runCount,dtype='covid-trace')

        except Exception as e:
            self.logger.error(f"Channel {self.channel} error running CovidTask, error: {e}")
            self.pipe.send({'action':'updateCovidTaskProgress','channel':self.channel,'remainingTime':'error'})
            self.cancelRun()
            self.done()
            return

    def done(self):
        "mark this task as done in logger."
        self.logger.markDone(self.channel)

class CovidTaskManualScript(CovidTask):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        scripts = self.method['scripts']
        self.lastFit = [None]*len(scripts)
        self.scriptPacketNames = []
        self.scriptDefaults = []
        self.traceCount = 0 # how many traces will create
        # replace all scripts with formatable string if need to auto Erange

        for script in scripts:
            script['script'],packetNames,scriptDefault = self.prepare_script(script['script'])
            self.scriptPacketNames.append(packetNames)
            self.scriptDefaults.append(scriptDefault)
            self.traceCount += len(packetNames)

    def prepare_script(self,script):
        "convert methodscript to a formatable string with E_begin and E_end,also return packet names"
        lines = script.split('\n')
        packetNames = []
        scriptDefault = {}
        for k,l in enumerate(lines):
            if l.strip().startswith('set_e'):
                lines[k] = 'set_e {E_begin}'
            elif l.strip().startswith('meas_loop_swv'):
                ls = l.split(' ')
                scriptDefault = {"E_begin": ls[-5], "E_end":ls[-4]}
                ls[-5:-3]=["{E_begin} {E_end}"]
                lines[k] = ' '.join(ls)
            elif l.strip().startswith('pck_add'):
                packetNames.append(l.strip().split(' ')[-1])
        #only return the 1:end packetNames, because assuming the first packet returned is always potential.
        return '\n'.join(lines),packetNames[1:],scriptDefault


    def getScript(self,k):
        "Update script based on last fitresult if needed."
        script = self.method['scripts'][k]['script']

        E_begin = self.scriptDefaults[k]['E_begin']
        E_end =  self.scriptDefaults[k]['E_end']
        if self.method.get('autoERange',False):
            if self.lastFit[k] and (not self.lastFit[k].get('err')):
                peakvoltage = self.lastFit[k].get('pv')
                gap = (ValConverter(float(E_end[:-1]),E_end[-1]) - ValConverter(float(E_begin[:-1]),E_begin[-1]))/2
                estart = peakvoltage - gap
                eend =peakvoltage + gap
                if estart >= -1.61 and eend<= 1.81:
                    E_begin = convert_voltage(estart)
                    E_end = convert_voltage(eend)
        return script.format(E_begin=E_begin,E_end=E_end)

    def parse(self,valmatrix):
        voltage = [i[0] for i in valmatrix[0]]
        amps=[]
        for a in range(1,len(valmatrix[0][0])):
            amps.append( [i[a] * 1e6 for i in valmatrix[0]] ) # convert to uA
        return  voltage, amps

    @timeClassFunction(attr='channel',show=True)
    def task(self):
        remainingTime = self.getRemainingTime()
        self.pipe.send({'action':'updateCovidTaskProgress','channel':self.channel,'remainingTime':remainingTime/60})
        if remainingTime<=0:
            self.done()
            return
        self.nextRun(delay=self.method['interval'])

        try:


            for k,script in enumerate(self.method['scripts']):
                # if the task run first time, need to create New trace.
                createNew = (self.runCount == 0)
                for i in range(script['repeat']):
                    Flush(self.ser)
                    self.ser.write(self.getScript(k).encode('ascii'))
                    results = GetResults(self.ser)
                    valMatrix = GetValueMatrix(results)
                    voltage, amps = self.parse(valMatrix)
                    for p,(amp,packetName) in enumerate(zip(amps,self.scriptPacketNames[k])):
                        index = sum(len(sn) for sn in self.scriptPacketNames[0:k] ) + p - self.traceCount
                        self.lastFit[k] = self.logger.add_result(self.channel, index, voltage,amp, packetName, k,datetime.now(),createNew,dtype='covid-trace-manualScript')

                    # if this script is repeating more than once, the next repeat shouldn't create new.
                    createNew = False

                    if i != script['repeat'] - 1: # if it's not the last one, sleep for gap time.
                        time.sleep(script['gap'])
                if k!=len(self.method['scripts'])-1:
                    time.sleep(script['wait'])

        except Exception as e:
            self.logger.error(f"Channel {self.channel} error running CovidTask, error: {e}")
            self.pipe.send({'action':'updateCovidTaskProgress','channel':self.channel,'remainingTime':'error'})
            self.cancelRun()
            self.done()
            return




class ReportTask(Task):
    def __init__(self,logger,pipe,queue):
        super().__init__(delay=1)
        self.logger = logger
        self.pipe = pipe
        self.queue = queue
        self.interval = 0.5

    # @timeClassFunction(show=True)
    def task(self):
        ""
        pst = self.logger.pstraces
        data_to_plot = { chanel:{
                         'dtype': pst[chanel][-1]['dtype'],
                         'idx': len(pst[chanel]) - 1,
                         'name': pst[chanel][-1]['name'],
                         'time': timeseries_to_axis(pst[chanel][-1]['data']['time']),
                         'fit':  pst[chanel][-1]['data']['fit'][-1],
                         'pc':[i['pc'] for i in pst[chanel][-1]['data']['fit']],
                         'peak': pst[chanel][-1]['data']['rawdata'][-1],
                         ### Need to implement
                         'status': self.logger.status[chanel],
                         } for chanel in self.logger.status if self.logger.status[chanel]!='reported'}
        for chanel in self.logger.status:
            self.logger.status[chanel]='reported'
        if data_to_plot:
            self.queue.put_nowait(data_to_plot)
        # self.pipe.send(data_to_plot)
        self.nextRun(delay=self.interval)

class OccupancyTask(Task):
    def __init__(self,pipe,taskQ):
        super().__init__(delay=5)
        self.taskQ = taskQ
        self.pipe = pipe
        self.interval = 10

    # @timeClassFunction(show=True)
    def task(self):
        self.nextRun(delay=self.interval)
        occupancy = self.taskQ.getOccupancy()
        if occupancy <0.3:color='green'
        elif occupancy<0.6: color = 'yellow'
        elif occupancy<0.8: color='pink'
        else:color='red'
        self.pipe.send({'action':'inform','msg':
        f"Work load {occupancy:.2%}." ,'color':color})

class SaveTask(Task):
    def __init__(self,logger,taskqueue, ):
        super().__init__(delay=300)
        self.logger = logger
        self.taskqueue = taskqueue
        self.interval = 900

    # @timeClassFunction(show=True)
    def task(self):
        "for save task, if next task is less than 3seconds later, delay 5 seconds."
        Thread(target=self.logger.save_pstraces,).start()
        self.nextRun(delay=self.interval)

class Scheduler():
    "Task scheduler, if any one task failed, will stop the loop. "
    def __init__(self,logger,ser,pipe,queue,ViewerQueue):
        ""
        self.taskQueue = TaskQueue()
        self.logger = logger
        self.exit = False
        self.ser = ser
        self.pipe = pipe
        self.queue = queue
        self.ViewerQueue = ViewerQueue

    def cleanup(self):
        "clean up tasks before exit"
        self.logger.save_pstraces()
        self.logger.debug('Exit scheduler')

    def execute(self,msg):
        'interpret and execute commands'
        action = msg.pop('action')
        if action == 'stop':
            self.exit = True
        elif action == 'edit':
            channel = msg.pop('channel')
            name = msg.pop('name')
            self.logger.pstraces[channel][-1]['name']=name
            self.logger.needToSave = True
        elif action == 'delete':
            self.logger.pstraces[msg['channel']][-1]['deleted']=True
            self.logger.needToSave = True
        elif action == 'newTask':
            self.taskQueue.newTask(msg,self)
        elif action == 'cancelTask':
            self.taskQueue.cancelTask(msg['channel'])
        elif action == 'updateTask':
            self.taskQueue.updateTask(msg['channel'],msg['method'],msg['dtype'])
        elif action == 'sendDataToViewer':
            def taskfunc():
                self.ViewerQueue.put({'source':'picoMemory','pstraces':self.logger.pstraces})
            Thread(target=taskfunc).start()
        elif action == 'savePSTraceEdit':
            memorySave = msg['data']
            self.logger.needToSave=True
            for channel, datasets in self.logger.pstraces.items():
                modifiedDatasets = memorySave.get(channel,[])
                for mod,ori in zip(modifiedDatasets,datasets):
                    for field in ['name','desc','exp','dtype','_uploaded','deleted']:
                        if mod.get(field,'__NonExist!') != '__NonExist!':
                            ori[field] = mod[field]

    def addTask(self,task):
        self.taskQueue.put(task)

    def runNextTask(self,):
        "run the next task in taskQueue"
        nextTime = self.taskQueue.nextTime()
        if nextTime > 0.01:
            time.sleep(0.01)
            return
        time.sleep(max(0, nextTime))
        nextTask = self.taskQueue.get()
        nextTask.run()
        if nextTask.nextExec:
            self.taskQueue.put(nextTask)


def PicoMainLoop(settings,port,pipe,queue,ViewerDataQueue,serialNo):
    "pipe for receiving data,port is the serial port for pico"
    logger = PicoLogger(port=serialNo, **settings)
    try:
        ser =  openSerialPort(port,logger)
    except Exception as e:
        logger.error(f"Error: Open serial port <{port}>, {e}")
        pipe.send({'action':'error','error':f'Open Port <{ port}> Error.'})
        time.sleep(3)
        return
    logger.info(f'Serial port <{port}> - Pico {serialNo} opened.')
    scheduler = Scheduler(logger=logger,ser=ser,pipe=pipe,queue=queue,ViewerQueue=ViewerDataQueue)
    reportTask = ReportTask(logger,pipe,queue)
    occupancyTask = OccupancyTask(pipe,scheduler.taskQueue)
    scheduler.addTask(occupancyTask)
    scheduler.addTask(reportTask)
    saveTask = SaveTask(logger,scheduler.taskQueue)
    scheduler.addTask(saveTask)
    while True:
        # time.sleep(1)
        try:
            while pipe.poll():
                msg = pipe.recv()
                scheduler.execute(msg)

            if scheduler.exit:
                scheduler.cleanup()
                break

            scheduler.runNextTask()

        except Exception as e:
            logger.error(f"Pico Main Loop Error: Exiting... error: {e}")
            break
    try:
        scheduler.cleanup()
        ser.close()
        logger.debug('Exited subprocess.')
    except Exception as e:
        logger.error('Closing pico subprocess error {e}')

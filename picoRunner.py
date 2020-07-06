import time 
from datetime import datetime
from file_monitor import PSS_Logger
import heapq 
from picoLibrary import Flush,GetResults,GetValueMatrix,openSerialPort
from utils import timeseries_to_axis


def timeClassFunction(attr=None,show=True):
    def decorator(func):
        def wrap(self,*args,**kwargs):
            t0 = time.perf_counter()
            res = func(self,*args,**kwargs)
            dt = time.perf_counter() - t0 
            self.avgTime = (self.avgTime * self.runCount + dt) / (self.runCount + 1)
            self.runCount += 1
            if show:
                text = getattr(self,attr) if attr else ""
                print(f"{self.__class__.__name__} {text} took {dt:.3f}s, average: {self.avgTime:.3f}s")
            return res
        return wrap 
    return decorator



class PicoLogger(PSS_Logger): 
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.needToSave = False
        self.status={}
    def save_pstraces(self): 
        if self.needToSave:
            super().save_pstraces()
        self.needToSave = False
    def add_result(self,parseresult,count):
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
            return True
        else:
            # if the timepoint is later than first time point in the dataset, insert.
            dataset = self.pstraces[chanel][-1]
            dataset['data']['time'].append(t)
            dataset['data']['rawdata'].append([voltage, amp])
            dataset['data']['fit'].append(fitres)
            self.debug(
                f"Channel {chanel}, dataset {dataset['name']} append {count+1}th data, time: {t}, ")
            self.markUpdate(chanel)
            return True
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
                t.method=method
                t.pipe.send({'action':'inform','msg':f"{channel} method updated.",'color':'cyan'})
        
    def newTask(self,msg, scheduler):
        "add a measurement task "
        dtype = msg['dtype']
        if dtype == 'covid-trace':
            newtask = CovidTask(channel=msg['channel'],method=msg['method'],ser=scheduler.ser,logger=scheduler.logger,pipe=scheduler.pipe,dtype=dtype)

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
         
            
    def parse(self,valmatrix):
        voltage = [i[0] for i in valmatrix[0]]
        amp = [i[1] * 1e6 for i in valmatrix[0]] # convert to uA
        return self.channel, voltage, amp, datetime.now() 

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

        Flush(self.ser) 
        self.ser.write(self.method['script'].encode('ascii'))
        results = GetResults(self.ser)
        valMatrix = GetValueMatrix(results)
        parseresult = self.parse(valMatrix)
        self.logger.add_result(parseresult,self.runCount) 
        
        
    def done(self):
        "mark this task as done"
        self.logger.markDone(self.channel)
        
class ReportTask(Task):
    def __init__(self,logger,pipe,queue):
        super().__init__(delay=1)
        self.logger = logger
        self.pipe = pipe
        self.queue = queue
        self.interval = 0.5

    @timeClassFunction(show=True)
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
                         } for chanel in self.logger.status if self.logger.status[chanel]!='updated'}
        for chanel in self.logger.status: 
            self.logger.status[chanel]='updated' 
        if data_to_plot:
            self.queue.put_nowait(data_to_plot)
        # self.pipe.send(data_to_plot)
        self.nextRun(delay=self.interval)

class OccupancyTask(Task):
    def __init__(self,pipe,taskQ):
        super().__init__(delay=5)
        self.taskQ = taskQ 
        self.pipe = pipe 
        self.interval = 5 

    @timeClassFunction(show=True)
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
    def __init__(self,logger,taskqueue,saveGap=900):
        super().__init__(delay=600)
        self.logger = logger
        self.taskqueue = taskqueue
        self.interval = saveGap 
    
    @timeClassFunction(show=True)
    def task(self):
        "for save task, if next task is less than 3seconds later, delay 5 seconds."
        if self.taskqueue.nextTime()>3:
            self.logger.save_pstraces()
            self.nextRun(delay=self.interval)
        else:
            self.nextRun(delay=5.2)
        
class Scheduler():
    "Task scheduler"
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
            channel = msg.pop(channel)
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
            self.ViewerQueue.put({'source':'picoMemory','pstraces':self.logger.pstraces}) 
        elif action == 'savePSTraceEdit':
            memorySave = msg['data']
            self.logger.needToSave=True
            for channel, datasets in self.logger.pstraces.items():
                modifiedDatasets = memorySave.get(channel,[])
                for mod,ori in zip(modifiedDatasets,datasets):
                    ori['name'] = mod['name']
                    ori['desc'] = mod['desc']
                    ori['exp'] = mod['exp']
                    ori['dtype'] = mod['dtype']
                    ori['deleted'] = mod.get('deleted',False)
            
    def addTask(self,task):
        self.taskQueue.put(task)    

    def runNextTask(self,):
        "run the next task in taskQueue"
        nextTime = self.taskQueue.nextTime()
        # print(nextTime)
        if nextTime > 0.01:
            time.sleep(0.01)
            return 

        time.sleep(max(0, nextTime))
        nextTask = self.taskQueue.get()
        nextTask.run()
        if nextTask.nextExec:
            self.taskQueue.put(nextTask)
        

def PicoMainLoop(settings,port,pipe,queue,ViewerDataQueue):
    "pipe for receiving data,port is the serial port for pico"
    logger = PicoLogger(**settings)
    try:
        ser =  openSerialPort(port)
    except Exception as e:
        logger.error(f"Error: Open serial port <{port}>, {e}")
        pipe.send({'action':'error','error':f'Open Port <{ port}> Error.'})
        time.sleep(3)
        return 
    logger.info(f'Serial port <{port}> opened.')
    scheduler = Scheduler(logger=logger,ser=ser,pipe=pipe,queue=queue,ViewerQueue=ViewerDataQueue) 
    reportTask = ReportTask(logger,pipe,queue)
    occupancyTask = OccupancyTask(pipe,scheduler.taskQueue)
    scheduler.addTask(occupancyTask)
    scheduler.addTask(reportTask)
    saveTask = SaveTask(logger,scheduler.taskQueue)
    scheduler.addTask(saveTask)
    while True:
        # time.sleep(1)
        scheduler.runNextTask()
        
        while pipe.poll():
            msg = pipe.recv()

            scheduler.execute(msg) 

        if scheduler.exit:
            scheduler.cleanup()
            break 
    ser.close()
    logger.debug('exited subprocess.')

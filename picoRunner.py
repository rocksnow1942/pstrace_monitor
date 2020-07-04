import time 
from datetime import datetime
from file_monitor import PSS_Logger
import heapq 
from picoLibrary import Flush,GetResults,GetValueMatrix
from utils import timeseries_to_axis
 
class PicoLogger(PSS_Logger): 
    
    def save_pstraces(self): 
        if self.needToSave:
            super().save_pstraces()
        self.needToSave = False
    def add_result(self,parseresult,count):
        self.needToSave = True
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
            self.debug(f"Create New Channel {chanel}, add first new data: time: {t}, count:{count+1}")
            return True
        else:
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
                self.debug(
                    f"Channel {chanel} start a new dataset {new_name}: time: {t}, count:{count+1}")
                return True
            else:
                # if the timepoint is later than first time point in the dataset, insert.
                dataset = self.pstraces[chanel] 
                dataset['data']['time'].append(t)
                dataset['data']['rawdata'].append([voltage, amp])
                dataset['data']['fit'].append(fitres)
                self.debug(
                    f"Channel {chanel}, dataset {dataset['name']} append {count+1}th data, time: {t}, ")
                return True
        return False  

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
    def remove(self,channel):
        'remove a measurement task'
        for i,t in enumerate(self):
            if getattr(t,'channel',None) == channel:
                del self[i]
                break 
        heapq.heapify(self)
        
    def nextTime(self):
        if self.empty: return 999 
        return self.peek().nextExec - time.monotonic()

class Task():
    "measurement task"
    def __init__(self,delay=0):
        "init a measurement task"
        self.nextExec = time.monotonic() + delay
    
    def __gt__(self,b):
        return self.nextExec > b.nextExec
    
    def __lt__(self,b):
        return self.nextExec < b.nextExec
        
    def __eq__(self,b):
        return self.nextExec == b.nextExec 
    def nextRun(self,delay=1):
        self.nextExec = time.monotonic() + delay
        
class SWVTask(Task):
    def __init__(self,channel,method,ser,logger):
        """
        method: {
        script: text to send  # musht have 
        interval: seconds interval # must have
        repeats: how many repeat to run # have either repeats or duration. 
        duration: how long in total seconds to run. 
        }
        """
        super().__init__()    
        self.channel = channel 
        self.method = method 
        self.ser = ser
        self.logger = logger 
        self.runCount = 0
        self.startTime = time.monotonic()
    def __repr__(self):
        return f"MeasurementTask {self.channel}"
    
    def parse(self,valmatrix):
        voltage = [i[0] for i in valmatrix]
        amp = [i[1] for i in valmatrix]
        return self.channel, voltage, amp, datetime.now()
    def run(self):
        " run measurement,set its nextExec to a time "
        Flush(self.ser) 
        self.ser.write(self.method['script'].encode('ascii'))
        results = GetResults(self.ser)
        valMatrix = GetValueMatrix(results)
        parseresult = self.parse(valMatrix)
        self.logger.add_result(parseresult,self.runCount) 
        self.runCount+=1 
        runningTime = time.monotonic() - self.startTime 
        maxCount = self.method.get('repeats',9999999)
        maxTime = self.method.get('duration',9999999)
        if self.runCount>= maxCount or runningTime >= maxTime:
            return 
        self.nextRun(delay=self.method['interval'])
        
class ReportTask(Task):
    def __init__(self,logger,pipe):
        super().__init__(delay=1)
        self.logger = logger
        self.pipe = pipe

    def __repr__(self):
        return f"ReprotTask"
    
    def run(self):
        pst = self.logger.pstraces
        data_to_plot = { chanel:{
                         'dtype': pst[chanel][-1]['dtype'],
                         'idx': -1,
                         'name': pst[chanel][-1]['name'],
                         'exp': pst[chanel][-1]['exp'],
                         'time': timeseries_to_axis(pst[chanel][-1]['data']['time']),
                         'pc': [i['pc'] for i in pst[chanel][-1]['data']['fit']],
                         'peak': pst[chanel][-1]['data']['rawdata'][-1]
                         } for chanel in pst if not pst[chanel][-1].get('deleted',False)}
        self.pipe.send(data_to_plot)
        self.nextRun(delay=2)

class SaveTask(Task):
    def __init__(self,logger,taskqueue,saveGap=900):
        super().__init__(delay=600)
        self.logger = logger
        self.taskqueue = taskqueue
        self.SaveGap = saveGap
        
    def run(self):
        "for save task, if next task is less than 3seconds later, delay 5 seconds."
        if self.taskqueue.nextTime>3:
            self.logger.save_pstraces()
            self.nextRun(delay=self.SaveGap)
        else:
            self.nextRun(delay=5)
        
class Scheduler():
    "Task scheduler"
    def __init__(self,logger):
        ""
        self.taskQueue = TaskQueue()
        self.logger = logger
        self.exit = False


    def cleanup(self):
        "clean up tasks before exit" 
        self.logger.save_pstraces()
        self.logger.debug('Exit scheduler')
    
    def addTask(self,newTask):
        self.taskQueue.put(newTask)
        
    def execute(self,msg):
        'interpret and execute commands'
        action = msg.pop('action')
        if action == 'exit':
            self.exit = True 
        
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
        

def mainLoop(settings,pipe):
    "pipe for receiving data"
    logger = PicoLogger(**settings)
    scheduler = Scheduler(logger=logger) 
    reportTask = ReportTask(logger,pipe)
    scheduler.addTask(reportTask)
    saveTask = SaveTask(logger,scheduler.taskQueue)
    scheduler.addTask(saveTask)
    while True:
        scheduler.runNextTask()
        
        while pipe.poll():
            msg = pipe.recv()
            scheduler.execute(msg) 
        
        if scheduler.exit:
            scheduler.cleanup()
            break 



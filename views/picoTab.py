import time
import os
from pathlib import Path
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import multiprocessing as mp
import math
from utils.picoRunner import PicoMainLoop
from utils.picoLibrary import constructScript,openSerialPort
import serial.tools.list_ports
from collections import deque
import threading
from views import PicoMethod

class PicoTab(tk.Frame):
    defaultFigure = ([{'channel':'C1','dtype':'covid-trace','show':False,'showPeak':True,'yMin':0,'yMax':0,
    'E Begin':-0.6,'E End':0,'E Step':0.002,'CurrentRange Min': '100 uA','CurrentRange Max':'100 uA',
    'E Amp':0.05, 'Frequency':100,'Interval':15,'Duration(s)':2400,'Total Scans':160}
         for i in range(8)] )
    def __init__(self,parent,master):
        super().__init__(parent)
        self.master=master
        self.settings = master.settings
        self.create_figure()
        self.create_widgets()
        self.PICORUNNING = None
        self.plotData = {}
        self.datainfo= deque() # information received from pipe
        self.plotjob = None # after job ID for cancelling.
        self.processMessageJob = None

    def saveToMemory(self,memorySave):
        if self.picoisrunning:
            pipe = self.PICORUNNING['pipe']
            pipe.send({'action':'savePSTraceEdit',  'data': memorySave })

    def fetchPicoData(self):
        if self.picoisrunning:
            pipe = self.PICORUNNING['pipe']
            pipe.send({'action':'sendDataToViewer',})

    def edit_pico_settings(self):
        """
        PICO_MONITOR_SETTINGS : {'TARGET_FOLDER','LOG_LEVEL','PRINT_MESSAGES',}
        """
        def submit():
            self.settings['PicoFigureColumns'] = columnCount.get()
            self.settings['PICO_MONITOR_SETTINGS'] = {
                "LOG_LEVEL": loglevel.get() ,
                "PRINT_MESSAGES": printmsg.get(),
            }
            self.updateFigure(columnOnly=True)
            top.destroy()

        top = tk.Toplevel()
        top.geometry(f"+{self.master.winfo_x()+100}+{self.master.winfo_y()+100}")
        top.title('Pico Panel Settings')
        ROW = 0
        printmsg = tk.BooleanVar()
        printmsg.set(self.settings.get('PICO_MONITOR_SETTINGS',{}).get('PRINT_MESSAGES',True))
        tk.Label(top,text='Print Messages:').grid(row=ROW,column=0,padx=30,pady=(15,1),sticky='e')
        tk.Radiobutton(top,text='True',variable=printmsg,value=True).grid(row=ROW,column=1,pady=(15,1),sticky='w')
        tk.Radiobutton(top,text='False',variable=printmsg,value=False).grid(row=ROW,column=1,pady=(15,1),padx=(1,10),sticky='e')

        ROW+=1
        loglevel = tk.StringVar()
        loglevel.set(self.settings.get('PICO_MONITOR_SETTINGS',{}).get('LOG_LEVEL','INFO'))
        tk.Label(top,text='Log Level:').grid(row=ROW,column=0,padx=30,sticky='e')
        tk.OptionMenu(top,loglevel,*['DEBUG','INFO','WARNING','ERROR','CRITICAL']).grid(row=ROW,column=1,sticky='we',padx=(1,45))

        ROW +=1
        tk.Label(top,text='Panel Columns:').grid(row = ROW, column=0,padx=30,sticky='e')
        columnCount = tk.IntVar()
        columnCount.set(self.settings.get('PicoFigureColumns',4))
        tk.Entry(top,width=10,textvariable=columnCount,).grid(row=ROW,column=1,padx=(1,45))

        ROW +=1
        subbtn = tk.Button(top, text='Save', command=submit)
        subbtn.grid(column=0, row=ROW,padx=10,pady=10,sticky='we')
        calbtn = tk.Button(top, text='Cancel', command=top.destroy)
        calbtn.grid(column=1,row=ROW,padx=10,pady=10,sticky='we')

    @property
    def picoisrunning(self):
        return bool(self.PICORUNNING and self.PICORUNNING.get('process',False) and self.PICORUNNING['process'].is_alive())

    def create_figure(self):
        " "
        self.figureWidgets = {}
        self.figureSettings = {}
        for i,figsettings in enumerate(filter(lambda x:x['show'],
                self.settings.get('PicoChannelSettings',self.defaultFigure))):
            channel = figsettings['channel']
            figtype = figsettings['dtype']
            self.figureSettings[channel] = {'dtype':figtype,'channel':channel,'position':i}
            self.create_ithFigure(i,figsettings)
            self.grid_ithFigure(i,figsettings)

    def removeFromGrid(self,channel):
        "remove a figure widget from grid"
        widgets = self.figureWidgets.get(channel)
        for w in widgets:
            try:
                w.grid_forget()
            except:
                continue

    def updateFigure(self,columnOnly=False):
        ""
        if columnOnly:
            for i,figsettings in enumerate(filter(lambda x:x['show'],
                self.settings.get('PicoChannelSettings',self.defaultFigure))):
                self.grid_ithFigure(i,figsettings)
        else:
            newfigsettings = {}
            for i,figsettings in enumerate(filter(lambda x:x['show'],
                self.settings.get('PicoChannelSettings',self.defaultFigure))):
                channel = figsettings['channel']
                figtype = figsettings['dtype']
                newfigsettings[channel] = {'dtype':figtype,'channel':channel,'position':i}

            for channel in self.figureSettings:
                if channel not in newfigsettings:
                    self.removeFromGrid(channel)

            for channel,para in newfigsettings.items():
                if channel not in self.figureSettings:
                    # need to create new
                    self.create_ithFigure(para['position'],para)
                    self.grid_ithFigure(para['position'],para)
                else:
                    # need to update
                    oldpara = self.figureSettings[channel]
                    if oldpara['dtype'] != para['dtype']:
                        self.removeFromGrid(channel)
                        self.create_ithFigure(para['position'],para)
                        self.grid_ithFigure(para['position'],para)
                    elif oldpara['position'] != para['position']:
                        self.grid_ithFigure(para['position'],para)
            self.figureSettings = newfigsettings

        self.msglabel.grid(row=math.ceil(self.TOTAL_PLOT/self.TOTAL_COL) * 4 + 2,
                column=0, columnspan=20*self.TOTAL_COL,pady=15)
    @property
    def TOTAL_PLOT(self):
        return len(self.figureSettings.keys())

    @property
    def TOTAL_COL(self):
        return self.settings.get('PicoFigureColumns',4)

    def create_ithFigure(self,i,settings):
        """create figure and respective widigets.
        need to make sure core buttons are in the same order.
        that is, ax,canvas,tkwidget,name,nameE,start,stop,save,delete need to be in fixed order.
        the only customizable buttons should be after that."""
        channel = settings.get('channel')
        figtype = settings.get('dtype')
        if figtype=='covid-trace':
            f = Figure(figsize=(2, 1.6), dpi=100)
            ax = f.subplots()
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(channel)
            f.set_tight_layout(True)
            canvas = FigureCanvasTkAgg(f, self)
            tkwidget = canvas.get_tk_widget()
            tkwidget.bind('<1>', lambda e: self.focus_set())
            name = tk.Label(self,text='Name')
            nameE = tk.Entry(self, textvariable="", width=15)
            start = tk.Button(self,text='Start',command=self.start_channel(channel))
            stop = tk.Button(self,text='Stop',command=self.stop_channel(channel),state='disabled')
            save = tk.Button(self,text='Save',command=self.trace_edit_cb(channel))
            delete = tk.Button(self, text='X', fg='red',command=self.trace_delete_cb(channel),)
            toggle = tk.Button(self,text='Peak/Trace',command = self.toggle_peak_trace_cb(channel))
            infoVar = tk.StringVar()
            info = tk.Label(self,textvariable=infoVar,)
            self.figureWidgets[channel] = (ax,canvas,tkwidget,name,nameE,start,stop,save,delete,toggle,info,infoVar)
        elif figtype == 'dummy-type':
            f = Figure(figsize=(2, 1.6), dpi=100)
            ax = f.subplots()
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(channel+'Dummy Channel')
            f.set_tight_layout(True)
            canvas = FigureCanvasTkAgg(f, self)
            tkwidget = canvas.get_tk_widget()
            tkwidget.bind('<1>', lambda e: self.focus_set())
            name = tk.Label(self,text='Name')
            nameE = tk.Entry(self, textvariable="", width=15)
            start = tk.Button(self,text='Start', )
            stop = tk.Button(self,text='Stop', )
            save = tk.Button(self,text='Save', )
            delete = tk.Button(self, text='X', fg='red',)
            toggle = tk.Button(self,text='Dummy Button',)
            self.figureWidgets[channel] = (ax,canvas,tkwidget,name,nameE,start,stop,save,delete,toggle)

    def grid_ithFigure(self,i,settings):
        channel = settings.get('channel')
        figtype = settings.get('dtype')
        row = i // self.TOTAL_COL
        col = i % self.TOTAL_COL
        if figtype == 'covid-trace':
            (*_,tkwidget,name,nameE,start,stop,save,delete,toggle,info,_)=self.figureWidgets[channel]
            tkwidget.grid(column= col*4,row=row*4+1,columnspan=4,padx=5)
            name.grid(column=col*4,row=row*4+2,sticky='w',padx=10)
            nameE.grid(column=col*4,row=row*4+2,columnspan=4,sticky='w',padx=(60,1))
            start.grid(column=col*4,row=row*4+3,columnspan=4,padx=(15,4),sticky='w')
            stop.grid(column=col*4,row=row*4+3,columnspan=4,padx=(75,4),sticky='w')
            save.grid(column=col*4,row=row*4+3,columnspan=4,padx=(135,4),sticky='w')
            delete.grid(column=col*4,row=row*4+3,columnspan=4,padx=(1,5),sticky='e')
            toggle.grid(column=col*4,row=row*4+4,columnspan=4,sticky='w',padx=(25,1))
            info.grid(column=col*4,row=row*4+4,columnspan=4,stick='e',padx=(1,15))
        elif figtype == 'dummy-type':
            (*_,tkwidget,name,nameE,start,stop,save,delete,toggle)=self.figureWidgets[channel]
            tkwidget.grid(column= col*4,row=row*4+1,columnspan=4,padx=5)
            name.grid(column=col*4,row=row*4+2,sticky='w',padx=10)
            nameE.grid(column=col*4,row=row*4+2,columnspan=4,sticky='w',padx=(60,1))
            start.grid(column=col*4,row=row*4+3,columnspan=4,padx=(15,4),sticky='w')
            stop.grid(column=col*4,row=row*4+3,columnspan=4,padx=(75,4),sticky='w')
            save.grid(column=col*4,row=row*4+3,columnspan=4,padx=(135,4),sticky='w')
            delete.grid(column=col*4,row=row*4+3,columnspan=4,padx=(1,5),sticky='e')
            toggle.grid(column=col*4,row=row*4+4,columnspan=4,)

    def trace_edit_cb(self,channel):
        "trace edit callback factory"
        def func():
            if self.picoisrunning:
                if channel in self.plotData:
                    pipe = self.PICORUNNING['pipe']
                    name = self.figureWidgets[channel][4].get()
                    pipe.send({'action':'edit','channel':channel,'name':name})
                else:
                    self.displaymsg(f'No data in {channel}','pink')
        return func

    def trace_delete_cb(self,channel):
        "trace delete callback factory"
        def func():
            if self.picoisrunning:
                if channel in self.plotData:
                    pipe = self.PICORUNNING['pipe']
                    pipe.send({'action':'delete','channel':channel})
                    self.covid_trace_plot(channel,data=None,Update=True)
                    self.displaymsg(f'Data in {channel} marked as deleted.','pink')
                else:
                    self.displaymsg(f'No data in {channel}','pink')
        return func

    def start_channel(self,channel):
        "cb function factory for channel"
        def func():
            if self.picoisrunning:
                pipe = self.PICORUNNING['pipe']
                settings = self.getPicoChannelSettings(channel)
                try:
                    method = constructScript(settings)
                except Exception as e:
                    self.displaymsg(f"{channel} method error {e}",'red')
                    return

                pipe.send({'action':'newTask','method':method,'channel':channel,'dtype':settings['dtype']})
                # need to disable start and delete button.
                self.figureWidgets[channel][5]['state']='disabled'
                self.figureWidgets[channel][8]['state']='disabled'
                self.figureWidgets[channel][6]['state']='normal'
                self.displaymsg(f"Started {channel}",'cyan')

        return func

    def update_running_channel(self,channel):
        "update the running channel with new parameters"
        if self.picoisrunning:
            pipe = self.PICORUNNING['pipe']
            settings = self.getPicoChannelSettings(channel)
            try:
                method = constructScript(settings)
            except Exception as e:
                self.displaymsg(f"{channel} method error {e}",'red')
                return
            pipe.send({'action':'updateTask','method':method,'channel':channel,'dtype':settings['dtype']})
            # need to disable start and delete button.
            # self.displaymsg(f"Updated {channel} settings.",'cyan')

    def stop_channel(self,channel):
        "stop channel callback facotry"
        def func():
            if self.picoisrunning:
                pipe = self.PICORUNNING['pipe']
                pipe.send({'action':'cancelTask', 'channel':channel, })
                # need to disable start and delete button.
                self.figureWidgets[channel][5]['state']='normal'
                self.figureWidgets[channel][8]['state']='normal'
                self.figureWidgets[channel][6]['state']='disabled'
                self.displaymsg(f"Stopped {channel}",'red')
        return func

    def toggle_peak_trace_cb(self,channel):
        " toggle channel plot peak or trace callback"
        def func():
            settings = self.getPicoChannelSettings(channel)
            settings['showPeak']=not settings['showPeak']
            if channel in self.plotData:
                self.covid_trace_plot(channel,Update=False)
        return func

    def create_widgets(self):
        ""
        tk.Button(self,text='Scan',command = self.scanPico).grid(row=0,column=0,pady=(15,1))

        self.picoPort = tk.StringVar()
        self.picoPort.set('Select One...')
        self.picoPortMenu = tk.OptionMenu(self,self.picoPort,*['Scan First'])
        self.picoPortMenu.grid(row=0,column=1,columnspan=6,sticky='we',pady=(15,1))

        self.connectPico = tk.Button(self,text='Connect',command=self.connectPico_cb)
        self.connectPico.grid(row=0,column=8,columnspan=2, pady=(15,1))

        self.disconnectPico = tk.Button(self,text='Disconnect',state='disabled',command=self.disconnectPico_cb)
        self.disconnectPico.grid(row=0,column=10,columnspan=2,pady=(15,1))
        tk.Button(self,text='Channel Settings',command=self.channel_settings).grid(row=0,column=13,columnspan=3,pady=(15,1))
        self.msg = tk.StringVar()
        self.msg.set('Pico Ready')
        self.msglabel = tk.Label(self,textvariable=self.msg,bg='cyan')
        self.msglabel.grid(row=math.ceil(self.TOTAL_PLOT/self.TOTAL_COL) * 4 + 2,
                column=0, columnspan=20*self.TOTAL_COL,pady=15)

    def displaymsg(self,msg,color=None):
        self.msg.set(msg)
        if color:
            self.msglabel.config(bg=color)

    def scanPico(self):
        "scan Pico connected and update pico list"
        def cb(i):
            def func():
                self.picoPort.set(i)
            return func
        ports = [i.device for i in serial.tools.list_ports.comports()]
        # start a multi thread finding
        def findPort(p):
            try:
                ser = openSerialPort(p)
                ser.write('i\n'.encode('ascii'))
                res = str(ser.readline(),  'ascii').strip()
                if res:
                    lb = f"{res[1:]} : {p}"
                    self.picoPortMenu['menu'].add_command(label=lb,command=cb(lb))
                    self.displaymsg(f"Found pico {res[1:]} on port <{p}>.")
            except: pass

        self.picoPortMenu['menu'].delete(0,'end')
        for i in ports:
            threading.Thread(target=findPort,args=(i,)).start()

    def connectPico_cb(self):
        port = self.picoPort.get().split(':')[-1].strip()
        defaultDir = str(Path(self.settings['TARGET_FOLDER']).parent)
        directory = tk.filedialog.askdirectory(title="Choose folder to save your data",
            initialdir= self.settings.get( 'PICO_MONITOR_SETTINGS' , {}).get('TARGET_FOLDER',None) or defaultDir )
        if not os.path.exists(directory):
            self.msg.set(
                f"'{directory}' is not a valid folder.")
            self.msglabel.config(bg='red')
            return
        self.connectPico['state']='disabled'
        self.disconnectPico['state']='normal'
        settings = self.settings.get('PICO_MONITOR_SETTINGS',{ })
        settings.update(TARGET_FOLDER=directory)
        p,c = mp.Pipe()
        q = mp.Queue()
        picoprocess = mp.Process(target=PicoMainLoop,args=(settings,port,c,q,self.master.viewer.tempDataQueue))

        while self.picoisrunning:
            time.sleep(0.01)
        self.PICORUNNING = {'process':picoprocess,'pipe':p,'queue':q}
        picoprocess.start()
        self.after(1000,self.start_pico_plotting)
        self.displaymsg(f'Data saved to {directory}','yellow')

    def disconnectPico_cb(self):
        if self.plotjob:
            self.after_cancel(self.plotjob)
        if self.picoisrunning:
            while self.PICORUNNING['pipe'].poll():
                self.PICORUNNING['pipe'].recv()
            self.PICORUNNING['pipe'].send({'action':'stop'})
            while self.picoisrunning:
                time.sleep(0.05)
        self.plotData = {}
        self.connectPico['state']='normal'
        self.disconnectPico['state']='disabled'
        self.displaymsg('Pico Disconnected.','cyan')

    def channel_settings(self):
        "set channel method"
        PicoMethod(parent=self,master=self.master)

    def getPicoChannelSettings(self,channel):
        for figsettings in  self.settings.get('PicoChannelSettings',self.defaultFigure):
            if channel == figsettings['channel']:
                return figsettings
        return None

    def processMessage(self,):
        "process message received from subprocess. return True to stop after cycle."
        if self.datainfo:
            info = self.datainfo.popleft()
            action = info.pop('action')
            if action == 'error':
                self.disconnectPico_cb()
                self.displaymsg(info['error'],'red')
                self.datainfo=deque()
            elif action == 'updateCovidTaskProgress':
                channel = info['channel']
                remain = info['remainingTime']
                text = "Done" if remain<=0 else f"R: {remain:.1f} min"
                color = "green" if remain<=0 else "yellow"
                self.figureWidgets[channel][-1].set(text)
                self.figureWidgets[channel][-2].config(bg=color)
            elif action == 'inform':
                self.displaymsg(info['msg'],info['color'])
            self.processMessageJob = self.after(1200,self.processMessage)
        else:
            self.processMessageJob = None

    def start_pico_plotting(self):
        " start fetch data and plot to ax"
        self.plotjob=None
        if self.picoisrunning:
            pipe = self.PICORUNNING['pipe']
            queue = self.PICORUNNING['queue']
            datatoplot= {}

            while pipe.poll():
               self.datainfo.append(pipe.recv())

            if self.datainfo and not self.processMessageJob:
                self.after(1200,self.processMessage)

            while not queue.empty():
                datatoplot.update(queue.get())

            for channel,data in datatoplot.items():
                figtype = self.getPicoChannelSettings(channel)['dtype']
                if figtype == 'covid-trace':
                    self.covid_trace_plot(channel,data)
            self.plotjob = self.after(1000,self.start_pico_plotting)


    def covid_trace_plot(self,channel,data=None,Update=True):
        (ax,canvas,_,_,nameE,*_)=self.figureWidgets[channel]
        olddata = self.plotData.get(channel,None)
        if ( Update and olddata and data and olddata['name']==data['name'] and len(olddata['time'])==len(data['time']) and
            olddata['status'] == data['status']):
            return
        if not Update:
            data = self.plotData.get(channel,None)
        if data:
            settings =  self.getPicoChannelSettings(channel)
            color = 'grey' if data['status']=='done' else 'green'
            ax.clear()
            ax.tick_params(axis='x',labelsize=6)
            ax.tick_params(axis='y', labelsize=6)
            if settings.get('showPeak',True):
                v,a = data['peak']
                f = data['fit']
                x1, x2 = f['fx']
                y1, y2 = f['fy']
                peakvoltage = f['pv']
                peakcurrent = f['pc']
                k = (y2-y1)/(x2-x1)
                b = -k*x2 + y2
                baselineatpeak = k * f['pv'] + b
                ax.plot(v, a,  f['fx'], f['fy'],
                        [peakvoltage, peakvoltage], [baselineatpeak, baselineatpeak+peakcurrent])
                ax.set_title( f"{channel}-{data['idx']}-{peakcurrent:.1f}uA",color=color,fontsize=8)

            else:
                ymin = settings.get('yMin',None)
                ymax = settings.get('yMax',None)
                t = data['time']
                c = data['pc']
                ax.plot(t,c,marker='o',linestyle='',markersize=2,markerfacecolor='w',color=color)
                ax.set_title(f"{channel}-{data['name'][0:20]}",color=color,fontsize=8)
                ax.set_ylim([ymin or None, ymax or None])
            canvas.draw()
            if (not olddata) or olddata['name'] != data['name']:
                nameE.delete(0, tk.END)
                nameE.insert(tk.END, data['name'])
            self.plotData[channel]=data
        else:
            ax.clear()
            canvas.draw()
            self.plotData.pop(channel)

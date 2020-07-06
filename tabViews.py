import time
import os
from pathlib import Path
import matplotlib
import json
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import ttk
from file_monitor import StartMonitor,save_csv,plot_curve_fit,datasets_to_csv
import multiprocessing as mp
from itertools import zip_longest
from utils import timeseries_to_axis,calc_peak_baseline,PlotState,ViewerDataSource
import platform
from contextlib import contextmanager
import math
import shutil 
from picoRunner import PicoMainLoop
from picoLibrary import constructScript,openSerialPort
import serial.tools.list_ports
from collections import deque
import threading
# TODO
# use Queue for 

# platform conditional imports
if 'darwin' in platform.platform().lower():
    import subprocess
    RIGHT_CLICK = "<Button-2>"
else:
    from io import BytesIO
    import win32clipboard
    from PIL import Image
    RIGHT_CLICK = "<Button-3>"
    def send_image_to_clipboard(imagePath,):
        image = Image.open(imagePath)
        output = BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()


class PicoMethod(tk.Toplevel):
    ""
    defaultCovid = {'channel':'C1','dtype':'covid-trace','show':True,'showPeak':True,'yMin':0,'yMax':0,
    'E Begin':-0.6,'E End':0,'E Step':0.002,'CurrentRange Min': '100 uA','CurrentRange Max':'100 uA',
    'E Amp':0.05, 'Frequency':100,'Interval':15,'Duration(s)':2400,'Total Scans':160}
    dummy = {'channel':'C1','dtype':'dummy-type','show':False,'dummy':0}
    def __init__(self,parent,master):
        super().__init__()
        self.master=master
        self.parent = parent
        self.title("Pico Method Settings")
        self.geometry(f"+{master.winfo_x()+master.winfo_width()}+{master.winfo_y()}")
        self.create_widgets()
    
    def create_widgets(self):
        ""
        self.paramWidgets = []
        self.paramVars = {}
        tk.Label(self,text='Channel List').grid(row=0,column=0,padx=(45,1),pady=(15,1))
        self.channels = tk.Listbox(self,selectmode=tk.EXTENDED,width=10,height=20)
        self.channels.configure(exportselection=False)
        for c in range(16):
            self.channels.insert('end',f'>> C{c+1}') 
        self.channels.bind('<<ListboxSelect>>',self.changeSelect)
        self.channels.grid(row=1,column=0,rowspan=999,padx=(45,1),pady=(1,20),sticky='ne')
 
        self.dType = tk.StringVar()
        self.dType.trace_id = self.dType.trace('w',self.on_dType_change)
        # self.dType.set(channelsetting['dtype'])
        tk.Label(self,text='Exp Type:').grid(column=1,row=0,padx=(10,1),sticky='e',pady=(15,1))
        tk.OptionMenu(self,self.dType,*['covid-trace','dummy-type']).grid(column=2,row=0,padx=(1,25),pady=(15,1),sticky='w')

        tk.Button(self,text='Save Edit',command=self.saveEdit).grid(column=1,row=997,pady=(15,15))
        tk.Button(self,text='Close',command=self.destroy).grid(column=2,row=997,pady=(15,15))

        # channelsetting = self.master.settings.get('PicoChannelSettings',[None])[0] or self.defaultCovid
        # self.dType.set(channelsetting['dtype'])
    
    def create_covid_trace_widget(self,):
        "create covid-trace settings widget and paramVars"
        self.paramVars = {'show':tk.BooleanVar(),'showPeak':tk.BooleanVar()}
        self.paramWidgets = []
        # self.paramVars['show'].set(settings.get('show',False))
        # self.paramVars['showPeak'].set(settings.get('showPeak',True))
        ROW=1
        w = tk.Checkbutton(self,text='Show Channel',variable=self.paramVars['show'])
        w.grid(column=2,row=ROW,sticky='w')
        self.paramWidgets.append(w)
        ROW +=1 
        w = tk.Checkbutton(self,text='Show Peak',variable=self.paramVars['showPeak'])
        w.grid(column=2,row=ROW,sticky='w')
        self.paramWidgets.append(w)
        ROW +=1 
        for name in ['yMin','yMax','E Begin','E End', 'E Step', 'E Amp','Frequency','Interval','Duration(s)','Total Scans']:
            w=tk.Label(self,text=name)
            w.grid(column=1,row=ROW,padx=(10,1),sticky='e')
            self.paramWidgets.append(w)
            self.paramVars[name]=tk.DoubleVar()
            # self.paramVars[name].set(settings.get(name,0))
            w=tk.Entry(self,textvariable=self.paramVars[name],width=15)
            w.grid(column=2,row=ROW,padx=(1,25),sticky='w')
            self.paramWidgets.append(w)
            ROW+=1
        currentRange = ('100 nA','1 uA','10 uA','100 uA','1 mA','5 mA')
        for name in ['CurrentRange Min','CurrentRange Max']:
            self.paramVars[name] = tk.StringVar()
            # self.paramVars[name].set(settings.get(name,'100 uA'))
            w=tk.OptionMenu(self, self.paramVars[name] ,*currentRange)
            w.grid(column=2,row=ROW,padx=(1,25),sticky='w')
            self.paramWidgets.append(w)
            w=tk.Label(self,text=name)
            w.grid(column=1,row=ROW,padx=(10,1),sticky='e')
            self.paramWidgets.append(w)
            ROW+=1 
    
    def craete_dummy_widget(self):
        self.paramVars = {'show':tk.BooleanVar(),'dummy':tk.DoubleVar()}
        self.paramWidgets = []
        ROW=1
        w = tk.Checkbutton(self,text='Show Channel',variable=self.paramVars['show'])
        w.grid(column=2,row=ROW,sticky='w')
        self.paramWidgets.append(w)
        ROW+=1
        w=tk.Label(self,text='dummy')
        w.grid(column=1,row=ROW,padx=(10,1),sticky='e')
        self.paramWidgets.append(w)
        w=tk.Entry(self,textvariable=self.paramVars['dummy'],width=15)
        w.grid(column=2,row=ROW,padx=(1,25),sticky='w')
        self.paramWidgets.append(w)

    def changeSelect(self,e):
        ""
        cur = self.channels.curselection()
        if not cur: return 
        cur = cur[0]
        cur = f'C{cur+1}'
        channelsetting = self.parent.getPicoChannelSettings(cur) or self.defaultCovid 
        dtype = channelsetting.get('dtype')
        self.create_dType_Widgets(dtype)
        self.set_dType(dtype)
        self.writeSettingsToWidget(channelsetting)
            
    def saveEdit(self):
        ""
        channels = self.channels.curselection()
        channels = [f"C{i+1}" for i in channels]
        params = {k:i.get() for k,i in self.paramVars.items()}
        params.update(dtype=self.dType.get())
        for channel in channels: 
            params.update(channel=channel) 
            self.updateMasterSettings(channel,params.copy())
        self.parent.updateFigure()
        for channel in channels:
            self.parent.update_running_channel(channel)

    def updateMasterSettings(self,channel,params): 
        setting = self.master.settings 
        if 'PicoChannelSettings' not in setting:
            setting['PicoChannelSettings'] = []
        setting['PicoChannelSettings'] = list(filter(lambda x:x['channel']!=channel,setting['PicoChannelSettings']))
        setting['PicoChannelSettings'].append(params)
        setting['PicoChannelSettings'].sort(key=lambda x: int(x['channel'][1:]))

    def on_dType_change(self,*args):
        "first remove all widgets then update with new one. also update paramVars"
        dtype = self.dType.get()
        self.create_dType_Widgets(dtype)
        settings = {'covid-trace':self.defaultCovid,'dummy-type':self.dummy}[dtype]
        self.writeSettingsToWidget(settings)
        
    def set_dType(self,dType):
        self.dType.trace_vdelete('w',self.dType.trace_id)
        self.dType.set(dType) 
        self.dType.trace_id = self.dType.trace('w',self.on_dType_change)

    def create_dType_Widgets(self,dtype):
        for w in self.paramWidgets:
            w.grid_forget()
        if dtype == 'covid-trace':
            self.create_covid_trace_widget()
        elif dtype == 'dummy-type':
            self.craete_dummy_widget()

    def writeSettingsToWidget(self,settings):
        for k,i in self.paramVars.items():
            i.set(settings.get(k))
 
class PS_Method(tk.Toplevel):
    def __init__(self,master):
        super().__init__()
        self.master=master
        self.title("PS Method Settings")
        self.geometry(f"+{master.winfo_x()+100}+{master.winfo_y()+100}")
        self.create_widgets()

    def create_widgets(self,):
        ""
        # get settings
        self.getChannelSettings()
        self.channelItems = list(self.psmethod.keys())
        self.channelItems.sort()
        firstChannel = self.channelItems[0] if self.channelItems else None

        # float variables:
        floatParams = ['E_BEGIN','E_END','E_STEP','E_AMP','FREQ']
        self.paramVars = {i:tk.DoubleVar() for i in floatParams}
        # if need future variable, just update the self.paramVars dict.

        paramNames = floatParams
        for ROW, name in enumerate(paramNames):
            self.paramVars[name].set(self.getParam(firstChannel,name))
            tk.Label(self,text=name+': ', ).grid(row=ROW+1,column=1,sticky='e')
            tk.Entry(self,textvariable= self.paramVars[name],width=15).grid(column=2,row=ROW+1,padx=(1,25))

        # special case for current ranges:
        ROW+=1
        tk.Label(self,text='Current Range:').grid(row=ROW+1, column=1,sticky='e')
        self.currentRange = tk.StringVar()
        self.currentRangeOption = ['1nA','10nA','100nA','1uA','10uA','100uA','1mA','10mA']
        tk.OptionMenu(self,self.currentRange,*self.currentRangeOption).grid(column=2,row=ROW+1,padx=(1,25))
        self.currentRange.set(self.currentRangeOption[int(self.getParam(firstChannel, 'IRANGE_START'))])

        ROW+=1
        tk.Button(self, text='Save',command = self.saveEdit).grid(column=1,row=ROW+1,pady=10)
        tk.Button(self, text='Close',command = self.destroy).grid(column=2,row=ROW+1,pady=10)


        tk.Label(self,text='Channel List').grid(row=0,column=0,padx=10,pady=(15,1))
        self.channels = tk.Listbox(self,selectmode=tk.EXTENDED,width=15)
        self.channels.configure(exportselection=False)
        self.reloadChannelList()
        self.channels.grid(row=1,column=0,rowspan=ROW*2,padx=25,pady=(1,5))
        self.channels.bind("<<ListboxSelect>>",self.changeSelect)
        tk.Button(self,text="+ Channel",command=self.addChannel,).grid(column=0,row=ROW*2+1,pady=(1,25))

    def reloadChannelList(self):
        self.channelItems = list(self.psmethod.keys())
        self.channelItems.sort()
        self.channels.delete(0,tk.END)
        for channel in self.channelItems:
            self.channels.insert('end'," >> "+channel)

    def addChannel(self):
        name = tk.simpledialog.askstring('New Channel','Enter new channel name:',parent=self)
        if name:
            fd = self.master.settings.get("TARGET_FOLDER")
            newchannel = os.path.join(fd,name)
            if os.path.exists(newchannel):
                return
            os.mkdir(newchannel)
            selffd = Path(__file__).parent
            srmethod = selffd / 'resources/default.psmethod'
            srscript = selffd / 'resources/default.psscript'
            shutil.copyfile(srmethod,os.path.join(newchannel,'default.psmethod'))
            shutil.copyfile(srscript,os.path.join(newchannel,'default.psscript'))
            self.getChannelSettings()
            self.reloadChannelList()

    def readParamsFromWidget(self):
        params = {}
        for k,i in self.paramVars.items():
            try:
                d = i.get()
            except:
                continue
            if isinstance(d,float):
                params[k] = "{:.3E}".format(d)
            else:
                params[k] = str(d)
        # special case: read current range
        try:
            currentidx = self.currentRangeOption.index(self.currentRange.get())
            params['IRANGE_MIN']=str(currentidx)
            params['IRANGE_MAX']=str(currentidx)
            params['IRANGE_START']=str(currentidx)
            cur = "{:.3E}".format(-3 + currentidx)
            params['IRANGE_MIN_F']=cur
            params['IRANGE_MAX_F']=cur
            params['IRANGE_START_F']=cur
        except Exception as e:
            print(e)
            pass
        return params

    def saveEdit(self):
        cur = self.channels.curselection()
        if not cur: return
        # read current params
        params = self.readParamsFromWidget()
        for sele in cur:
            channel = self.channelItems[sele]
            for pair in self.psmethod[channel]['settings']:
                if pair[0] in params:
                    pair[1]=params[pair[0]]
            self.writeChannelSettings(channel)

    def writeChannelToWidget(self,channel):
        for key,item in self.paramVars.items():
            item.set(self.getParam(channel,key))
        # set current range:
        self.currentRange.set(
            self.currentRangeOption[int(self.getParam(channel, 'IRANGE_START'))])

    def changeSelect(self,e):
        ""
        cur = self.channels.curselection()
        if not cur: return
        cur = cur[0]
        channel = self.channelItems[cur]
        self.writeChannelToWidget(channel)

    def getParam(self,channel,name):
        if channel == None:
            return 0
        st = self.psmethod.get(channel)['settings']
        for res in st:
            if res[0] == name:
                return res[1]

    def writeChannelSettings(self,channel):
        ""
        data = self.psmethod[channel]
        file = data['file']
        with open(file,'wt',encoding='utf-16') as f:
            f.write("\n".join('='.join(entry) for entry in data['settings']))

    def getChannelSettings(self):
        """
        {
            channel name: {
                file: path to psmethod,
                settings: [[field,value]...]
            }
        }
        """
        self.psmethod = {}
        fd = self.master.settings.get("TARGET_FOLDER")
        for r,fd,files in os.walk(fd):
            for file in files:
                if file.endswith('.psmethod'):
                    filepath = Path(r) / file
                    channel = filepath.parent.stem
                    try:
                        with open(filepath,'rt', encoding='utf-16') as f:
                            data = f.read()
                        settings = { 'file':filepath,'settings':[]}
                        data = data.split('\n')
                        for entry in data:
                            if entry.startswith('#'):
                                continue
                            settings['settings'].append(entry.split('='))
                        self.psmethod[channel] = settings
                    except:
                        continue

class ViewerTab(tk.Frame):
    defaultParams = {
            'color':'blue','linestyle': '-','marker':None,'label':"Curve",'alpha':0.75,
            'markersize': 1.0, 'linewidth': 0.5, 'ymin': 0.0, 'ymax': 100.0, 'markerfacecolor':'white',
            'markeredgecolor': 'black','title':'New Plot','legendFontsize': 9.0, 'titleFontsize':14.0,
            'axisFontsize':12.0, 'labelFontsize': 8.0 , 'showGrid': 0,
        }
    markerStyle = [None] + list('.,ov^<>1+xs')
    lineColors = ['blue','green','red','skyblue','orange','lime','royalblue','pink','cyan','white','black']

    def __init__(self,parent=None,master=None):
        super().__init__(parent)
        self.master=master
        self.settings = master.settings
        self.save_settings = master.save_settings
        self.plot_state= PlotState(maxlen=200)

        self.datasource = ViewerDataSource()
        self.create_figures()
        self.create_widgets()
        self.bind('<1>', lambda e: self.focus_set() )

        self.tempDataQueue = mp.Queue() # queue for fetchting data from monitors

        # if True:
        #     self.datasource.load_picklefiles(['/Users/hui/Cloudstation/R&D/Users/Hui Kang/JIM echem data/20200629_pstraces.pickle'])
        #     self.updateTreeviewMenu()

    @property
    def needToSave(self):
        return self.datasource.needToSave

    def saveDataSource(self):
        # self.save_settings()
        memorySave = self.datasource.save()
        if memorySave:
            # save to memory
            for k,d in memorySave.items():
                {'picoMemory':self.master.pico,
                 'monitorMemory': self.master.monitor}[k].saveToMemory(d)
                 

    def create_figures(self):
        STARTCOL = 2
        MHEIGHT = 55
        MWIDTH = 8
        BHEIGHT = 35
        PWIDTH = 4
        PHEIGHT = 9
        BWIDTH = 5


        # main plot window
        self.Mfig = Figure(figsize=(6,4.125),dpi=100)
        self.Max  = self.Mfig.subplots()
        self.Mfig.set_tight_layout(True)
        self.Mcanvas = FigureCanvasTkAgg(self.Mfig, self)
        w= self.Mcanvas.get_tk_widget()
        w.grid(column= STARTCOL,row= 0,columnspan = MWIDTH , pady=(15,0), padx=15, rowspan = MHEIGHT, sticky='n' )
        # self.Mcanvas.callbacks.connect('button_press_event',self.save_fig_cb(self.Mfig))
        w.bind(RIGHT_CLICK,self.OnfigRightClick(self.Mfig))

        # peaks window
        self.Pfig = Figure(figsize=(3.65,2.74),dpi=90)
        self.Pax = [i for j in self.Pfig.subplots(2, 2) for i in j]
        self.Pfig.set_tight_layout(True)
        self.Pcanvas = FigureCanvasTkAgg(self.Pfig, self)

        for pax in self.Pax:
            pax.set_xticks([])
            pax.set_yticks([])

        w=self.Pcanvas.get_tk_widget()
        w.grid(column=STARTCOL, row=MHEIGHT, columnspan=PWIDTH,
               rowspan=PHEIGHT, padx=15, sticky='nw')
        # self.Pcanvas.callbacks.connect('button_press_event',self.save_fig_cb(self.Pfig))
        w.bind(RIGHT_CLICK,self.OnfigRightClick(self.Pfig))

        # browser figure window:
        self.Bfig = Figure(figsize=(3.5,2.8),dpi=82)
        self.Bax = self.Bfig.subplots()
        # self.Bfig.set_tight_layout(True)
        self.Bcanvas = FigureCanvasTkAgg(self.Bfig,self)
        # self.Bcanvas.draw()
        w=self.Bcanvas.get_tk_widget()
        w.grid(column=MWIDTH+STARTCOL,row=0,columnspan=BWIDTH,rowspan=BHEIGHT,padx=10,pady=10,sticky='n')
        # self.Bcanvas.callbacks.connect('button_press_event',self.save_fig_cb(self.Bfig))
        w.bind(RIGHT_CLICK,self.OnfigRightClick(self.Bfig))

    def create_widgets(self):
        ""
        # left area for data loading.
        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL)
        xscrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        tree = ttk.Treeview(self, selectmode='extended', height=40, show=['tree'], yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set,)
        tree.column("#0",minwidth=500,stretch=True)
        scrollbar.config(command=tree.yview)
        xscrollbar.config(command=tree.xview)

        tree.grid(column=0, row=1, padx=5, pady=5, rowspan=100, sticky='ns')
        scrollbar.grid(column=1, row=1, rowspan=100, sticky='nsw')
        xscrollbar.grid(column=0,row=101,sticky='we')
        self.tree = tree
        self.treeViewSelectBind()

        tk.Button(self, text='X',fg='red', command=self.drop_pstrace).grid(
            column=0, row=0, padx=(10,1), pady=(5,1), sticky='ws')
        self.fetchBtn = tk.Button(self, text="Fetch",command=self.add_pstrace('memory'))
        self.fetchBtn.grid(column=0,row=0,padx=(50,40),pady=(5,1),sticky='ws')
        tk.Button(self, text="+File",command=self.add_pstrace('file')).grid(
            column=0,row=0,padx=(105,0),pady=(5,1),sticky='ws')
        tk.Button(self, text='+Folder', command=self.add_pstrace('folder')).grid(
            column=0, row=0, padx=(10,1), pady=(5,1), sticky='es')

        STARTCOL = 2
        MHEIGHT = 55
        MWIDTH = 8
        PWIDTH = 4
        PHEIGHT = 9
        BHEIGHT = 35
        BWIDTH = 5

        # information area
        tk.Label(self, text='Name:').grid(column=STARTCOL+MWIDTH,row=BHEIGHT,sticky='w')
        tk.Label(self, text='Exp:').grid(column=STARTCOL+MWIDTH,row=BHEIGHT+1,sticky='w')
        tk.Label(self, text='Desc:').grid(column=STARTCOL+MWIDTH, row=BHEIGHT+2, sticky='nw')
        self.name = tk.Entry(self, textvariable="", width=22,)
        self.name.grid(column=STARTCOL+MWIDTH,row=BHEIGHT,columnspan=5,sticky='w',padx=(50,1))
        self.exp = tk.Entry(self, textvariable="", width=22,)
        self.exp.grid(column=STARTCOL+MWIDTH,row=BHEIGHT+1,columnspan=5,sticky='w',padx=(50,1))
        self.desc = tk.Text(self,  width=34, height=10, highlightthickness=2,undo=1)
        self.desc.configure(font=('Arial',10))
        self.desc.grid(column=STARTCOL+MWIDTH,row=BHEIGHT+2,columnspan=5,rowspan=10,sticky='w',padx=(50,1))
        tk.Button(self,text="Export CSV", command=self.export_csv,).grid(column=STARTCOL+MWIDTH,row=MHEIGHT,padx=10,pady=10,sticky='e')
        tk.Button(self,text="Upload Data",command=self.uploadData).grid(column=STARTCOL+MWIDTH+2,row=MHEIGHT,padx=10,pady=10)

        self.name.bind('<FocusOut>',self.data_info_cb('name'))
        self.exp.bind('<FocusOut>',self.data_info_cb('exp'))
        self.desc.bind('<FocusOut>', self.data_info_cb('desc'))


        # peak plot area
        self.peak_start = tk.IntVar()
        tk.Label(self, text='Start:').grid(column=STARTCOL,row=MHEIGHT+PHEIGHT,sticky='w',padx=15)
        tk.Entry(self, textvariable=self.peak_start, width=4 ).grid(column=2,row=MHEIGHT+PHEIGHT,padx=(40,1),)
        self.peak_gap = tk.IntVar()
        tk.Label(self, text='Gap:').grid(column=STARTCOL+1, row=MHEIGHT+PHEIGHT, sticky='w',padx=5)
        tk.Entry(self, textvariable=self.peak_gap, width=4).grid(
            column=STARTCOL+1, row=MHEIGHT+PHEIGHT, padx=(20, 1),)
        tk.Button(self,text=" < ",command=lambda : self.peak_start.set(
            max(self.peak_start.get() - 1,0) )).grid(column=STARTCOL+2,row=MHEIGHT+PHEIGHT,sticky='w',padx=10)
        tk.Button(self, text=" > ", command=lambda: self.peak_start.set(
            self.peak_start.get() + 1)).grid(column=STARTCOL+2, row=MHEIGHT+PHEIGHT, padx=10,sticky='e')
        self.peak_start.trace('w', self.variable_callback(self.peak_start,lambda *_: self.plotPeakFig(invodedFrom='peakparams')) )


        # main plotting area tools
        self.plot_params = {}
        for k,i in self.defaultParams.items():
            if isinstance(i,int): var = tk.IntVar()
            elif isinstance(i,float): var = tk.DoubleVar()
            else: var = tk.StringVar()
            self.plot_params[k]=var



        pp = self.plot_params
        self.init_plot_params()

        self.relinkPlotParamsTrace() # add tarces to variables.
        # plottign area layout

        tk.Label(self,text='Plot Title:').grid(column=STARTCOL+PWIDTH,row=MHEIGHT,sticky='w',pady=7,padx=8)
        tk.Entry(self,textvariable=pp['title'],width=30).grid(column=STARTCOL+PWIDTH,row=MHEIGHT,columnspan=4,padx=(53,1))
        tk.Checkbutton(self, text='Show Grid', variable=pp['showGrid']).grid(
            row=MHEIGHT+1, column=STARTCOL+PWIDTH+4,sticky='w')
        # self.liveupdateVar = tk.IntVar()
        # self.liveupdateVar.set(0)
        # tk.Checkbutton(self, text='Live Update', variable=self.liveupdateVar).grid(
        #     row=MHEIGHT+2, column=STARTCOL+PWIDTH+4,sticky='w')
        # self.liveupdateVar.trace('w', lambda *_: self.relinkPlotParamsTrace()
        #     if self.liveupdateVar.get() else self.unlinkPlotParamsTrace() )

        tk.Label(self, text='Legend').grid(
            column=STARTCOL+PWIDTH, row=MHEIGHT+1, columnspan=2)
        tk.Label(self, text='Y Min').grid(
            column=STARTCOL+PWIDTH+2, row=MHEIGHT+1)
        tk.Label(self,text='Y Max').grid(column=STARTCOL+PWIDTH+3,row=MHEIGHT+1)

        tk.Entry(self,textvariable=pp['label'],width=16).grid(column=STARTCOL+PWIDTH,row=MHEIGHT+2,columnspan=2)
        tk.Entry(self,textvariable=pp['ymin'],width=6).grid(column=STARTCOL+PWIDTH+2,row=MHEIGHT+2)
        tk.Entry(self,textvariable=pp['ymax'],width=6).grid(column=STARTCOL+PWIDTH+3,row=MHEIGHT+2)

        linecolors = self.lineColors
        tk.Label(self, text='Line Style').grid(
            column=STARTCOL+PWIDTH, row=MHEIGHT+3)
        tk.Label(self, text='Line Width').grid(
            column=STARTCOL+PWIDTH+1, row=MHEIGHT+3)
        tk.Label(self, text='Line Color').grid(
            column=STARTCOL+PWIDTH+2, row=MHEIGHT+3, padx=15)
        tk.Label(self,text='Line Alpha').grid(column=STARTCOL+PWIDTH+3,row=MHEIGHT+3,padx=15)
        tk.OptionMenu(self,pp['linestyle'],*[None,'-',':','--','-.',]).grid(column=STARTCOL+PWIDTH,row=MHEIGHT+4,sticky='we',padx=5)
        tk.Entry(self, textvariable=pp['linewidth'],width= 6 ).grid(column=STARTCOL+PWIDTH+1,row=MHEIGHT+4)
        tk.OptionMenu(self,pp['color'],*linecolors).grid(column=STARTCOL+PWIDTH+2,row=MHEIGHT+4,sticky='we',padx=5)
        tk.Entry(self,textvariable=pp['alpha'],width=6).grid(column=STARTCOL+PWIDTH+3,row=MHEIGHT+4)

        markerstyle = self.markerStyle
        tk.Label(self,text='Marker Style').grid(column=STARTCOL+PWIDTH,row=MHEIGHT+5)
        tk.Label(self,text='Marker Size').grid(column=STARTCOL+PWIDTH+1,row=MHEIGHT+5)
        tk.Label(self,text='Face Color').grid(column=STARTCOL+PWIDTH+2,row=MHEIGHT+5)
        tk.Label(self,text='Edge Color').grid(column=STARTCOL+PWIDTH+3,row=MHEIGHT+5)
        tk.OptionMenu(self, pp['marker'], *markerstyle).grid(column=STARTCOL+PWIDTH, row=MHEIGHT+6, sticky='we', padx=5)
        tk.Entry(self, textvariable=pp['markersize'], width=6).grid(column=STARTCOL+PWIDTH+1, row=MHEIGHT+6)
        tk.OptionMenu(self, pp['markerfacecolor'], *linecolors).grid(column=STARTCOL+PWIDTH+2, row=MHEIGHT+6, sticky='we', padx=5)
        tk.OptionMenu(self, pp['markeredgecolor'], *linecolors).grid(column=STARTCOL+PWIDTH+3, row=MHEIGHT+6, sticky='we', padx=5)

        tk.Label(self, text='Legend Size').grid(column=STARTCOL+PWIDTH, row=MHEIGHT+7)
        tk.Label(self,text='Title Size').grid(column=STARTCOL+PWIDTH+1,row=MHEIGHT+7)
        tk.Label(self,text='Tick Size').grid(column=STARTCOL+PWIDTH+2,row=MHEIGHT+7)
        tk.Label(self,text='Label Size').grid(column=STARTCOL+PWIDTH+3,row=MHEIGHT+7)
        tk.Entry(self,textvariable=pp['legendFontsize'],width=6).grid(column=STARTCOL+PWIDTH,row=MHEIGHT+8)
        tk.Entry(self,textvariable=pp['titleFontsize'],width=6).grid(column=STARTCOL+PWIDTH+1,row=MHEIGHT+8)
        tk.Entry(self,textvariable=pp['axisFontsize'],width=6).grid(column=STARTCOL+PWIDTH+2,row=MHEIGHT+8)
        tk.Entry(self,textvariable=pp['labelFontsize'],width=6).grid(column=STARTCOL+PWIDTH+3,row=MHEIGHT+8)

        self.undoBtn = tk.Button(self,text='Undo',command=self.undoMainPlot,state='disabled')
        self.undoBtn.grid(column=STARTCOL+PWIDTH, row=MHEIGHT+9, padx=10, pady=15)
        self.redoBtn = tk.Button(self,text='Redo',command=self.redoMainPlot,state='disabled')
        self.redoBtn.grid(column=STARTCOL+PWIDTH+1,row=MHEIGHT+9,padx=10,pady=15)
        tk.Button(self,text='Clear Plot',command=self.clearMainPlot).grid(column=STARTCOL+PWIDTH+2,row=MHEIGHT+9,padx=10,pady=15)
        tk.Button(self,text='Add To Plot',command=self.addMainPlot).grid(column=STARTCOL+PWIDTH+3,row=MHEIGHT+9,padx=10,sticky='we',pady=15)


        # pop up window
        self.rightClickMenu = tk.Menu(self,tearoff=0)
        self.rightClickMenu.add_command(label='Copy Figure to Clipboard',command=self.sendFigToClipboard)
        self.rightClickMenu.add_separator()
        self.rightClickMenu.add_command(label='Save Figure',command=self.save_fig_cb)


    def treeViewSelectBind(self):
        self.treeViewcbID = self.tree.bind('<<TreeviewSelect>>', self.treeviewselect_cb)
    def treeViewSelectUnbind(self):
        self.tree.unbind('<<TreeviewSelect>>',self.treeViewcbID)

    @contextmanager
    def treeViewCbUnbind(self):
        try:
            self.treeViewSelectUnbind()
            yield
        except Exception as e:
            raise e
        finally:
            self.treeViewSelectBind()

    def export_csv(self):
        'export'

        data = self.getAllTreeSelectionData()
        if not data: return
        files = [('CSV file','*.csv'),('All files','*'),]
        file = tk.filedialog.asksaveasfilename(title='Save CSV',filetypes=files,
                initialdir=self.datasource.picklefolder,defaultextension='.csv')
        # print(file)
        if file:
            datasets_to_csv(data,file)

    def uploadData(self):
        data,items = self.getAllTreeSelectionData(returnSelection=True)
        if not data: return
        for _,item in zip(data,items):
            # upload data to database
            print(f'uploaded data to database dummy code{item}')

            # self.datasource.modify(d,'_uploaded',True)
            # self.tree.item(item,text=self.datasource.itemDisplayName(d))

    def switchView(self,view):
        def cb():
            self.settings['TreeViewFormat'] = view
            self.updateTreeviewMenu()
        return cb

    @property
    def TreeViewFormat(self):
        return self.settings.get('TreeViewFormat','dateView')

    def save_plot_settings(self):
        params = self.get_plot_params()
        self.settings.update(params)
        # self.save_settings()

    def updateMainFig(self,datapacket):
        "draw additional data to figure without drawing yet"
        data, params = datapacket
        if data == None:
            self.Max.clear()
            return
        params = params.copy()
        ymin = params.pop('ymin')
        ymax = params.pop('ymax')
        # print(datapacket)
        # print(ymin,ymax)
        title = params.pop('title')
        legendFontsize = params.pop('legendFontsize')
        titleFontsize = params.pop('titleFontsize')
        axisFontsize = params.pop('axisFontsize')
        labelFontsize = params.pop('labelFontsize')
        showGrid = params.pop('showGrid')
        self.Max.set_title(title,fontsize=titleFontsize)
        self.Max.set_ylim([ymin,ymax])
        self.Max.set_xlabel('Time / mins',fontsize=labelFontsize)
        self.Max.set_ylabel('Signal / uA',fontsize=labelFontsize)
        self.Max.tick_params(axis='x',labelsize=axisFontsize)
        self.Max.tick_params(axis='y',labelsize=axisFontsize)
        self.Max.grid(showGrid)
        if data:
            t = timeseries_to_axis(data[0]['data']['time'])
            c = [i['pc'] for i in data[0]['data']['fit']]
            self.Max.plot(t,c,**params)
            params.pop('label')
            for d in data[1:]:
                t = timeseries_to_axis(d['data']['time'])
                c = [i['pc'] for i in d['data']['fit']]
                self.Max.plot(t,c,**params)
            self.Max.legend(fontsize=legendFontsize)

    def newStyleMainFig(self,*args,**kwargs):
        "apply new style to the current selections."
        # if current state has no figure, dont update:
        # also update the small window color.
        self.plotBrowseFig()
        data = self.getAllTreeSelectionData()
        updateSource = 0
        if not data:
            data = self.plot_state.getCurrentData()[0]
            # print(self.plot_state.current,len(self.plot_state))
            if data == None:
                return
            updateSource = 1
        # data,_ = self.plot_state.getCurrentData()
        for packets in self.plot_state.fromLastClear(updateSource):
            self.updateMainFig(packets)
        params = self.get_plot_params()
        self.updateMainFig((data,params))
        self.Mcanvas.draw()
        if updateSource: self.plot_state.updateCurrent((data,params))

    def addMainPlot(self):
        data = self.getAllTreeSelectionData()
        if not data:
            return
        params = self.get_plot_params()
        # if self.plot_state.isBack:
        #     # self.updateMainFig((data,params))
        #     self.plot_state.advance()
        #     self.plot_state.updateCurrent((data,params))
        # else:
        #     self.plot_state.append( )
        #     # self.updateMainFig((data,params) )
        with self.treeViewCbUnbind():
            self.plot_state.upsert((data,params))
            self.tree.selection_set()
            # self.Mcanvas.draw()
            self.undoBtn['state'] = self.plot_state.undoState
            self.redoBtn['state'] = self.plot_state.redoState
            self.nextplotColor()

    def clearMainPlot(self):
        params = self.get_plot_params()
        self.plot_state.append((None,params))
        self.updateMainFig((None,params))
        self.Mcanvas.draw()
        self.undoBtn['state'] = self.plot_state.undoState
        self.redoBtn['state'] = self.plot_state.redoState

    def undoMainPlot(self):
        ""
        # for sele in self.tree.selection():
        #     self.tree.selection_remove(sele)
        # for packets in self.plot_state.fromLastClear():
        #     self.updateMainFig(packets)
        # self.Mcanvas.draw()
        self.plot_state.backward()
        _,params = self.plot_state.getCurrentData()
        self.unlinkPlotParamsTrace()
        for k,i in params.items():
            self.plot_params[k].set(i)
        self.relinkPlotParamsTrace()
        self.tree.selection_set() # this will trigger a redraw to current state.

        self.undoBtn['state'] = self.plot_state.undoState
        self.redoBtn['state'] = self.plot_state.redoState

    def redoMainPlot(self):
        ""
        # self.updateMainFig(self.plot_state.getNextData())
        # self.Mcanvas.draw()
        self.plot_state.advance()
        _,params = self.plot_state.getCurrentData()
        self.unlinkPlotParamsTrace()
        for k,i in params.items():
            self.plot_params[k].set(i)
        self.relinkPlotParamsTrace()
        self.tree.selection_set()
        self.redoBtn['state'] = self.plot_state.redoState
        self.undoBtn['state'] = self.plot_state.undoState

    def variable_callback(self,var,callback):
        def wrap(*args,**kwargs):
            try:
                var.get()
                callback(*args,**kwargs)
            except:
                return
        return wrap

    def init_plot_params(self):
        ""
        for k,var in self.plot_params.items():
            var.set(self.settings.get(k,self.defaultParams[k]))

    def data_info_cb(self, entry):
        def callback(e):
            if entry == 'desc':
                txt = e.widget.get(1.0,'end').strip()
            else:
                txt = e.widget.get().strip()
            if not txt:return
            data,items = self.getAllTreeSelectionData(returnSelection=True)
            if not data: return
            if data[0][entry] != txt:
                # confirm = tk.messagebox.askquestion(f'Edit {entry}',
                # f"Do you want to change <{entry}> on <{len(data)}> datasets??",icon='warning')
                # if confirm != 'yes':
                #     return
                pass
            else:
                return

            if entry=='name':
                if len(data) == 1:
                    self.datasource.modify(data[0],entry,txt) 
                    self.tree.item(items[0],text=self.datasource.itemDisplayName(data[0]))
                else:
                    for i,(d,item) in enumerate(zip(data,items)):
                        nn = txt+'-'+str(i+1)
                        self.datasource.modify(d,entry,nn)
                        self.tree.item(item,text= self.datasource.itemDisplayName(d) )
            else:
                for d in data:
                    self.datasource.modify(d,entry,txt)
                if entry=='exp': # need to rebuild menu
                    self.datasource.rebuildExpView()
                    if self.TreeViewFormat == 'expView':
                        self.updateTreeviewMenu()


        return callback

    def get_plot_params(self):
        para = {}
        for k,i in self.plot_params.items():
            try:
                para[k]=i.get()
            except:
                para[k] = self.defaultParams[k]
        return para

    def plotBrowseFig(self):
        "plot Bfig"
        data = self.getAllTreeSelectionData()
        if not data: return
        self.Bax.clear()
        params = self.get_plot_params()
        if len(data) == 1:
            name = data[0]['name']
        else:
            name = f'{len(data)} Curves'
        self.Bax.set_title(name)
        usefulparams = ({i: params[i] for i in ['linestyle','linewidth',
        'color','marker','markersize','markerfacecolor','markeredgecolor']})
        for d in data:
            t = timeseries_to_axis(d['data']['time'])
            c = [i['pc'] for i in d['data']['fit']]
            self.Bax.plot(t,c,**usefulparams)
        self.Bcanvas.draw()

    def getAllTreeSelectionData(self,returnSelection=False):
        "get all data of current tree selection"
        currentselection = self.tree.selection()
        data = []
        selection = []
        for sele in currentselection:
            d = self.datasource.getData(sele, self.TreeViewFormat )
            if d :
                data.append(d)
                selection.append(sele)
        if returnSelection: return data,selection
        return data

    def getFirstTreeSelectionData(self):
        "get the first data of current selection."
        currentselection = self.tree.selection()
        for sele in currentselection:
            data = self.datasource.getData(sele, self.TreeViewFormat)
            if data: return data
        return None

    def plotPeakFig(self,invodedFrom=None):
        "plot the first peak in selection"
        data = self.getFirstTreeSelectionData()
        if not data: return
        # plot:
        name = data['name']
        self.Pfig.suptitle(name,fontsize=10)
        start = self.peak_start.get()
        interval = self.peak_gap.get()
        timeseries = timeseries_to_axis(data['data']['time'])
        times = timeseries[start::interval][0:4]
        raw = data['data']['rawdata'][start::interval][0:4]
        fit = data['data']['fit'][start::interval][0:4]
        for t,r,f,ax in zip(times,raw,fit,self.Pax):
            ax.clear()
            x1, x2 = f['fx']
            y1, y2 = f['fy']
            peakvoltage = f['pv']
            peakcurrent = f['pc']
            k = (y2-y1)/(x2-x1)
            b = -k*x2 + y2
            baselineatpeak = k * f['pv'] + b
            v, a = r
            color = 'r' if f['err'] else 'b'
            ax.plot(v, a,  f['fx'], f['fy'],
                    [peakvoltage, peakvoltage], [baselineatpeak, baselineatpeak+peakcurrent])
            ax.set_title("{:.1f}m {:.2f}uA".format(t, peakcurrent),
                        fontsize=8, color=color)
            ax.tick_params(axis='x',labelsize=7)
            ax.tick_params(axis='y', labelsize=7)
        self.Pcanvas.draw()

        if invodedFrom=='peakparams':
            # if this update is from peak params update, also change drawing in browser window.
            self.Bax.clear()
            params = self.get_plot_params()
            usefulparams = ({i: params[i] for i in ['linestyle','linewidth',
                'color','marker','markersize','markerfacecolor','markeredgecolor']})
            self.Bax.set_title(name)
            self.Bax.plot(timeseries,[i['pc'] for i in data['data']['fit']],**usefulparams)
            self.Bax.plot(times,[i['pc'] for i in fit],linestyle="", marker='x',markersize=8,color='red')
            self.Bcanvas.draw()

    def updatePeakVariables(self):
        "when select a new plot, only update peak gap to 1/4 of length, this won't trigger drawing peak."
        data = self.getFirstTreeSelectionData()
        if not data: return
        datalength = len(data['data']['time'])
        # self.peak_start.set(0)
        self.peak_gap.set((datalength-1)//4)

    def updateInfo(self):
        data = self.getFirstTreeSelectionData()
        if  not data: return
        self.name.delete(0,'end')
        self.name.insert('end',data['name'])
        self.exp.delete(0,'end')
        self.exp.insert('end',data['exp'])
        self.desc.delete(1.0,'end')
        self.desc.insert('end',data['desc'])

    def treeviewselect_cb(self,e):
        "call back for chaning treeview selection."
        # self.nextplotColor()
        # print('tree view cb')
        self.updatePeakVariables()
        self.plotBrowseFig()
        self.updateInfo()
        data = self.getAllTreeSelectionData()
        for packets in self.plot_state.fromLastClear(currentMinus=0):
            self.updateMainFig(packets)
        if data:
            params = self.get_plot_params()
            self.updateMainFig((data,params))
            # self.plot_state.advance()
            # self.plot_state.updateCurrent((data,params))
        self.Mcanvas.draw()

    def unlinkPlotParamsTrace(self):
        "unlink traces"
        try:
            for i in self.plot_params.values():
                i.trace_vdelete('w',i.trace_id)
        except Exception as e:
            print(e)
            pass

    def relinkPlotParamsTrace(self):
        ""
        for i in self.plot_params.values():
            i.trace_id = i.trace('w', self.variable_callback(i,self.newStyleMainFig))

    def nextplotColor(self):
        "change all color to a next one."
        self.unlinkPlotParamsTrace()
        colors = ['color','markeredgecolor','markerfacecolor']
        try:
            cc = [self.plot_params[i].get() for i in colors]
        except:
            cc = [self.defaultParams[i] for i in colors]
        def ncc(x):
            n = self.lineColors[(self.lineColors.index(x)+1) % len(self.lineColors)]
            if n=='white':
                return ncc(n)
            return n
        for k,i in enumerate(colors):
            self.plot_params[i].set(ncc(cc[k]))
        self.relinkPlotParamsTrace()

    def save_fig_cb(self,):
        fig = self._fig_tosave
        files = [('All files','*'),('PNG image','*.png'),('SVG image','*.svg',),]
        file = tk.filedialog.asksaveasfilename(title='Save figure',filetypes=files,
        initialdir=self.datasource.picklefolder,)
        if file:
            fig.savefig(file,dpi=150)

    def OnfigRightClick(self,fig):
        def cb(e):
            try:
                self._fig_tosave = fig
                self.rightClickMenu.tk_popup(e.x_root,e.y_root)
            finally :
                self.rightClickMenu.grab_release()
        return cb

    def sendFigToClipboard(self,):
        fig= self._fig_tosave
        if self.master.isMAC:
            fig.savefig('__temp.jpg')
            subprocess.run(["osascript", "-e", 'set the clipboard to (read (POSIX file "__temp.jpg") as JPEG picture)'])
            os.remove('__temp.jpg')
        else:
            fig.savefig('__temp.png')
            send_image_to_clipboard('__temp.png')
            os.remove('__temp.png')

    def updateTreeviewMenu(self):
        ""
        for i in self.tree.get_children():
            self.tree.delete(i)
        for parent, children in self.datasource.generate_treeview_menu(view=self.TreeViewFormat):
            self.tree.insert("",'end',parent, text=parent )
            for idx,childname in children:
                self.tree.insert(parent, 'end', idx, text=childname)

    def add_pstrace(self,mode='folder'):
        "add by folder or file"
        def cb():
            if mode == 'folder':
                answer = tk.filedialog.askdirectory(initialdir=str(
                    Path(self.settings['TARGET_FOLDER']).parent))
                answer = answer and [answer]
            elif mode == 'file':
                answer = tk.filedialog.askopenfilenames(initialdir=str(
                    Path(self.settings['TARGET_FOLDER']).parent),filetypes=[("PStrace Pickle File","*.pickle"),('PStrace Pickle File Compressed','*.picklez')])
            elif mode == 'memory':
                if self.master.monitor.ismonitoring or self.master.pico.picoisrunning:
                    if self.datasource.needToSaveToMonitor:
                        confirm = tk.messagebox.askquestion('Unsaved data',
                            "You have unsaved data From Memory, do you want to save?",icon='warning')
                        if confirm=='yes':
                            return
                    self.fetchBtn['state'] = 'disabled'
                    self.master.monitor.fetchMonitoringData()
                    self.master.pico.fetchPicoData()
                    self._fetch_datacount = self.master.monitor.ismonitoring + self.master.pico.picoisrunning
                    self._fetch_datatimeout = 10
                    self.after(500,self.add_pstrace_from_monitor)
                return
            if answer:
                self.add_pstrace_by_file_or_folder(*answer)
        return cb

    def add_pstrace_from_monitor(self):
        self._fetch_datatimeout -= 0.5
        if self._fetch_datatimeout>0 and self._fetch_datacount>0: 
            if not self.tempDataQueue.empty():
                data = self.tempDataQueue.get() 
                self.datasource.load_from_memory(data) 
                self.updateTreeviewMenu()
                self._fetch_datacount -= 1
            self.after(500,self.add_pstrace_from_monitor)
            
        else: 
            # try:
            #     # self.tempDataQueue.close()
            # except:
            #     pass 
            # finally:
            #     self.tempDataQueue=None
            self.fetchBtn['state'] = 'normal'

    def add_pstrace_by_file_or_folder(self,*selectdir):
        picklefiles = []
        for i in selectdir:
            if os.path.isdir(i):
                for r,_,fl in os.walk(i):
                    for f in fl:
                        if f.endswith('.pickle') or f.endswith('.picklez'):
                            picklefiles.append(os.path.join(r,f))
            elif os.path.isfile(i) and (i.endswith('.pickle') or i.endswith('.picklez')):
                picklefiles.append(i)
            else:
                continue
            if i not in self.settings['PStrace History']:
                if len(self.settings['PStrace History']) >= 10:
                    self.settings['PStrace History'].pop(0)
                self.settings['PStrace History'].append(i)
        if self.master.monitor.ismonitoring:
            targetfolder = self.settings['TARGET_FOLDER']
            picklefiles = [f for f in picklefiles if targetfolder not in f]
        if picklefiles:
            self.datasource.load_picklefiles(picklefiles)
            self.updateTreeviewMenu()
            self.master.updateRecentMenu()
            # self.save_settings()

    def drop_pstrace(self):
        data = self.getAllTreeSelectionData()
        if not data: return
        for d in data:
            self.datasource.modify(d,'deleted', (not d.get('deleted',False)) )
        self.datasource.rebuildDateView()
        self.datasource.rebuildExpView()
        self.updateTreeviewMenu()

    def clear_pstrace(self):
        'remove all pstraces loaded.'
        if self.needToSave:
            confirm = tk.messagebox.askquestion('Unsaved data',
                    "You have unsaved data, do you want to save?",icon='warning')
            if confirm=='yes':
                return
        self.datasource.remove_all()
        self.datasource.rebuildDateView()
        self.datasource.rebuildExpView()
        self.updateTreeviewMenu()

class MonitorTab(tk.Frame):
    def __init__(self, parent=None,master=None):
        super().__init__(parent)
        self.master = master
        self.settings = master.settings
        self.save_settings = master.save_settings
        self.create_figure()
        self.create_widgets()
        self.MONITORING = None
        self.plotData = []
        self.bind('<1>',lambda e: self.focus_set())
        self.plotjob = None

    def update_Channel_Count(self):
        " update the channel window count"
        newchanel = self.settings.get('MONITOR_CHANNEL_COUNT',8)
        newcol = self.settings.get('MONITOR_CHANNEL_COL',4)
        if newcol != self.TOTAL_COL:
            self.TOTAL_COL = newcol
            for i in range(self.TOTAL_PLOT):
                self.grid_ithFigure(i)

        if newchanel > self.TOTAL_PLOT:
            for i in range(self.TOTAL_PLOT,newchanel):
                self.create_ithFigure(i)
                self.grid_ithFigure(i)
        else:
            for i in range(newchanel,self.TOTAL_PLOT):
                *_,widgets = self.axes.pop(),self.canvas.pop(),self.trace_edit_tools.pop(),self.figurewidget.pop()
                for w in widgets:
                    w.grid_forget()
        self.TOTAL_PLOT = newchanel
        self.msglabel.grid(row=math.ceil(newchanel/newcol) * 4 + 2, column=0, columnspan=20*newcol,pady=15)
        self.TOTAL_PLOT = newchanel

    def create_figure(self,):
        "make canvas for figures"
        TOTAL_PLOT = self.TOTAL_PLOT = self.settings.get('MONITOR_CHANNEL_COUNT',8)
        self.TOTAL_COL = self.settings.get('MONITOR_CHANNEL_COL',4)
        self.axes = []
        self.canvas=[]
        self.figurewidget=[]
        self.trace_edit_tools = [] # (too1,tool2)
        for i in range(TOTAL_PLOT):
            self.create_ithFigure(i)
            self.grid_ithFigure(i)

    def create_ithFigure(self,i):
        f = Figure(figsize=(2, 1.6), dpi=100)
        ax = f.subplots()
        self.axes.append(ax)
        ax.set_xticks([])
        ax.set_yticks([])
        f.set_tight_layout(True)
        canvas = FigureCanvasTkAgg(f, self)
        self.canvas.append(canvas)
        tkwidget = canvas.get_tk_widget()
        tkwidget.bind('<1>', lambda e: self.focus_set())
        name = tk.Label(self,text='Name')
        nameE = tk.Entry(self, textvariable="", width=15)
        exp = tk.Label(self, text='Exp')
        expE = tk.Entry(self, textvariable="", width=15)
        save = tk.Button(self,text='Save Changes',command=self.trace_edit_cb(i))
        delete = tk.Button(self, text='X', fg='red',command=self.trace_delete_cb(i),)
        self.trace_edit_tools.append((nameE,expE,))
        self.figurewidget.append((tkwidget,name,nameE,exp,expE,delete,save))

    def grid_ithFigure(self,i):
        tkwidget,name,nameE,exp,expE,delete,save = self.figurewidget[i]
        row = i // self.TOTAL_COL
        col = i % self.TOTAL_COL
        name.grid(column=col*20,row=row*4 + 2,columnspan= 2, sticky=tk.E)
        tkwidget.grid(column=col*20, row=row*4+1, columnspan=20,  )
        nameE.grid(column=col*20 + 2, row=row*4 + 2, columnspan=16, )
        exp.grid(column=col*20, row=row*4 + 3, columnspan=2, sticky=tk.E)
        expE.grid(column=col*20 + 2, row=row*4 + 3, columnspan=16, )
        save.grid(column=col*20+5,row=row*4 + 4, columnspan=15)
        delete.grid(column=col*20,row=row*4+4,columnspan=5)

    def create_widgets(self):
        self.folderbutton = tk.Button(
            self, text='Folder', command=self.new_folder)
        self.folderbutton.grid(row=0, column=0, padx=10, pady=10, sticky=tk.E)
        self.folderinput = tk.Entry(self, width=50)
        self.folderinput.insert(tk.END, self.settings['TARGET_FOLDER'])
        self.folderinput.grid(row=0, column=10,columnspan=40, sticky=tk.W)
        self.start_monitor_button = tk.Button(
            self, text="Start Monitor", command=self.start_monitor)
        self.start_monitor_button.grid(row=0, column=50, columnspan=10)
        self.stop_monitor_button = tk.Button(self, text="Stop Monitor", fg="red", state='disabled',
                                             command=self.stop_monitor)
        self.stop_monitor_button.grid(row=0, column=60, columnspan=10)
        self.save_csv_button = tk.Button(self, text="Save CSV", fg="green",
                                         command=self.save_csv)
        self.save_csv_button.grid(row=0, column=70, columnspan=10)

        self.msg = tk.StringVar()
        self.msg.set('PSS MONITOR READY')
        self.msglabel = tk.Label(self, textvariable=self.msg, bg='cyan')

        self.msglabel.grid(row=math.ceil(self.TOTAL_PLOT/self.TOTAL_COL) * 4 + 2,
                column=0, columnspan=20*self.TOTAL_COL,pady=15)

    @property
    def ismonitoring(self):
        return bool(self.MONITORING and self.MONITORING.get('process', False) and self.MONITORING['process'].is_alive())

    def displaymsg(self,msg,color='cyan'):
        self.msg.set(msg)
        if color:
            self.msglabel.config(bg=color)

    def new_folder(self):
        self.settings['TARGET_FOLDER'] = tk.filedialog.askdirectory(
            initialdir=str(Path(self.settings['TARGET_FOLDER']).parent))
        self.folderinput.delete(0, tk.END)
        self.folderinput.insert(tk.END, self.settings['TARGET_FOLDER'])
        # self.save_settings()

    def plot_curve_fit(self):
        interval = tk.simpledialog.askinteger("Plot Interval","Enter integer interval between 1 to 100.\n 15 is roughly 1min.",
                    parent=self.master,minvalue=1,maxvalue=100,initialvalue=15)
        # done = plot_curve_fit()
        target_folder = self.settings['TARGET_FOLDER']
        tf = Path(target_folder)
        pstraces_loc = tf / f'{tf.stem}_pstraces.pickle'
        if interval:
            if os.path.exists(pstraces_loc):
                if self.ismonitoring:
                    p1,p2 = mp.Pipe()
                    self.MONITORING['pipe'].send({'action':'senddata','pipe':p2})
                else:
                    p1 = None
                p = mp.Process(target=plot_curve_fit, args=(target_folder, interval,p1))
                p.start()
                self.displaymsg(f"Curve fit saved to <{target_folder}>")
            else:
                self.displaymsg(f"PStraces file <{pstraces_loc}> doesn't exist.")

    def trace_delete_cb(self,id):
        "generate delete button callback"
        def func():
            if self.ismonitoring:
                if len(self.plotData) > id:
                    chanel = self.plotData[id]['chanel']
                    name = self.plotData[id]['name']
                    confirm = tk.messagebox.askquestion('Delete data!',
                        f'Delete {chanel} - {name} data?', icon='warning')
                    if confirm == 'yes':
                        idx = self.plotData[id]['idx']
                        pipe = self.MONITORING['pipe']
                        pipe.send({'action':'delete','chanel':chanel,'idx':idx})
                        self.displaymsg(f'Deleted {chanel} - {name}.','cyan')
            else:
                self.displaymsg('Not Monitoring!','yellow')

        return func

    def trace_edit_cb(self,id):
        "generate save chagnes button callback"
        def func():
            if self.ismonitoring:
                if len(self.plotData) > id:
                    chanel = self.plotData[id]['chanel']
                    idx = self.plotData[id]['idx']

                    pipe = self.MONITORING['pipe']
                    name = self.trace_edit_tools[id][0].get()
                    exp = self.trace_edit_tools[id][1].get()
                    pipe.send({'action': 'edit', 'chanel': chanel, 'idx': idx, 'name':name,'exp':exp})
                    self.displaymsg(f'Saved changes to {chanel} - {name}.','cyan')
                else:
                    self.displaymsg('This channel has no data.','cyan')
            else:
                self.displaymsg('Not Monitoring!', 'yellow')

        return func

    def informLogger(self):
        " infor the logger process about new setting changes"
        if self.ismonitoring:
            pipe = self.MONITORING['pipe']
            pipe.send({'action':'setlogger', 'MAX_SCAN_GAP': self.settings['MAX_SCAN_GAP'] })
            self.displaymsg(f"Set max scan gap to {self.settings['MAX_SCAN_GAP']}",'cyan')

    def fetchMonitoringData(self):
        if self.ismonitoring:
            pipe = self.MONITORING['pipe']
            pipe.send({'action':'sendDataToViewer', })
            

    def saveToMemory(self,memorySave):
        if self.ismonitoring:
            pipe = self.MONITORING['pipe']
            pipe.send({'action':'savePSTraceEdit',  'data': memorySave })

    def start_plotting(self):
        if self.ismonitoring:
            pipe = self.MONITORING['pipe']
            datatoplot = []
            while pipe.poll():
                datatoplot = pipe.recv()
            if datatoplot:
                ymin,ymax = self.settings.get('MONITOR_YLIM',(None, None))
                for k, (nd, ax, canvas, tool) in enumerate(zip( datatoplot, self.axes, self.canvas, self.trace_edit_tools)):

                    od = None if len(self.plotData)<=k else self.plotData[k]

                    if (od and od['chanel'] == nd['chanel'] and od['idx'] == nd['idx']
                        and od['name'] == nd['name'] and od['exp']==nd['exp']
                        and len(od['time']) == len(nd['time']) and od['color']==nd['color']):
                        # don't need to plot
                        continue
                    else:
                        t = nd['time']
                        c = nd['pc']
                        color = nd['color']
                        ax.clear()
                        ax.plot(t,c,marker='o',linestyle='',markersize=2,markerfacecolor='w',color=color)
                        ax.set_title(f"{nd['chanel'] +'-'+ nd['name'][0:20]}",color=color,fontsize=8)
                        ax.tick_params(axis='x', labelsize=6)
                        ax.tick_params(axis='y', labelsize=6)
                        ax.set_ylim( [ymin or None, ymax or None] )
                        canvas.draw()
                        nameE, expE = tool
                        if (not od) or od['name'] != nd['name']:
                            nameE.delete(0, tk.END)
                            nameE.insert(tk.END, nd['name'])
                        if (not od) or od['exp'] != nd['exp']:
                            expE.delete(0, tk.END)
                            expE.insert(tk.END, nd['exp'])
                for ax,canvas in zip( self.axes[len(datatoplot):], self.canvas[len(datatoplot):] ):
                    ax.clear()
                    canvas.draw()
                self.plotData = datatoplot
            self.displaymsg('Monitoring...', 'yellow')
            self.plotjob = self.after(2000,self.start_plotting)
        else:
            self.displaymsg('Monitor stopped.','cyan')

    def callback(self,id):

        def func(event):
            # event.widget.grid_forget()

            x,y = (event.x,event.y)
            ax = self.axes[id]
            ax.plot([x],[y],marker='o')
            ax.set_title('plot')
            self.canvas[id].draw()
        return func

    def save_csv(self):
        if self.ismonitoring:
            self.MONITORING['pipe'].send({'action':'savecsv'})
            saved = True
        else:
            saved = save_csv(self.settings['TARGET_FOLDER'])
        if saved:
            self.displaymsg(f"CSV Saved To {self.settings['TARGET_FOLDER']}!")
        else:
            self.displaymsg(f"No pstraces in {self.settings['TARGET_FOLDER']}",'red')

    def stop_monitor(self):
        # self.appPipe.send('stop')
        if self.ismonitoring:
            self.after_cancel(self.plotjob)
            while self.MONITORING['pipe'].poll():
                self.MONITORING['pipe'].recv()
            self.MONITORING['pipe'].send({'action':'stop'})
            while self.ismonitoring:
                # wait until previous monitor is stopped.
                time.sleep(0.05)
        self.plotData = []
        self.start_monitor_button['state'] = 'normal'
        self.folderinput['state'] = 'normal'
        # self.save_csv_button['state'] = 'normal'
        self.stop_monitor_button['state'] = 'disabled'
        self.folderbutton['state'] = 'normal'
        self.displaymsg('Monitor stopped.', 'cyan')

    def start_monitor(self, ):
        self.settings['TARGET_FOLDER'] = self.folderinput.get()

        if not os.path.exists(self.settings['TARGET_FOLDER']):
            self.msg.set(
                f"'{self.settings['TARGET_FOLDER']}' is not a valid folder.")
            self.msglabel.config(bg='red')
            return

        # self.save_settings()
        self.start_monitor_button['state'] = 'disabled'
        self.folderinput['state'] = 'disabled'
        self.stop_monitor_button['state'] = 'normal'
        # self.save_csv_button['state'] = 'disabled'
        self.folderbutton['state'] = 'disabled'

        p,c = mp.Pipe()
        monitorprocess = mp.Process(target=StartMonitor, args=(self.settings,c,self.master.viewer.tempDataQueue))

        while self.ismonitoring:
            # wait until previous monitor is stopped.
            time.sleep(0.1)

        self.MONITORING = {'process':monitorprocess,'pipe':p}
        monitorprocess.start()
        self.start_plotting()
        self.displaymsg('Monitoring...', 'yellow')

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
                ser.write('t\n'.encode('ascii'))
                res = ser.read_until('*\n'.encode('ascii')).decode('ascii')
                if 'esp' in res: 
                    # result.append(p)
                    self.picoPortMenu['menu'].add_command(label=p,command=cb(i))
                    self.displaymsg(f"Found pico on port <{p}>.")
            except: pass 
        
        self.picoPortMenu['menu'].delete(0,'end')  
        for i in ports:
            threading.Thread(target=findPort,args=(i,)).start()
   
    def connectPico_cb(self):
        port = self.picoPort.get()
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
            self.after(800,self.processMessage)
            
    def start_pico_plotting(self):
        " start fetch data and plot to ax"
        self.plotjob=None
        if self.picoisrunning:
            pipe = self.PICORUNNING['pipe']
            queue = self.PICORUNNING['queue']
            datatoplot= {}
            
            while pipe.poll():
               self.datainfo.append(pipe.recv())

            if self.datainfo:
                self.after(500,self.processMessage())
    
            while not queue.empty():
                datatoplot.update(queue.get())

            for channel,data in datatoplot.items():
                figtype = self.getPicoChannelSettings(channel)['dtype']
                if figtype == 'covid-trace':
                    self.covid_trace_plot(channel,data)  
            self.plotjob = self.after(300,self.start_pico_plotting) 
        # else:
        #     print('start pco')
        #     pass
            # self.displaymsg('Pico Stopped.','cyan')

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
       


    
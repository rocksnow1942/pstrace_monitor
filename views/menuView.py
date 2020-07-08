import os
from pathlib import Path
import tkinter as tk
import shutil 


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
            selffd = Path(__file__).parent.parent
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


class PicoMethod(tk.Toplevel):
    """
    How to add a new dtype:
    1. add entry to tk.OptionMenu in self.create_widgets 
    2. add entry in self.create_dType_Widgets
    3. add new method to create widgets layout. 
    4. add entry in self.getDefaultSettings
    5. add default settings as class property.
    """
    defaultCovid = {'channel':'C1','dtype':'covid-trace','show':True,'showPeak':True,'yMin':0,'yMax':0,
    'E Begin':-0.6,'E End':0,'E Step':0.002,'CurrentRange Min': '100 uA','CurrentRange Max':'100 uA',
    'E Amp':0.05, 'Frequency':100,'Interval':15,'Duration(s)':2400,'Total Scans':160}
    dummy = {'channel':'C1','dtype':'dummy-type','show':False,'dummy':0}
    defaultCovidScript = {'channel':'C1','dtype':'covid-trace-manualScript','show':True,'showPeak':True,
    'Interval':15,'Duration(s)':2400,'Total Scans':160,'ScriptFile':"Path/To/Script/File"}
    def __init__(self,parent,master):
        super().__init__()
        self.master=master
        self.parent = parent
        self.title("Pico Method Settings")
        self.geometry(f"+{master.winfo_x()+master.winfo_width()}+{master.winfo_y()}")
        self.create_widgets()
    
    def on_closing(self):
        self.parent.picoMethodMenu = None
        self.destroy()

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
        tk.OptionMenu(self,self.dType,*['covid-trace','covid-trace-manualScript','dummy-type']).grid(column=2,row=0,padx=(1,25),pady=(15,1),sticky='w')

        tk.Button(self,text='Save Edit',command=self.saveEdit).grid(column=1,row=997,pady=(15,15))
        tk.Button(self,text='Close',command=self.on_closing).grid(column=2,row=997,pady=(15,15))

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
    
    def create_covid_treace_manualScript_widget(self):
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
        for name in ['yMin','yMax', 'Interval','Duration(s)','Total Scans']:
            w=tk.Label(self,text=name)
            w.grid(column=1,row=ROW,padx=(10,1),sticky='e')
            self.paramWidgets.append(w)
            self.paramVars[name]=tk.DoubleVar()
            # self.paramVars[name].set(settings.get(name,0))
            w=tk.Entry(self,textvariable=self.paramVars[name],width=15)
            w.grid(column=2,row=ROW,padx=(1,25),sticky='w')
            self.paramWidgets.append(w)
            ROW+=1
        def load_script():
            ""
            answer = tk.filedialog.askopenfilename(initialdir=Path(__file__).parent.parent,filetypes=[(("All Files","*"))])
            if os.path.exists(answer):
                self.paramVars['ScriptFile'].set(answer) 

        w = tk.Button(self,text='Script',command=load_script)
        w.grid(column=1,row=ROW,padx=(10,1),sticky='e')
        self.paramWidgets.append(w)
        self.paramVars['ScriptFile'] = tk.StringVar()
        w = tk.Entry(self,textvariable=self.paramVars['ScriptFile'],width=15)
        w.grid(column=2,row=ROW,padx=(1,25),sticky='w')
        self.paramWidgets.append(w)

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
        
        self.writeSettingsToWidget(channelsetting,self.getDefaultSettings(dtype))
            
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
        self.writeSettingsToWidget(self.getDefaultSettings(dtype))
        
    def set_dType(self,dType):
        self.dType.trace_vdelete('w',self.dType.trace_id)
        self.dType.set(dType) 
        self.dType.trace_id = self.dType.trace('w',self.on_dType_change)

    def getDefaultSettings(self,dtype):
        return ({'covid-trace':self.defaultCovid,
                 'dummy-type':self.dummy, 
                 'covid-trace-manualScript':self.defaultCovidScript}.get(dtype,{}))

    def create_dType_Widgets(self,dtype):
        for w in self.paramWidgets:
            w.grid_forget()
        if dtype == 'covid-trace':
            self.create_covid_trace_widget()
        elif dtype == 'dummy-type':
            self.craete_dummy_widget()
        elif dtype == 'covid-trace-manualScript':
            self.create_covid_treace_manualScript_widget()

    def writeSettingsToWidget(self,settings,default={}):
        for k,i in self.paramVars.items():
            i.set(settings.get(k,default.get(k,0)))
 
import tkinter as tk
from tkinter import ttk
import platform
from views import ViewerTab,PS_Method,MonitorTab,PicoTab,__version__
import json
from pathlib import Path
import time
import os



class Application(tk.Tk):
    isMAC = 'darwin' in platform.platform().lower()
    def __init__(self):
        super().__init__()

        self.title(f"PSTrace master @ {__version__}")
        self.geometry('+40+40')
        self.load_settings()

          # development code:
        # rememb file history
        history = self.settings.get('PStrace History',[])
        self.settings['PStrace History'] = [ i for i in history if os.path.exists(i)]
        # self.datasource.load_picklefiles(self.settings['PStrace History'])
        # self.datasource.load_picklefiles(['/Users/hui/Downloads/2020-06-05/2020-06-05_pstraces.pickle'])
        # self.updateTreeviewMenu()

        self.tabs = ttk.Notebook(self)
        self.monitor = MonitorTab(parent=self.tabs, master=self)
        self.viewer = ViewerTab(parent=self.tabs,master=self)
        self.pico = PicoTab(parent=self.tabs,master=self)
        self.tabs.add(self.pico,text='Pico')
        self.tabs.add(self.monitor,text = 'Monitor')
        self.tabs.add(self.viewer, text='Viewer')
        self.tabs.pack(expand=1,fill='both')
        self.create_menus()
        self.tabs.bind('<<NotebookTabChanged>>',self.onNotebookTabChange)
        # self.windowResizeID = None
        self.windowResizeID = self.bind("<Configure>",self.onWindowResize)

    def on_closing(self):
        "handle window closing. clean up shit"
        self.monitor.stop_monitor()
        self.pico.disconnectPicoFunc()
        while self.monitor.ismonitoring or self.pico.picoisrunning:
            time.sleep(0.01)
        if self.viewer.needToSave:
            confirm = tk.messagebox.askquestion('Unsaved data',
                "You have unsaved data, do you want to save?",icon='warning')
            if confirm=='yes':
                return
        self.save_settings()
        self.destroy()

    def onNotebookTabChange(self,e):
        tab = self.getCurrentTab()
        self.geometry(self.settings.get(tab+'_SIZE','1460x950'),)

    def onWindowResize(self,e):
        self.after(300,self.setWindowSize)

    def setWindowSize(self):
        tab = self.getCurrentTab()
        h = self.winfo_height()
        w = self.winfo_width()
        self.settings[tab+'_SIZE'] = f"{w}x{h}" #self.wm_geometry()

    def getCurrentTab(self):
        selected = self.tabs.select()
        if selected == ".!notebook.!monitortab":
            return 'monitor'
        elif selected == ".!notebook.!viewertab":
            return 'viewer'
        elif selected == '.!notebook.!picotab':
            return 'pico'

    def updateRecentMenu(self):
        last = self.recentmenu.index('end')
        if last!=None:
            for i in range(last,-1,-1):
                self.recentmenu.delete(i)
        for fd in self.settings['PStrace History']:
            self.recentmenu.add_command(label=f"Load <{fd}>",
                command=(lambda fd: lambda:self.viewer.add_pstrace_by_file_or_folder(fd) )(fd) )

    def create_menus(self):
        menu = tk.Menu(self)
        self.config(menu=menu)

        # recent menu
        self.recentmenu = tk.Menu(menu,tearoff=False)
        self.updateRecentMenu()

        # file menu
        filemenu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label='File', menu=filemenu)
        filemenu.add_command(label='New Monitor Folder', command=self.monitor.new_folder)
        filemenu.add_command(label='Save PStrace Edits', command=self.viewer.saveDataSource)
        filemenu.add_cascade(label='Recent PStraces',menu = self.recentmenu)
        filemenu.add_separator()
        filemenu.add_command(label='Quit', command=self.on_closing)

        # pico menu
        picomenu = tk.Menu(menu,tearoff = False)
        menu.add_cascade(label='Pico',menu=picomenu)
        picomenu.add_command(label='Pico Panel Settings',command = self.pico.edit_pico_settings)


        # Monitor menu
        monitormenu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label='Monitor', menu=monitormenu)
        monitormenu.add_command(label='Plot Curve Fit To Monitor Folder', command=self.monitor.plot_curve_fit)
        monitormenu.add_separator()
        monitormenu.add_command(label='Edit PS methods', command = self.edit_ps_methods)
        monitormenu.add_command(label='Monitor Settings',command=self.edit_settings)

        # View Menu
        viewmenu = tk.Menu(menu,tearoff=False)
        menu.add_cascade(label='Viewer', menu=viewmenu)
        viewmenu.add_command(label='Date View', command=self.viewer.switchView('dateView'))
        viewmenu.add_command(label='Experiment View', command=self.viewer.switchView('expView'))
        viewmenu.add_separator()
        viewmenu.add_command(label='Sort Items By Name', command=self.viewer.sortViewcb('name'))
        viewmenu.add_command(label='Sort Items By Time', command=self.viewer.sortViewcb('time'))
        viewmenu.add_separator()
        viewmenu.add_command(label='Clear loaded PStraces', command=self.viewer.clear_pstrace)
        viewmenu.add_separator()
        viewmenu.add_command(label='Save Plotting Parameters',command=self.viewer.save_plot_settings)
        viewmenu.add_command(label='Viewer Tab Settings',command=self.viewer.viewerSettings)

        # About menu
        aboutmenu = tk.Menu(menu,tearoff=False)
        menu.add_cascade(label='About', menu=aboutmenu)
        aboutmenu.add_command(label='Update Notes',command = self.aboutPage)
        aboutmenu.add_command(label='Update Via Github',command = self.updateGithub)

    def edit_ps_methods(self):
        "edit ps trace method in the target folder."
        PS_Method(master=self)

    def aboutPage(self,):
        from views import __updateNote__,__version__
        tk.messagebox.showinfo(title=f"PS Master @ {__version__}", message=__updateNote__, )

    def updateGithub(self,):
        import subprocess
        subprocess.run(['git','pull'])

    def edit_settings(self):
        "edit monitor settings"
        def submit():
            self.settings['PRINT_MESSAGES'] = printmsg.get()
            self.settings['MAX_SCAN_GAP'] = maxgap.get()
            self.settings['LOG_LEVEL'] = loglevel.get()
            self.settings['MONITOR_YLIM'] = [monitor_ymin.get(),monitor_ymax.get()]
            channelcount = channelCount.get()
            channelcol = channelCol.get()
            if (self.settings.get('MONITOR_CHANNEL_COUNT',8) != channelcount
                ) or (self.settings.get('MONITOR_CHANNEL_COL',4) != channelcol ):
                self.settings['MONITOR_CHANNEL_COUNT']  = channelcount
                self.settings['MONITOR_CHANNEL_COL']  = channelcol
                self.monitor.update_Channel_Count()

            self.monitor.informLogger()
            top.destroy()

        top = tk.Toplevel()
        top.geometry(f"+{self.winfo_x()+100}+{self.winfo_y()+100}")
        top.title('Monitor Settings')

        _ROW = 0
        printmsg = tk.BooleanVar()
        printmsg.set(self.settings['PRINT_MESSAGES'])
        tk.Label(top,text='Print Messages:').grid(row=_ROW,column=0,padx=10,pady=10,sticky='e')
        tk.Radiobutton(top,text='True',variable=printmsg,value=True).grid(row=_ROW,column=1,)
        tk.Radiobutton(top,text='False',variable=printmsg,value=False).grid(row=_ROW,column=2,padx=10)

        _ROW+=1
        maxgap = tk.IntVar()
        maxgap.set(self.settings['MAX_SCAN_GAP'])
        tk.Label(top,text='Max Scan Gap:').grid(row=_ROW,column=0,padx=10,sticky=tk.E)
        tk.Entry(top,width=10,textvariable=maxgap).grid(row=_ROW,column=1)

        _ROW+=1
        monitor_ymin = tk.DoubleVar()
        monitor_ymax = tk.DoubleVar()
        ymin,ymax = self.settings.get('MONITOR_YLIM',[0.0,0.0])
        monitor_ymin.set(ymin)
        monitor_ymax.set(ymax)
        tk.Label(top, text='Monitor YMin').grid(row=_ROW,column=0,padx=10,sticky='e')
        tk.Entry(top, width=10, textvariable=monitor_ymin).grid(row=_ROW, column=1)
        _ROW+=1
        tk.Label(top, text='Monitor YMax').grid(row=_ROW,column=0,padx=10,sticky='e')
        tk.Entry(top, width=10, textvariable=monitor_ymax).grid(row=_ROW, column=1)

        _ROW+=1
        channelCount = tk.IntVar()
        channelCount.set(self.settings.get('MONITOR_CHANNEL_COUNT',8))
        tk.Label(top, text='Monitor Channel').grid(row=_ROW,column=0,padx=10,sticky='e')
        tk.Entry(top, width=10, textvariable=channelCount).grid(row=_ROW, column=1)

        _ROW+=1
        channelCol = tk.IntVar()
        channelCol.set(self.settings.get('MONITOR_CHANNEL_COL',4))
        tk.Label(top, text='Monitor Colummn').grid(row=_ROW,column=0,padx=10,sticky='e')
        tk.Entry(top, width=10, textvariable=channelCol).grid(row=_ROW, column=1)


        _ROW+=1
        loglevel = tk.StringVar()
        loglevel.set(self.settings['LOG_LEVEL'])
        tk.Label(top,text='Log Level:').grid(row=_ROW,column=0,padx=10,pady=10,sticky=tk.E)
        tk.OptionMenu(top,loglevel,*['DEBUG','INFO','WARNING','ERROR','CRITICAL']).grid(row=_ROW,column=1)

        _ROW+=1
        subbtn = tk.Button(top, text='Save', command=submit)
        subbtn.grid(column=0, row=_ROW,padx=10,pady=10)
        calbtn = tk.Button(top, text='Cancel', command=top.destroy)
        calbtn.grid(column=1,row=_ROW,padx=10,pady=10)

    def load_settings(self):
        pp = Path(__file__).parent.parent / '.appconfig'
        if os.path.exists(pp):
            settings = json.load(open(pp, 'rt'))
        else:
            settings = dict(
                # default settings
                MAX_SCAN_GAP=30,  # mas interval to be considerred as two traces in seconds
                PRINT_MESSAGES=True,  # whether print message
                LOG_LEVEL='DEBUG',
                TARGET_FOLDER=str((Path(__file__).parent.parent).absolute()),
                TreeViewFormat='dateView',
            )
        self.settings = settings

    def save_settings(self):
        pp = Path(__file__).parent.parent / '.appconfig'
        with open(pp, 'wt') as f:
            json.dump(self.settings, f, indent=2)

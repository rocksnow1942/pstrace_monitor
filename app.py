import time
import os
from pathlib import Path
import matplotlib
import json
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import ttk
from file_monitor import StartMonitor,save_csv,plot_curve_fit
import multiprocessing as mp
from itertools import zip_longest
from utils import timeseries_to_axis,calc_peak_baseline,PlotState,ViewerDataSource
import platform
from contextlib import contextmanager




# TODO:
# add method to edit all psmethod.
# font size

# BUgs
# can not reproduce multi replicate pstrace bug seen on widowns.

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


class Application(tk.Tk):
    isMAC = 'darwin' in platform.platform().lower()
    def __init__(self):
        super().__init__()

        self.title("PSTrace master")
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
        self.tabs.add(self.monitor,text = 'Monitor')
        self.tabs.add(self.viewer, text='Viewer')
        self.tabs.pack(expand=1,fill='both')
        self.create_menus()
        self.tabs.bind('<<NotebookTabChanged>>',self.onNotebookTabChange)
        # self.windowResizeID = None
        self.windowResizeID = self.bind("<Configure>",self.onWindowResize)
        

    def on_closing(self):
        "handle window closing. clean up shit"
        # if self.windowResizeID:
        #     self.unbind("<Configure>",self.windowResizeID)
        self.monitor.stop_monitor()
        while self.monitor.ismonitoring:
            time.sleep(0.1)

        if self.viewer.needToSave:
            confirm = tk.messagebox.askquestion('Unsaved data',
                "You have unsaved data, do you want to save?",icon='warning')
            if confirm=='yes':
                return
        self.save_settings()
        self.destroy()

    def onNotebookTabChange(self,e):
        if self.windowResizeID:
            self.unbind("<Configure>",self.windowResizeID)
        tab = self.getCurrentTab() 
        self.geometry(self.settings.get(tab+'_SIZE','1460x950'),)
        self.windowResizeID = self.bind("<Configure>",self.onWindowResize)

    def onWindowResize(self,e):
        self.after(3000,self.setWindowSize)
        
    def setWindowSize(self):
        tab = self.getCurrentTab()
        self.settings[tab+'_SIZE'] = self.wm_geometry()

    def getCurrentTab(self):
        selected = self.tabs.select()
        if selected == ".!notebook.!monitortab":
            return 'monitor'
        elif selected == ".!notebook.!viewertab":
            return 'viewer'


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
        viewmenu.add_command(label='Save Viewer Settings',command=self.viewer.save_plot_settings)
    
    def edit_ps_methods(self):
        print('not implemeted')

    def edit_settings(self):
        "edit monitor settings"
        def submit():
            self.settings['PRINT_MESSAGES'] = printmsg.get()
            self.settings['MAX_SCAN_GAP'] = maxgap.get()
            self.settings['LOG_LEVEL'] = loglevel.get()
            self.settings['MONITOR_YLIM'] = [monitor_ymin.get(),monitor_ymax.get()]
            # self.save_settings()
            self.monitor.informLogger()
            top.destroy()

        top = tk.Toplevel()
        top.title('Monitor Settings')

        printmsg = tk.BooleanVar()
        printmsg.set(self.settings['PRINT_MESSAGES'])
        tk.Label(top,text='Print Messages:').grid(row=0,column=0,padx=10,pady=10,sticky='e')
        tk.Radiobutton(top,text='True',variable=printmsg,value=True).grid(row=0,column=1,)
        tk.Radiobutton(top,text='False',variable=printmsg,value=False).grid(row=0,column=2,padx=10)


        maxgap = tk.IntVar()
        maxgap.set(self.settings['MAX_SCAN_GAP'])
        tk.Label(top,text='Max Scan Gap:').grid(row=1,column=0,padx=10,sticky=tk.E)
        tk.Entry(top,width=10,textvariable=maxgap).grid(row=1,column=1)

        monitor_ymin = tk.DoubleVar()
        monitor_ymax = tk.DoubleVar()
        ymin,ymax = self.settings.get('MONITOR_YLIM',[0.0,0.0])
        monitor_ymin.set(ymin)
        monitor_ymax.set(ymax)
        tk.Label(top, text='Monitor YMin').grid(row=2,column=0,padx=10,sticky='e')
        tk.Entry(top, width=10, textvariable=monitor_ymin).grid(row=2, column=1)
        tk.Label(top, text='Monitor YMax').grid(row=3,column=0,padx=10,sticky='e')
        tk.Entry(top, width=10, textvariable=monitor_ymax).grid(row=3, column=1)



        loglevel = tk.StringVar()
        loglevel.set(self.settings['LOG_LEVEL'])
        tk.Label(top,text='Log Level:').grid(row=4,column=0,padx=10,pady=10,sticky=tk.E)
        tk.OptionMenu(top,loglevel,*['DEBUG','INFO','WARNING','ERROR','CRITICAL']).grid(row=4,column=1)

        subbtn = tk.Button(top, text='Save', command=submit)
        subbtn.grid(column=0, row=5,padx=10,pady=10)
        calbtn = tk.Button(top, text='Cancel', command=top.destroy)
        calbtn.grid(column=1,row=5,padx=10,pady=10)

    def load_settings(self):
        pp = (Path(__file__).parent / '.appconfig').absolute()
        if os.path.exists(pp):
            settings = json.load(open(pp, 'rt'))
        else:
            settings = dict(
                # default settings
                MAX_SCAN_GAP=30,  # mas interval to be considerred as two traces in seconds
                PRINT_MESSAGES=True,  # whether print message
                LOG_LEVEL='DEBUG',
                TARGET_FOLDER=str((Path(__file__).parent).absolute()),
                TreeViewFormat='dateView',
            )
        self.settings = settings

    def save_settings(self):
        pp = (Path(__file__).parent / '.appconfig').absolute()
        with open(pp, 'wt') as f:
            json.dump(self.settings, f, indent=2)

class MonitorTab(tk.Frame):
    def __init__(self, parent=None,master=None):
        super().__init__(parent)
        self.master = master
        self.settings = master.settings
        self.save_settings = master.save_settings
        self.create_widgets()
        self.create_figure()
        self.MONITORING = None
        self.plotData = []
        self.bind('<1>',lambda e: self.focus_set())

    def create_figure(self):
        "make canvas for figures"
        figures = []
        self.axes = []
        self.canvas=[]
        self.trace_edit_tools = []
        for i in range(8):
            f = Figure(figsize=(2, 1.6), dpi=100)
            ax = f.subplots()
            figures.append(f)
            self.axes.append(ax)
            ax.set_xticks([])
            ax.set_yticks([])
            f.set_tight_layout(True)

        T = tk
        for i in range(8):
            row = i // 4
            col = i % 4
            canvas = FigureCanvasTkAgg(figures[i], self)
            self.canvas.append(canvas)
            # canvas.draw()
            tkwidget = canvas.get_tk_widget()
            tkwidget.grid(column=col*20, row=row*4+1, columnspan=20,  )
            tkwidget.bind('<1>', lambda e: self.focus_set())
            name = T.Label(self,text='Name')
            nameE = T.Entry(self, textvariable="", width=15)
            exp = T.Label(self, text='Exp')
            expE = T.Entry(self, textvariable="", width=15)
            save = tk.Button(self,text='Save Changes',command=self.trace_edit_cb(i))
            delete = tk.Button(self, text='X', fg='red',command=self.trace_delete_cb(i),)
            name.grid(column=col*20,row=row*4 + 2,columnspan= 2, sticky=tk.E)
            nameE.grid(column=col*20 + 2, row=row*4 + 2, columnspan=16, )
            exp.grid(column=col*20, row=row*4 + 3, columnspan=2, sticky=tk.E)
            expE.grid(column=col*20 + 2, row=row*4 + 3, columnspan=16, )
            save.grid(column=col*20+5,row=row*4 + 4, columnspan=15)
            delete.grid(column=col*20,row=row*4+4,columnspan=5)
            self.trace_edit_tools.append((nameE,expE,))

    def create_widgets(self):

        # self.pack(fill=tk.BOTH, expand=True)

        # first row
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
        self.msglabel.grid(row=10, column=0, columnspan=80,pady=15)

    @property
    def ismonitoring(self):
        return self.MONITORING and self.MONITORING.get('process', False) and self.MONITORING['process'].is_alive()

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
            p1,p2 = mp.Pipe()
            pipe.send({'action':'senddata', 'pipe': p2 })
            return p1

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
        monitorprocess = mp.Process(target=StartMonitor, args=(self.settings,c))

        while self.ismonitoring:
            # wait until previous monitor is stopped.
            time.sleep(0.1)

        self.MONITORING = {'process':monitorprocess,'pipe':p}
        monitorprocess.start()
        self.start_plotting()
        self.displaymsg('Monitoring...', 'yellow')

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
            if self.master.monitor.ismonitoring:
                self.master.monitor.saveToMemory(memorySave)

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
            datatowrite = []
            timetowrite = []
            for exp in data:
                name = exp['name']
                time = timeseries_to_axis(exp['data']['time'])
                length = len(time)
                signal = [str(i['pc']) for i in exp['data']['fit']]
                avg_pv = sum(i['pv'] for i in exp['data']['fit']) / length
                avg_pbaseline =  sum(map(calc_peak_baseline,exp['data']['fit'])) / length
                timetowrite.append(
                    ['Avg. Peak Voltage','Avg. Peak Baseline','Time'] + [str(i) for i in time])
                datatowrite.append(
                    [ str(avg_pv), str(avg_pbaseline) , name] + signal)

            if timetowrite:
                maxtime = max(timetowrite, key=lambda x: len(x))
                with open(file, 'wt') as f:
                    for i in zip_longest(*([maxtime]+datatowrite), fillvalue=""):
                        f.write(','.join(i))
                        f.write('\n')

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
                confirm = tk.messagebox.askquestion(f'Edit {entry}',
                f"Do you want to change <{entry}> on <{len(data)}> datasets??",icon='warning')
                if confirm != 'yes':
                    return
            else:
                return

            if entry=='name':
                if len(data) == 1:
                    self.datasource.modify(data[0],entry,txt)
                    self.tree.item(items[0],text=txt)
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
        except:
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
                    Path(self.settings['TARGET_FOLDER']).parent),filetypes=[("PStrace Pickle File","*.pickle")])
            elif mode == 'memory':
                if self.master.monitor.ismonitoring: 
                    if self.datasource.needToSaveToMonitor:
                        confirm = tk.messagebox.askquestion('Unsaved data',
                            "You have unsaved data From Monitor, do you want to save?",icon='warning')
                        if confirm=='yes':
                            return
                    self.fetchBtn['state'] = 'disabled'
                    self.tempDataPipe = self.master.monitor.fetchMonitoringData()
                    self.after(500,self.add_pstrace_from_monitor)
                return 
            if answer:
                self.add_pstrace_by_file_or_folder(*answer)
        return cb

    def add_pstrace_from_monitor(self): 
        if self.tempDataPipe: 
            # print('fetch data from monitor')
            try:
                if self.tempDataPipe.poll():
                    data = self.tempDataPipe.recv()
                    
                    self.tempDataPipe.close()
                    self.datasource.load_from_memory(data)
                    self.updateTreeviewMenu()
                    
                    self.fetchBtn['state'] = 'normal'
                else:
                    self.after(500,self.add_pstrace_from_monitor)
            except: 
                self.tempDataPipe = None
                self.fetchBtn['state'] = 'normal'

    def add_pstrace_by_file_or_folder(self,*selectdir):
        picklefiles = []
        for i in selectdir:
            if os.path.isdir(i):
                for r,_,fl in os.walk(i):
                    for f in fl:
                        if f.endswith('.pickle'):
                            picklefiles.append(os.path.join(r,f))
            elif os.path.isfile(i) and i.endswith('.pickle'):
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

if __name__ == "__main__":
    matplotlib.use('TKAgg')
    mp.set_start_method('spawn')
    app = Application()
    app.protocol('WM_DELETE_WINDOW',app.on_closing)
    app.mainloop()

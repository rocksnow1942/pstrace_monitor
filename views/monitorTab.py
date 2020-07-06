import time
import os
from pathlib import Path
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from utils.file_monitor import StartMonitor,save_csv,plot_curve_fit
import multiprocessing as mp
import math

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

    
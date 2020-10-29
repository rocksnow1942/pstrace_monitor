import os
from pathlib import Path
import tkinter as tk
import tkinter.scrolledtext as ST
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import ttk
from utils.file_monitor import datasets_to_csv,datasets_to_pickle
from utils._util import timeseries_to_axis,PlotState,ViewerDataSource
from utils.calling_algorithm import transformers,algorithm,train_model,cross_validation,load_model,save_model
import platform
from contextlib import contextmanager
from threading import Thread
import platform
from views import __version__
import json
from pathlib import Path
import os
import numpy as np
# TODO:
# after upload force to save data immediately.
# able to save uploaded data id and delete the data later if want to retract.
# able to update uploaded data.
# editing the name,exp, desc not intuitive.

# platform conditional imports
if 'darwin' in platform.platform().lower():
    import subprocess
    RIGHT_CLICK = "<Button-2>"
elif 'win' in platform.platform().lower():
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
else:
    RIGHT_CLICK = "<Button-3>"
    def send_image_to_clipboard(imagePath,):
        print('cannot copy on linux')
        # assert os.path.exists(f), "file does not exist"
        # image = gtk.gdk.pixbuf_new_from_file(f)

        # clipboard = gtk.clipboard_get()
        # clipboard.set_image(image)
        # clipboard.store()

class TrainerApp(tk.Tk):
    isMAC = 'darwin' in platform.platform().lower()
    def __init__(self):
        super().__init__()

        self.title(f"Calling Algorithm Trainer @ {__version__}")
        self.geometry('+40+40')
        self.load_settings()
 
        history = self.settings.get('PStrace History',[])
        self.settings['PStrace History'] = [ i for i in history if os.path.exists(i)]
       

        self.tabs = ttk.Notebook(self)
        self.viewer = DataViewTab(parent=self.tabs,master=self)
        self.trainer = TrainerTab(parent=self.tabs,master=self)

        self.tabs.add(self.viewer,text='DataViewer')
        self.tabs.add(self.trainer,text='Trainer')

        self.tabs.pack(expand=1,fill='both')

        self.create_menus()    


    def on_closing(self):
        "handle window closing. clean up shit"
        vs = self.viewer.needToSave 
        ts = self.trainer.needToSave
        loc = "<viewerTab>" * int(vs) + "<trainerTab>" * int(ts)
        if vs or ts:
            confirm = tk.messagebox.askquestion('Unsaved data',
                f"You have unsaved data in {loc}, do you want to save?",icon='warning')
            if confirm=='yes':
                return
        self.save_settings()
        self.destroy()

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
        filemenu.add_command(label='Save PStrace Edits', command=self.viewer.saveDataSource)
        filemenu.add_cascade(label='Recent PStraces',menu = self.recentmenu)
        filemenu.add_separator()
        filemenu.add_command(label='Quit', command=self.on_closing)

        # View Menu
        viewmenu = tk.Menu(menu,tearoff=False)
        menu.add_cascade(label='Viewer', menu=viewmenu)
        self.addTreeViewMenu(viewmenu,self.viewer)
        viewmenu.add_command(label='Save Plotting Parameters',command=self.viewer.save_plot_settings)
        viewmenu.add_command(label='Viewer Tab Settings',command=self.viewer.viewerSettings)

        #trainer menu 
        trainermenu = tk.Menu(menu,tearoff=False)
        menu.add_cascade(label='Trainer', menu=trainermenu)        
        self.addTreeViewMenu(trainermenu,self.trainer)

    def addTreeViewMenu(self,menu,tab):
        menu.add_command(label='Group By Date', command=tab.switchView('dateView'))
        menu.add_command(label='Group By Experiment', command=tab.switchView('expView'))
        menu.add_command(label='No Group', command=tab.switchView('rawView'))
        menu.add_separator()
        menu.add_command(label='Sort Items By Name', command=tab.sortViewcb('name'))
        menu.add_command(label='Sort Items By Time', command=tab.sortViewcb('time'))
        menu.add_command(label='Sort Items By User Marked Result', command=tab.sortViewcb('result'))
        menu.add_command(label='Sort Items By Prediction Result', command=tab.sortViewcb('predict'))
        menu.add_separator()
        menu.add_command(label='Clear loaded PStraces', command=tab.clear_pstrace)
        menu.add_separator() 

    def load_settings(self):
        pp = Path(__file__).parent.parent / '.trainerconfig'
        if os.path.exists(pp):
            settings = json.load(open(pp, 'rt'))
        else:
            settings = dict(
                # default settings
                TreeViewFormat='dateView',
                TARGET_FOLDER=str((Path(__file__).parent.parent).absolute()),
            )
        self.settings = settings

    def save_settings(self):
        pp = Path(__file__).parent.parent / '.trainerconfig' 
        with open(pp, 'wt') as f:
            json.dump(self.settings, f, indent=2)

class TreeDataViewMixin():
    """
    mix in for all treeView related methods
    """
    def create_treeview(self,width=200):
        """
        tree view list,
        """
        self._tree_width = width
        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL)
        xscrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        tree = ttk.Treeview(self, selectmode='extended', height=40, 
                            show=['tree'], yscrollcommand=scrollbar.set, 
                            xscrollcommand=xscrollbar.set,)
        tree.column("#0",minwidth=100,stretch=True,width=width)
        scrollbar.config(command=tree.yview)
        xscrollbar.config(command=tree.xview)

        tree.grid(column=0, row=1, padx=5, pady=5, rowspan=100, sticky='ns')
        scrollbar.grid(column=1, row=1, rowspan=100, sticky='nsw')
        xscrollbar.grid(column=0,row=101,sticky='we')
        self.tree = tree
        self.treeViewSelectBind()

        tk.Button(self, text='X',fg='red', command=self.drop_pstrace).grid(
            column=0, row=0, padx=(10,1), pady=(5,1), sticky='ws')        
        self.fetchBtn = tk.Button(self, text="Device",command=self.add_pstrace('reader'))
        self.fetchBtn.grid(column=0,row=0,padx=(width//5,40),pady=(5,1),sticky='ws')
        tk.Button(self, text="+File",command=self.add_pstrace('file')).grid(
            column=0,row=0,padx=(width/1.9,0),pady=(5,1),sticky='ws')
        tk.Button(self, text='+Folder', command=self.add_pstrace('folder')).grid(
            column=0, row=0, padx=(10,1), pady=(5,1), sticky='es')
    
    @property
    def targetFolder(self):
        "return the last used folder location if exists."
        folder = str(Path(self.settings['TARGET_FOLDER']))
        if not os.path.exists(folder):
            folder = str((Path(__file__).parent.parent).absolute())
        return folder

    @property
    def needToSave(self):
        return self.datasource.needToSave

    @property
    def TreeViewFormat(self):
        return self.settings.get('TreeViewFormat','dateView')
    
    def switchView(self,view):
        def cb():
            self.settings['TreeViewFormat'] = view
            self.updateTreeviewMenu()
        return cb

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

    def changeItemDisplayName(self,sele):
        "sele is the selection id in self.tree"
        data = self.datasource.getData(sele, self.TreeViewFormat) 
        self.tree.item(sele,text=self.datasource.itemDisplayName(data))

    def drop_pstrace(self):
        data = self.getAllTreeSelectionData()
        if not data: return
        for d in data:
            self.datasource.modify(d,'deleted', (not d.get('deleted',False)) )
        self.datasource.rebuildViews()
        self.updateTreeviewMenu()

    def getFirstTreeSelectionData(self):
        "get the first data of current selection."
        currentselection = self.tree.selection()
        for sele in currentselection:
            data = self.datasource.getData(sele, self.TreeViewFormat)
            if data: return data
        return None

    def getAllTreeSelectionData(self,returnSelection=False):
        "get all data of current tree selection"
        currentselection = self.tree.selection()
        data,selection = self._getDataFromSelection(currentselection)
        if returnSelection: return data,selection
        return data

    def updateTreeviewMenu(self):
        "rebuild the whole tree view."
        maxlen = 20
        for i in self.tree.get_children():
            self.tree.delete(i)
        for parent, children in self.datasource.generate_treeview_menu(view=self.TreeViewFormat):
            self.tree.insert("",'end',parent, text=parent )
            maxlen = max(maxlen,len(parent))
            for idx,childname in children:
                self.tree.insert(parent, 'end', idx, text=childname)
                maxlen = max(maxlen,len(childname))
        width = max(self._tree_width,8*maxlen+50)
        self.tree.column("#0",minwidth=width,stretch=True,width=width)

    def _getDataFromSelection(self,currentselection):
        data = []
        selection = []
        for sele in currentselection:
            d = self.datasource.getData(sele, self.TreeViewFormat )
            if d :
                data.append(d)
                selection.append(sele)
        return data,selection
    
    def add_pstrace(self,mode='folder'):
        "add by folder or file"
        def cb():
             
            if mode == 'folder':
                answer = tk.filedialog.askdirectory(initialdir=self.targetFolder )
                answer = answer and [answer]
            elif mode == 'file':
                answer = tk.filedialog.askopenfilenames(initialdir=self.targetFolder,filetypes=[(("All Files","*")),("Device Data file","*.gz"),("PStrace Pickle File","*.pickle"),('PStrace Pickle File Compressed','*.picklez')])
            elif mode == 'reader':
                Thread(target=self.load_reader_data).start()
                return
            if answer:
                Thread(target = self.add_pstrace_by_file_or_folder,args=answer).start()
        return cb

    def load_reader_data(self):
        "load data from reader."
        ws = [i.strip().upper() for i in self.settings.get('ReaderNames',"").split(',') if i.strip()]
        if ws:
            self.datasource.load_reader_data(ws)
            self.updateTreeviewMenu()
    
    def add_pstrace_by_file_or_folder(self,*selectdir):
        picklefiles = []
        for i in selectdir:
            if os.path.isdir(i):
                self.settings['TARGET_FOLDER'] = i
                self.master
                for r,_,fl in os.walk(i):
                    for f in fl:
                        if f.endswith('.pickle') or f.endswith('.picklez') or f.endswith('.gz'):
                            picklefiles.append(os.path.join(r,f))
            elif os.path.isfile(i) and (i.endswith('.pickle') or i.endswith('.picklez') or i.endswith('.gz')):
                self.settings['TARGET_FOLDER'] = str(Path(i).parent)
                picklefiles.append(i)
            else:
                continue
            if i not in self.settings['PStrace History']:
                if len(self.settings['PStrace History']) >= 10:
                    self.settings['PStrace History'].pop(0)
                self.settings['PStrace History'].append(i)
        if picklefiles:
            self.datasource.load_picklefiles(picklefiles)
            self.updateTreeviewMenu()
            self.master.updateRecentMenu()
            # self.save_settings()

    def clear_pstrace(self):
        'remove all pstraces loaded.'
        if self.needToSave:
            confirm = tk.messagebox.askquestion('Unsaved data',
                    "You have unsaved data, do you want to save?",icon='warning')
            if confirm=='yes':
                return
        self.datasource.remove_all()
        self.datasource.rebuildViews()
        self.updateTreeviewMenu()

    def treeviewselect_cb(self,e):
        "call back for chaning treeview selection."
        raise Exception ('treeviewselect_cb. Your should overwite this method in your class.')
    
    def sortViewcb(self,mode):
        def cb():
            self.datasource.sortViewByNameOrTime(mode=mode)
            self.updateTreeviewMenu()
        return cb

class MessageBoxMixin():
    def create_message_box(self,columnstart,rowstart,width=40,height=15):
        self.msgDisplay = ST.ScrolledText(self,wrap=tk.WORD,width=width,height=height,font=('Arial',10),padx=3,pady=0)
        self.msgDisplay.grid(row=rowstart,column=columnstart,columnspan=4,rowspan=30)
        self.msgDisplay.configure(state='disabled')

    def displayMsg(self,msg):
        "display a message to messsage box"
        self.msgDisplay.configure(state='normal')
        self.msgDisplay.insert('1.0',msg+'\n')
        self.msgDisplay.configure(state='disabled')

class MetaInfoMixin():
    def create_metainfo_widgets(self,startcol,startrow):
        # information area
        tk.Label(self, text='Name:').grid(column=startcol,row=startrow,sticky='w')
        tk.Label(self, text='Exp:').grid(column=startcol,row=startrow+1,sticky='w')
        tk.Label(self, text='Desc:').grid(column=startcol, row=startrow+2, sticky='nw')
        self.name = tk.Entry(self, textvariable="", width=22,)
        self.name.grid(column=startcol,row=startrow,columnspan=5,sticky='w',padx=(50,1))
        self.exp = tk.Entry(self, textvariable="", width=22,)
        self.exp.grid(column=startcol,row=startrow+1,columnspan=5,sticky='w',padx=(50,1))
        self.desc = tk.Text(self,  width=34, height=10, highlightthickness=2,undo=1)
        self.desc.configure(font=('Arial',10))
        self.desc.grid(column=startcol,row=startrow+2,columnspan=5,rowspan=10,sticky='w',padx=(50,1))

    def updateInfo(self):
        data = self.getFirstTreeSelectionData()
        if not data: return
        self.name.delete(0,'end')
        self.name.insert('end',data['name'])
        self.exp.delete(0,'end')
        self.exp.insert('end',data['exp'])
        self.desc.delete(1.0,'end')
        self.desc.insert('end',data['desc'])

class EditMetaInfoMixin():
    def create_editmeatainfo_widgets(self,startcol,startrow):
        tk.Button(self,text="Save Edit",command=self.save_data_info_cb).grid(column=startcol,row=startrow,padx=10,pady=10,sticky='we')
        
        self.saveEditBtn = tk.Button(self,text="Save Pickle", command=self.saveDataSource,)
        self.saveEditBtn.grid(column=startcol+2,row=startrow,padx=10,pady=10,sticky='we')
        
        tk.Button(self, text="Clear",command=self.userMarkAsCb(None)).grid(
            row=startrow+1, column=startcol+2,padx=10,pady=10,sticky='we')
        tk.Button(self, text='Positive',command=self.userMarkAsCb('positive')).grid(
            row=startrow+2, column=startcol,padx=10,pady=10,sticky='we')
        tk.Button(self, text="Negative",command=self.userMarkAsCb('negative')).grid(
            row=startrow+2, column=startcol+2,padx=10,pady=10,sticky='we')       
        tk.Button(self, text='Export Positive',command=self.exportPickleForResult('positive')).grid(
            row=startrow+3, column=startcol,padx=10,pady=10,sticky='we')             
        tk.Button(self,text="Export Negative", command=self.exportPickleForResult('negative'),).grid(
            row=startrow+3, column=startcol+2,padx=10,pady=10,sticky='we')
    
    def userMarkAsCb(self,result):
        def cb():
            data,sele = self.getAllTreeSelectionData(returnSelection=True)
            for d,s in zip(data,sele):
                self.datasource.modify(d,'userMarkedAs',result)
                self.changeItemDisplayName(s)
        return cb
    
    def save_data_info_cb(self):
        data,items = self.getAllTreeSelectionData(returnSelection=True)
        if not data: return
        name = self.name.get().strip()
        exp = self.exp.get().strip()
        desc = self.desc.get(1.0,'end').strip()
        updateExpMenu = False
        for d in data:
            if d.get('exp',None) != exp:
                updateExpMenu = True
                break

        if data[0].get('name',"") != name:
            if len(data) == 1:
                self.datasource.modify(data[0],'name',name)
                self.changeItemDisplayName(items[0])
                # self.tree.item(items[0],text=self.datasource.itemDisplayName(data[0]))
            else:
                for i,(d,item) in enumerate(zip(data,items)):
                    nn = name+'-'+str(i+1)
                    self.datasource.modify(d,'name',nn)
                    self.tree.item(item,text= self.datasource.itemDisplayName(d) )
        for entry,txt in zip(['exp','desc'],[exp,desc]):
            if data[0].get(entry,"") != txt:
                for d in data:
                    self.datasource.modify(d,entry,txt)
        # decide if need to update experiment menu.
        if updateExpMenu: # need to rebuild menu
            self.datasource.rebuildExpView()
            if self.TreeViewFormat == 'expView':
                self.updateTreeviewMenu()
    
    def filterDataFromResult(self,result):
        "filter the data in datasource based on the usermarked result"
        data = []
        for k,item in self.datasource.dateView.items():
            for i in item:
                if i.get('userMarkedAs',None) == result:
                    data.append(i)
        return data

    def exportPickleForResult(self,result):
        def cb():
            data = self.filterDataFromResult(result)
            if not data: return 
            files = [('Compressed pickle file','*.picklez'),]
            file = tk.filedialog.asksaveasfilename(title=f'Save {result.upper()} Results',filetypes=files,
                    initialdir=self.datasource.picklefolder,defaultextension='.picklez')        
            if file:
                datasets_to_pickle(data,file)
                datasets_to_csv(data,file[0:-7]+'csv')
        return cb

    def saveDataSource(self):
        # check if loaded new data reader file
        for f in list(self.datasource.pickles.keys()):
            d = self.datasource.pickles[f]
            if d['modified'] and f.endswith('unspecified_filename_in_load_reader_data'):
                files = [('PStrace Pickle File Compressed','*.picklez')]                 
                file = tk.filedialog.asksaveasfilename(filetypes=files,defaultextension = files)
                self.datasource.pickles[f]['tempSavePath'] = file
        
        # self.save_settings()
        self.saveEditBtn['state']='disabled'
        def callback():
            self.saveEditBtn['state']='normal'
        
        t = Thread(target=self.datasource.save,args=(callback,))
        t.start()

class FigureMixin():
    def create_figure_rightclick_menu(self):
        # pop up window
        self.rightClickMenu = tk.Menu(self,tearoff=0)
        self.rightClickMenu.add_command(label='Copy Figure to Clipboard',command=self.sendFigToClipboard)
        self.rightClickMenu.add_separator()
        self.rightClickMenu.add_command(label='Save Figure',command=self.save_fig_cb)

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


class DataViewTab(tk.Frame,TreeDataViewMixin,MessageBoxMixin,MetaInfoMixin,EditMetaInfoMixin,FigureMixin):
    defaultParams = {
            'color':'blue','linestyle': '-','marker':None,'label':"Curve",'alpha':0.75,
            'markersize': 1.0, 'linewidth': 0.5, 'ymin': 0.0, 'ymax': 100.0, 'markerfacecolor':'white',
            'markeredgecolor': 'black','title':'New Plot','legendFontsize': 9.0, 'titleFontsize':14.0,
            'axisFontsize':12.0, 'labelFontsize': 8.0 , 'showGrid': 0,
        }
    markerStyle = [None] + list('.,o+x')
    lineColors = ['blue','green','red','orange','white','black']

    def __init__(self,parent=None,master=None):
        super().__init__(parent)
        self.master=master
        self.settings = master.settings
        self.save_settings = master.save_settings
        self.plot_state= PlotState(maxlen=200)

        self.datasource = ViewerDataSource(app=self)
        self.create_figures()
        self.create_widgets()
        self.bind('<1>', lambda e: self.focus_set() )
        # for i in range(100):
        #     self.displayMsg(f"fasdf {i}")  

    def viewerSettings(self):
        ""
        def submit():
            self.settings['ReaderNames'] = url.get().strip().upper()
            top.destroy()

        top = tk.Toplevel()
        top.geometry(f"+{self.master.winfo_x()+100}+{self.master.winfo_y()+100}")
        top.title('Viewer Panel Settings')
        _ROW = 0

        url = tk.StringVar()
        url.set(self.settings.get('ReaderNames',""))
        tk.Label(top,text='Reader Names (separate by ,) :').grid(row=_ROW,column=0,padx=(5,0),pady=(15,0),sticky=tk.W)
        _ROW += 1 
        tk.Entry(top,width=50,textvariable=url).grid(row=_ROW,column=0,columnspan=2, padx=(10,10),pady=(1,0),)

        _ROW+=1
        tk.Button(top, text='Save', command=submit).grid(column=0, row=_ROW,padx=10,pady=10)
        tk.Button(top, text='Cancel', command=top.destroy).grid(column=1,row=_ROW,padx=10,pady=10)

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

        self.create_figure_rightclick_menu()

    def create_widgets(self):
        ""
        self.create_treeview()
        
        STARTCOL = 2
        MHEIGHT = 55
        MWIDTH = 8
        PWIDTH = 4
        PHEIGHT = 9
        BHEIGHT = 35

        startcol = STARTCOL+MWIDTH
        startrow = BHEIGHT
        
        # create name,exp,desc 
        self.create_metainfo_widgets(startcol,startrow)
        
        # save edits 
        startrow = MHEIGHT
        self.create_editmeatainfo_widgets(startcol,startrow)
        
        
        # message display
        self.create_message_box(STARTCOL+MWIDTH,MHEIGHT+4)        
        
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
            row=MHEIGHT+1, column=STARTCOL+MWIDTH,sticky='we')
        

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
           
    def save_plot_settings(self):
        params = self.get_plot_params()
        self.settings.update(params)
        self.save_settings()

    def updateMainFig(self,datapacket):
        "draw additional data to figure without drawing yet"
        data, params = datapacket
        if data == None:
            self.Max.clear()
            return
        params = params.copy()
        ymin = params.pop('ymin')
        ymax = params.pop('ymax')        
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
        with self.treeViewCbUnbind():
            self.plot_state.upsert((data,params))
            self.tree.selection_set()
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

    def treeviewselect_cb(self,e):
        "call back for chaning treeview selection."
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
        "unlink traces, this is to make the curve style change with style selection."
        try:
            for i in self.plot_params.values():
                i.trace_vdelete('w',i.trace_id)
        except Exception as e:
            print(e)
            return

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


class TrainerTab(tk.Frame,TreeDataViewMixin,MessageBoxMixin,MetaInfoMixin,EditMetaInfoMixin,FigureMixin):    
    def __init__(self,parent=None,master=None):
        super().__init__(parent)
        self.master = master
        self.settings = master.settings
        self.datasource=ViewerDataSource(app=self)
        self.create_figures()
        self.create_widgets()
        self.bind('<1>', lambda e: self.focus_set() )
        self.trained_model = None
    
    def create_figures(self):
        COL = 2
        HEIGHT = 55
        WIDTH = 16

        # rawfig
        self.Rfig = Figure(figsize=(8,3),dpi=100)
        self.Rax,self.Tax = self.Rfig.subplots(1,2)
        self.Rfig.set_tight_layout(True)
        self.canvas = FigureCanvasTkAgg(self.Rfig,self)        
        w = self.canvas.get_tk_widget()
        w.grid(column= COL,row=0,columnspan=WIDTH,pady=(15,0),padx=15,rowspan=HEIGHT,sticky='n')
        w.bind(RIGHT_CLICK,self.OnfigRightClick(self.Rfig))

        self.create_figure_rightclick_menu()

    def create_widgets(self):
        ""
        COL = 2
        HEIGHT = 55
        WIDTH = 16
        self.create_treeview(width=300)
        self.create_editmeatainfo_widgets(COL+1,HEIGHT + 13)
        self.create_metainfo_widgets(COL+1,HEIGHT + 1)
        
   
        
        # init parameters

        self.plot_params = {i:tk.DoubleVar() for i in ['Rymin','Rymax','Tymin','Tymax']}
        self.plot_params['RLS'] = tk.StringVar()
        self.plot_params['RLS'].set('-')
        self.plot_params['TLS'] = tk.StringVar()
        self.plot_params['TLS'].set('-')
        self.plot_params['transformer'] = tk.StringVar()
        self.plot_params['transformer'].set(list(transformers.keys())[0])
        self.plot_params['algorithm'] = tk.StringVar()
        self.plot_params['algorithm'].set(list(algorithm.keys())[0])
        self.plot_params['showGrid'] = tk.IntVar()

        lineStyles = ['-',':','.',',']
        pp = self.plot_params
        tk.Checkbutton(self, text='Show Grid', variable=pp['showGrid']).grid(
            row=HEIGHT + 14, column=COL+1,padx=10,pady=10,sticky='we')
        tk.Label(self,text='Ymin').grid(column=COL+6, padx=(10,0), row = HEIGHT + 1,sticky='w')
        tk.Label(self,text='Ymax').grid(column=COL+6,padx=(10,0),  row = HEIGHT + 2,sticky='w')
        tk.Label(self,text='Style').grid(column=COL+6,padx=(10,0), row = HEIGHT + 3,sticky='w')
        tk.Entry(self,textvariable=pp['Rymin'],width=8).grid(column=COL+6,row=HEIGHT+1,padx=(60,20),sticky='we')
        tk.Entry(self,textvariable=pp['Rymax'],width=8).grid(column=COL+6,row=HEIGHT+2,padx=(60,20),sticky='we')
        tk.OptionMenu(self,pp['RLS'],*lineStyles).grid(column=COL+6,row=HEIGHT+3,padx=(60,20),sticky='we')
        tk.Label(self,text='Ymin').grid(column=COL+7,row = HEIGHT + 1,sticky='w')
        tk.Label(self,text='Ymax').grid(column=COL+7,row = HEIGHT + 2,sticky='w')
        tk.Label(self,text='Style').grid(column=COL+7,row = HEIGHT + 3,sticky='w')
        tk.Entry(self,textvariable=pp['Tymin'],width=8).grid(column=COL+7,row=HEIGHT+1,padx=(40,20),sticky='we')
        tk.Entry(self,textvariable=pp['Tymax'],width=8).grid(column=COL+7,row=HEIGHT+2,padx=(40,20),sticky='we')
        tk.OptionMenu(self,pp['TLS'],*lineStyles).grid(column=COL+7,row=HEIGHT+3,padx=(40,20),sticky='we')
        for i in self.plot_params.values():
            i.trace_id = i.trace('w', lambda *x:self.plotFigure())

        tk.Button(self,text = 'Load Saved Model',command=self.loadSavedModelCb).grid(column=COL+6,row=HEIGHT+4,columnspan=2,sticky='we',padx=60,pady=(10,0))
        self.predictBtn = tk.Button(self,text = "Run Prediction",command = self.predictBtnCb)
        self.predictBtn.grid(column=COL+6,row=HEIGHT+5,columnspan=2,sticky='we',padx=60,pady=(10,10))
        self.predictBtn['state'] = 'disabled'


        tk.Label(self,text='Transform').grid(column=COL+8, padx=(10,0), row = HEIGHT + 1,sticky='w')
        tk.Label(self,text='Algorithm').grid(column=COL+8, padx=(10,0), row = HEIGHT + 2,sticky='w')
        tk.OptionMenu(self,pp['transformer'],*list(transformers.keys())).grid(column=COL+8,row=HEIGHT+1,padx=(90,20),sticky='we')
        tk.OptionMenu(self,pp['algorithm'],*list(algorithm.keys())).grid(column=COL+8,row=HEIGHT+2,padx=(90,20),sticky='we')
        
        self.fitBtn = tk.Button(self,text = 'Fit Model', command = self.fitBtnCb)
        self.fitBtn.grid(column = COL+8,row = HEIGHT+3,sticky='we',padx = 30,pady=(10,0))
        self.saveModelBtn = tk.Button(self, text="Save Model",command = self.saveModelBtnCb)
        self.saveModelBtn.grid(column=COL+8, row=HEIGHT+4,sticky='we',padx=30,pady=(10,0))
        self.saveModelBtn['state'] = 'disabled'
        tk.Button(self, text="Clear Prediction",command = self.clearPredictCb).grid(
                column=COL+8, row=HEIGHT+5,sticky='we',padx=30,pady=(10,0))
    
        self.create_message_box(rowstart=HEIGHT+6,columnstart=COL+6,width=80,height=20)

        self.displayMsg("> load data to start.")

    def get_plot_para(self):
        para = dict(zip(['Rymin','Rymax','Tymin','Tymax'],[0,0,0,0]))
        for k,i in self.plot_params.items():
            try:
                para[k]=i.get()
            except:
                continue
        return para

    def plotFigure(self):
        data = self.getAllTreeSelectionData()
        if not data: return 
        self.Rax.clear()
        self.Tax.clear()
        self.Rax.set_title('Raw Data')
        self.Tax.set_title('Transformed Data')
        self.Rax.set_xlabel('Time / mins')
        self.Rax.set_ylabel('Signal / uA')
        self.Tax.set_xlabel('First Dimension')
        self.Tax.set_ylabel('Value')
        params = self.get_plot_para()   
        self.Tax.grid(params['showGrid'])
        self.Rax.grid(params['showGrid'])

        for _ in 'RT':
            if params[f'{_}ymin']<params[f'{_}ymax']:
                getattr(self,f'{_}ax').set_ylim([params[f'{_}ymin'],params[f'{_}ymax']])
        
        if self.trained_model:
            transformer = self.trained_model[0:-1]
        else:
            transformer = transformers[params['transformer']]()

        labels = set()
        for d in data:
            mark = d.get('userMarkedAs',None) or "?"
            color = {'positive':'green','negative':'red'}.get(mark,'black')
            
            if mark in labels:
                mark = None
            else:            
                labels.add(mark)

            # plot raw data
            t = timeseries_to_axis(d['data']['time'])
            c = [i['pc'] for i in d['data']['fit']]
            facecolor = None if params['RLS'] == ',' else 'white'
            self.Rax.plot(t,c,params['RLS'],color = color, markerfacecolor = facecolor,label = mark)
            
            try:
                X = np.empty((1,2),dtype=list)
                X[0] = [t,c]
                X_trans = transformer.transform(X)[0]
                facecolor = None if params['TLS'] == ',' else 'white'
                self.Tax.plot(X_trans,params['TLS'],color = color, markerfacecolor = facecolor,label=mark)
            except Exception as e:
                self.Tax.set_title('Transform Failed.')
                self.displayMsg(f"{e}")

        self.Tax.legend()
        self.Rax.legend()
        
        self.canvas.draw()
        
    def treeviewselect_cb(self,e):
        self.updateInfo()
        self.plotFigure()

    def loadSavedModelCb(self):
        file = tk.filedialog.askopenfilename(title=f'Open Fitted Model',
                filetypes=[('Fitting Model','*.model'),],
                initialdir=self.targetFolder,defaultextension='.model')     
        if file:
            self.trained_model = load_model(file)
            self.predictBtn['state'] = 'normal'


    def predictBtnCb(self):
        ""
        def predict():
            self.datasource.predict(self.trained_model,callback = self.displayMsg)
            self.updateTreeviewMenu()
        Thread(target=predict,).start()
        
        

    def fitBtnCb(self):
        model = self.plot_params['algorithm'].get()
        transform = self.plot_params['transformer'].get()
        def fitting(model,transform):
            self.displayMsg('Fitting model...')
            X,y = self.datasource.exportXy()
            if len(y)<=2:
                self.displayMsg('Not enough data available for training...')
                return 
            self.displayMsg(f'Data contain {len(y)} datapoints, {y.sum()} positive, {len(y)-y.sum()} negative.')
            self.trained_model = train_model(transform,model,X,y)
            self.displayMsg(f"Training result: {self.trained_model}")
            fold = 5
            p,r = cross_validation(self.trained_model,X,y,fold)
            self.displayMsg(f"{fold}-fold Cross validation...")
            self.displayMsg(f"Precision: {', '.join(f'{i:.3f}' for i in p)}")
            self.displayMsg(f"Recall:    {', '.join(f'{i:.3f}' for i in r)}")
            self.displayMsg('Fitting Done.')
            self.saveModelBtn['state'] = 'normal'
            self.predictBtn['state'] = 'normal'

        Thread(target=fitting,args=(model,transform)).start()

    def saveModelBtnCb(self):
        file = tk.filedialog.asksaveasfilename(title=f'Save Fitted Model',
                filetypes=[('Fitting Model','*.model'),],
                initialdir=self.datasource.picklefolder,defaultextension='.model')     
        if file:
            save_model(self.trained_model,file)
            self.saveModelBtn['state'] = 'disabled'


    def clearPredictCb(self):
        for d in self.datasource.rawView.get('data',[]):
            d['predictAs'] = None
        for k in self.datasource.pickles.values():
            k['modified'] = True
        self.updateTreeviewMenu()




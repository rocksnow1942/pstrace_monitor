import tkinter as tk
import platform
from views import ViewerTab,__version__
import json
from pathlib import Path
import os

"""
For data viewer app.
"""


class Void:
    def __getattr__(self,name):
        return None

class ViewerApp(tk.Tk):
    isMAC = 'darwin' in platform.platform().lower()
    def __init__(self):
        super().__init__()

        self.title(f"PSTrace Viewer @ {__version__}")
        self.geometry('+40+40')
        self.load_settings()

          # development code:
        # rememb file history
        history = self.settings.get('PStrace History',[])
        self.settings['PStrace History'] = [ i for i in history if os.path.exists(i)]
        # self.datasource.load_picklefiles(self.settings['PStrace History'])
        # self.datasource.load_picklefiles(['/Users/hui/Downloads/2020-06-05/2020-06-05_pstraces.pickle'])
        # self.updateTreeviewMenu()
        self.viewer = ViewerTab(parent=self,master=self)
        self.viewer.pack()

        self.create_menus()
        
        self.monitor=Void()
        self.pico=Void()


    def on_closing(self):
        "handle window closing. clean up shit"
        if self.viewer.needToSave:
            confirm = tk.messagebox.askquestion('Unsaved data',
                "You have unsaved data, do you want to save?",icon='warning')
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

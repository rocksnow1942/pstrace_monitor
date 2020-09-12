import matplotlib
from views import ViewerApp


"""
for run the viewr app along.
"""



if __name__ == "__main__":
    matplotlib.use('TKAgg')
    app = ViewerApp()
    app.protocol('WM_DELETE_WINDOW',app.on_closing)
    app.mainloop()

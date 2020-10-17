import matplotlib
from views import TrainerApp


"""
for run the viewr app along.
"""



if __name__ == "__main__":
    matplotlib.use('TKAgg')
    app = TrainerApp()
    app.protocol('WM_DELETE_WINDOW',app.on_closing)
    app.mainloop()

import matplotlib
import multiprocessing as mp
from views import Application

# TODO:
# add wait on default covid trace.



if __name__ == "__main__":
    matplotlib.use('TKAgg')
    mp.set_start_method('spawn')
    app = Application()
    app.protocol('WM_DELETE_WINDOW',app.on_closing)
    app.mainloop()

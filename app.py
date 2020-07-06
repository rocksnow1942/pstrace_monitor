import matplotlib
import multiprocessing as mp
from views import Application

# TODO:
# BUgs
# can not reproduce multi replicate pstrace bug seen on widowns.


if __name__ == "__main__":
    matplotlib.use('TKAgg')
    mp.set_start_method('spawn')
    app = Application()
    app.protocol('WM_DELETE_WINDOW',app.on_closing)
    app.mainloop()

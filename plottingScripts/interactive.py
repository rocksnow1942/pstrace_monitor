import pandas as pd
import seaborn as sns
import scipy.stats as stat
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from itertools import chain, islice
import json


class AnnoteFinder(object):
    """callback for matplotlib to display an annotation when points are
    clicked on.  The point which is closest to the click and within
    xtol and ytol is identified.
    
    Register this function like this:
    
    scatter(xdata, ydata)
    af = AnnoteFinder(xdata, ydata, annotes)
    connect('button_press_event', af)
    """

    def __init__(self, data, x, y, ax=None, axes=None):
        self.data = data
        self.x = x
        self.y = y
        
        self.ax = ax
        self.axes = axes

        self.drawnAnnotations = {}
        self.links = []
        

    def distance(self, x1, x2, y1, y2):
        """
        return the distance between two points
        """
        return(math.sqrt((x1 - x2)**2 + (y1 - y2)**2))

    def __call__(self, event):
        
        if event.inaxes: # and (self.ax is event.inaxes):
            print(event)            
            clickX = round(event.xdata)
            clickY = round(event.ydata)
            annotes = []
            # print(event.xdata, event.ydata)
            ct = self.x[clickX]
            sd = self.y[clickY]
        
            self.drawAnnote(clickX, clickY, f"{self.data[clickY][clickX]:.3f}\nct {ct:.1f}\nsd {sd:.3f}")
            
        else:
            for pos in self.drawnAnnotations:
                self.drawAnnote(*pos, '')
        

    def drawAnnote(self, x, y, annote):
        """
        Draw the annotation on the plot
        """
        if (x, y) in self.drawnAnnotations:
            markers = self.drawnAnnotations[(x, y)]
            for m in markers:
                m.set_visible(annote and not m.get_visible())
            self.ax.figure.canvas.draw_idle()
        else:
            t = self.ax.text(x, y, annote, color='white', fontsize=8)
            m = self.ax.scatter([x], [y], marker='+', c='r', zorder=100)
            self.drawnAnnotations[(x, y)] = (t, m)
            self.ax.figure.canvas.draw_idle()

    def drawSpecificAnnote(self, annote):
        annotesToDraw = [(x, y, a) for x, y, a in self.data if a == annote]
        for x, y, a in annotesToDraw:
            self.drawAnnote(self.ax, x, y, a)


with open('matrixFull.json','rt') as f:
    resultMatrix = np.array(json.load(f))




ctT = 30
sdT = 0.106382
prT = 0.2


ctRange = np.linspace(15, 30, resultMatrix[0].shape[1])
sdRange = np.linspace(0.06, 0.18, resultMatrix[0].shape[0])
ratio = resultMatrix[0].shape[1] / resultMatrix[0].shape[0]

def onpick3(event):
   ind = event.ind
   print('onpick3 scatter:', ind)

fig, axes = plt.subplots(2, 3, figsize=(12, 8), facecolor='lightgray')

axes = [i for j in zip(*axes) for i in j]

labels = ['Positive','Negative']
items = ['Precision', 'Recall', 'F1 Score']
for i, ax in enumerate(axes):
   itemIdx, labelIdx = divmod(i, 2)
   label = labels[labelIdx]
   item = items[itemIdx]
   ax.imshow(resultMatrix[i], aspect=ratio)
   ax.set_title(f'{label} {item}')

   xtick = [i for i in np.linspace(0, len(ctRange)-1, 16)]

   ax.set_xticks(xtick)
   ax.set_xticklabels([f"{ctRange[int(i)]:.0f}" for i in xtick], rotation=45)
   ax.set_xlabel('Ct / min' )

   ytick = [int(i) for i in np.linspace(0, len(sdRange)-1, 15)]
   ax.set_yticks(ytick)
   ax.set_yticklabels([f"{sdRange[i]:.3f}" for i in ytick])
   ax.set_ylabel('SD')
   af =  AnnoteFinder(data = resultMatrix[i], x=ctRange, y=sdRange ,ax = ax, axes=axes)
   fig.canvas.mpl_connect('button_press_event', af)

    

plt.tight_layout()

plt.show()




# 
# from matplotlib.pyplot import figure, show
# import numpy as npy
# from numpy.random import rand
# 
# 
# if 1: # picking on a scatter plot (matplotlib.collections.RegularPolyCollection)
# 
#     x, y, c, s = rand(4, 100)
#     def onpick3(event):
#         ind = event.ind
#         print('onpick3 scatter:', ind, npy.take(x, ind), npy.take(y, ind))
# 
#     fig = figure()
#     ax1 = fig.add_subplot(111)
#     col = ax1.scatter(x, y, 100*s, c, picker=True)
#     #fig.savefig('pscoll.eps')
#     fig.canvas.mpl_connect('pick_event', onpick3)
# 
# show()
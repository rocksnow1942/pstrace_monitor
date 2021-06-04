from utils._util import ViewerDataSource
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from utils.calling_algorithm import *
from sklearn.metrics import precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score,StratifiedKFold
from sklearn.base import BaseEstimator, TransformerMixin, clone
from scipy import signal
from sklearn.tree import DecisionTreeClassifier
from sklearn.tree import export_graphviz
import pydot
import subprocess
import glob
import os
import textwrap
import csv
from itertools import combinations

def removeDuplicates(X,y,name):
    currents = set()
    ids = []
    for t,c in X:
        if sum(c) in currents:
            ids.append(False)
        else:
            ids.append(True)
            currents.add(sum(c))
    return X[ids],y[ids],name[ids]
        

def findTimeVal(t,val,t0,dt):
    t0idx = int((t0 - t[0]) / (t[-1]-t[0]) * len(val))
    t1idx = int((t0 +dt - t[0]) / (t[-1]-t[0]) * len(val))
    return val[t0idx:t1idx]

 

# pickle file to plot data from
"""
██████╗ ██╗ ██████╗██╗  ██╗██╗     ███████╗███████╗██╗██╗     ███████╗
██╔══██╗██║██╔════╝██║ ██╔╝██║     ██╔════╝██╔════╝██║██║     ██╔════╝
██████╔╝██║██║     █████╔╝ ██║     █████╗  █████╗  ██║██║     █████╗  
██╔═══╝ ██║██║     ██╔═██╗ ██║     ██╔══╝  ██╔══╝  ██║██║     ██╔══╝  
██║     ██║╚██████╗██║  ██╗███████╗███████╗██║     ██║███████╗███████╗
╚═╝     ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝╚══════╝╚══════╝
"""                                                                      
picklefile = r"C:\Users\hui\Desktop\non dtt buffer.picklez"



dataSource = ViewerDataSource()
pickleFiles = [picklefile]
dataSource.load_picklefiles(pickleFiles)
X,y,names = dataSource.exportXy()
X,y,names = removeDuplicates(X,y,names)

print('Total curve count is : '+str(len(X)))
print("Total Positive Data: "+str(sum(y)))
print("Total Negative Data: "+str(len(y)-sum(y)))



cutoffStart = 5
cutoffEnd = 30
normStart = 5
normEnd = 10

smoothT =  Pipeline([
    ('smooth',Smoother(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('remove time',RemoveTime()),
])

deriT =  Pipeline([
    ('smooth',Smoother(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('Derivitive',Derivitive(window=31,deg=3)),
    # ('remove time',RemoveTime()),
])


peaksT = Pipeline([
    ('smooth',Smoother(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('Derivitive',Derivitive(window=31,deg=3)),
    ('peak',FindPeak())
    # ('remove time',RemoveTime()),
])



smoothed_X = smoothT.transform(X)
deri_X = deriT.transform(X)
peaks_X = peaksT.transform(X)






#############################################################################
# plot the data                                                             #                              
# overwrite column numbers; set to 0 to determine automatically             #                     
#                                                                           #                         
# ██████╗ ██╗      ██████╗ ████████╗██████╗  █████╗ ██████╗  █████╗         #                    
# ██╔══██╗██║     ██╔═══██╗╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗        #                    
# ██████╔╝██║     ██║   ██║   ██║   ██████╔╝███████║██████╔╝███████║        #                    
# ██╔═══╝ ██║     ██║   ██║   ██║   ██╔═══╝ ██╔══██║██╔══██╗██╔══██║        #                    
# ██║     ███████╗╚██████╔╝   ██║   ██║     ██║  ██║██║  ██║██║  ██║        #                    
# ╚═╝     ╚══════╝ ╚═════╝    ╚═╝   ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝        #                                                                                     
# This set how many columns in the figure, set to 0 automatically determine.#                          
col = 0      
# ymin and ymax is the min and max of y axis
ymin = 0.3
ymax = 1.3                                             
#############################################################################


col = col or int(len(y)**0.5)
row = int(np.ceil(len(y) / col))

fig,axes = plt.subplots(row,col,figsize=(col*4,row*3))
axes = [i for j in axes for i in j]

for i,j in enumerate(y):
    ax = axes[i]
    smoothed_c = smoothed_X[i]
    t,deri,_ =  deri_X[i]
    left_ips,peak_prominence,peak_width, *sd= peaks_X[i]
    curvePeakRange = findTimeVal(t,smoothed_c,left_ips,peak_width)
    xvals = np.linspace(t[0],t[-1],len(deri)) 
    ax.plot(xvals,smoothed_c,color='red' if y[i] else 'green')    
    ax.plot(np.linspace(left_ips,left_ips+peak_width,len(curvePeakRange)) ,curvePeakRange,linewidth=4,alpha=0.75,color='cyan')
    # set plot y axis limits
    ax.set_ylim([ymin,ymax])    
    
    ax.plot(xvals,(deri - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c),'--',alpha=0.8)
    
    p_n = 'Positive' if y[i] else 'Negative'
    ax.set_title(f'Ct:{left_ips:.1f} Pm:{peak_prominence*100:.2f} M:{p_n}',
                    fontdict={'color':'red' if y[i] else 'green'})
    ax.set_xlabel('\n'.join(textwrap.wrap(names[i].strip(),width=45)),fontdict={'fontsize':10})

plt.tight_layout()


# save to figure
fig.savefig(picklefile+'.svg')






features =['Ct','Prominence','Peak_Width','SD_Peak_Width','SD_3min','SD_5min','SD_10min','SD_15min','SD_End']


# write result to csv file
with open(f'{picklefile}.csv','w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Name','P/N']+features)
    for i,j in enumerate(y):
        name = names[i].strip()
        _ = list(peaks_X[i])        
        writer.writerow([name,'Positive' if j else 'Negative'] + _)
        


# plot scatter plot of different features
fig,axes = plt.subplots(6,6,figsize=(22,20))
axes = [i for j in axes for i in j]
for (i,j),ax in zip(combinations(range(9),2),axes):
    il = features[i]
    jl = features[j]
    ax.plot(peaks_X[y==0,i],peaks_X[y==0,j],'gx',label='Negative')
    ax.plot(peaks_X[y==1,i],peaks_X[y==1,j],'r+',label='Positive')
    ax.set_title(f'{il} vs {jl}')
    ax.set_xlabel(il)
    ax.set_ylabel(jl)
    ax.legend()
    
plt.tight_layout()
fig.savefig(picklefile+'scatter.svg')
    
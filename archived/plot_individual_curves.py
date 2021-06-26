import sys
sys.path.append('../')
from utils._util import ViewerDataSource
import json,os
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
import textwrap
import seaborn as sns
import pandas as pd
from collections import defaultdict
from scipy.optimize import least_squares


def export_tree_graph(clf,feature_names,class_names,filename='new_tree'):
    export_graphviz(clf,out_file='temp_tree.dot',
    feature_names=feature_names,class_names=class_names,rounded=True,filled=True)
    subprocess.run(['dot','-Tpng','temp_tree.dot','-o',filename+'.png'])

def findTimeVal(t,val,t0,dt):
    t0idx = int((t0 - t[0]) / (t[-1]-t[0]) * len(val))
    t1idx = int((t0 +dt - t[0]) / (t[-1]-t[0]) * len(val))
    return val[max(0,t0idx):t1idx]
def findTimeIdx(t,value):
    return np.abs(t-value).argmin()
    


def get_picklez(folder):
    fs = []
    for root,fds,files in os.walk(folder):        
        for f in files:
            if f.endswith('picklez'):
                fs.append(os.path.join(root,f))
    return fs
    

def jitter(values,j):
    return values + np.random.normal(0,j,values.shape)
         

def prediction(Ct,prominence):
    def predictor(X):
        return np.apply_along_axis(lambda x: int(x[0]<=Ct and x[1]>=prominence),1,X)
    return predictor
    
def extract_copy(name):
    if '100c' in name.lower():
        return '100cp'
    elif '50c' in name.lower():
        return '50cp'
    elif '25c' in name.lower():
        return '25cp'
    elif 'ntc' in name.lower():
        return 'NTC'
    elif '300c' in name.lower():
        return '300cp'
    else:
        return name
        
def extract_saliva(name):
    name = name.lower()
    if 'hi-ps' in name:
        return 'HI-PS'
    if 'dsm' in name:
        return 'DSM'
    if 'u-ps' in name:
        return 'U-PS'
    return 'Unknown'


files = [ 
"/Users/hui/AMS_RnD/Projects/LAMP-Covid Sensor/Data Export/20210625/20210625 NTC vs PTC.picklez"
]

dataSource = ViewerDataSource()
pickleFiles = [*files] #r"C:\Users\hui\Desktop\saved.picklez"
dataSource.load_picklefiles(pickleFiles)
X,y,names,devices = dataSource.exportXy()

X,y,names,devices = removeDuplicates(X,y,names,devices)



print('X data length is : '+str(len(X)))
print('y data length is : '+str(len(y)))
print("Total Positive Data: "+str(sum(y)))
print("Total Negative Data: "+str(len(y)-sum(y)))

cutoffStart = 5
cutoffEnd = 30
normStart = 5
normEnd = 10

normalT = Pipeline([    
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),    
    ('remove time', RemoveTime()),
])
normed_X = normalT.transform(X)

smoothT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('remove time', RemoveTime()),
])
smoothed_X = smoothT.transform(X)

deriT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    # ('remove time',RemoveTime()),
])
deri_X = deriT.transform(X)

tCtT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('thresholdCt',ThresholdCt())
    # ('remove time',RemoveTime()),
])
tCt_X = tCtT.transform(X)


tCtPredictT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('thresholdCt',ThresholdCt()),
    ('predictor',CtPredictor(ct=23,prominence=0.2,sd=0.131))
])
pred_X = tCtPredictT.transform(X)



hCtT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('logCt',HyperCt()),
    
])
hCtT_X = hCtT.transform(X)

hCtTPredictT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('logCt',HyperCt()),
    ('predictor',CtPredictor(ct=20.4,prominence=0.4,sd=0.131))
])
hCtpred_X = hCtTPredictT.transform(X)



# plot traces with second derivative peak

i = idx = 14

prAndSDPos = 'left' # position the prominence and sD label at left or center

t,gradient,pc = deri_X[i]

heightlimit = np.quantile(np.absolute(gradient[0:-1] - gradient[1:]), 0.9)
peaks,props = signal.find_peaks(gradient,prominence=heightlimit,width= len(gradient) * 0.05, rel_height=0.5)

tspan = t[-1]-t[0]
normalizer =  tspan / len(gradient) 
mpi = props['prominences'].argmax()
peak_pos = peaks[mpi] * normalizer + t[0]
left_base = props['left_bases'][mpi]* normalizer + t[0]
right_base = props['right_bases'][mpi]* normalizer + t[0]
peak_index = peaks[mpi]
props


smoothed_c = smoothed_X[i]
t,deri,_ =  deri_X[i]
left_ips,peak_prominence,peak_width, *sd= hCtT_X[i]   


fig,ax = plt.subplots(figsize=(8,6))

ax.set_ylim([0.4,1.3])
ax.set_xlim([4.5,30.5])

xvals = np.linspace(t[0],t[-1],len(deri))


t_idx = findTimeIdx(np.array(X[i][0]),5)

# plot raw data
ax.plot(X[i][0][t_idx:],normed_X[i][t_idx:],'o',markeredgecolor='dodgerblue',markerfacecolor='white',label='Raw Data',alpha=0.75)
# plot smoothed current
ax.plot(xvals,smoothed_c,color='royalblue',linewidth=2,label='Smoothed',alpha=0.7)


# transform derivative peak so that they can be ploted together.
derivative_transform = lambda x:(x - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c)

# plot plot the derivative peaks
ax.plot(xvals,derivative_transform(deri),'--',color='tomato',alpha=0.8,label='2nd Derivative')
# # plot linear fitting line
# ax.plot(xvals,thresholdline(xvals),'b-.',alpha=0.7)
# ax.plot([thresholdCt,thresholdCt],[0,2],'b-.',linewidth=1,alpha=0.7)    
# plot hyperbolic fitting line
hyperline = HyperCt.hyperF(None,hCtT_X[i][-4:-1])
ax.plot(xvals,hyperline(xvals),'--',color='fuchsia',alpha=0.7,linewidth=2,label='Hyperbolic Fit')

#plot ct line
# hyper ct
hyperCt = hCtT_X[i][-1]
ax.plot([hyperCt,hyperCt],[0,2],'k-.',alpha=0.7,linewidth=2, )
ax.text(hyperCt+0.25,0.45,f"Ct: {hyperCt:.1f}'",fontdict=dict(fontsize=14))


# plot 2nd derivative peak prominence
ax.plot([left_base,peak_pos],[derivative_transform(deri[peak_index] - peak_prominence/100),
        derivative_transform(deri[peak_index] - peak_prominence/100)],color='limegreen',linewidth=1)
prLow,prHigh = derivative_transform(np.array([deri[peak_index] - peak_prominence/100 ,deri[peak_index]]))
ax.annotate('',xy=[peak_pos,prLow],
xytext=[peak_pos,prHigh],xycoords='data',textcoords='data',ha='left',va='center',
arrowprops=dict(arrowstyle='<->',edgecolor='limegreen')
)
ax.text(peak_pos,prHigh+0.02,f'Prominence: {peak_prominence:.2f}',
        fontdict=dict(fontsize=14),ha=prAndSDPos)

ax.plot([peak_pos,peak_pos],)

# plot signal drop at 5min
sdstartIdx = findTimeIdx(left_ips,xvals)
sdendIdx = findTimeIdx(left_ips+5,xvals)
ax.plot([left_ips,left_ips+5],[smoothed_c[sdstartIdx],smoothed_c[sdstartIdx]],linewidth=1,color='teal')
ax.annotate('',xy=[left_ips+5,smoothed_c[sdendIdx]],
xytext=[left_ips+5,smoothed_c[sdstartIdx]],ha='left',va='center',xycoords='data',textcoords='data',
arrowprops=dict(arrowstyle='<->',edgecolor='teal')
)
ax.text(left_ips+5.2, smoothed_c[sdendIdx]+( 0.02 if prAndSDPos=='left' else -0.02 ),
        f'SD@5min: {sd[2]:.2f}',fontdict=dict(fontsize=14),ha=prAndSDPos,va='bottom' if prAndSDPos=='left' else 'top')


ax.set_title('Negative Curve')
ax.set_ylabel('Electrochemical Signal (normalized)')
ax.set_xlabel('Time (Minutes)')

ax.legend()        
plt.tight_layout()

fig.savefig('early positive.svg')










# plot full negative curve, no second derivative peak

i = idx = 4


t,gradient,pc = deri_X[i]

smoothed_c = smoothed_X[i]
t,deri,_ =  deri_X[i]
left_ips,peak_prominence,peak_width, *sd= hCtT_X[i]   


fig,ax = plt.subplots(figsize=(8,6))

ax.set_ylim([0.4,1.3])
ax.set_xlim([4.5,30.5])

xvals = np.linspace(t[0],t[-1],len(deri))


t_idx = findTimeIdx(np.array(X[i][0]),5)

# plot raw data
ax.plot(X[i][0][t_idx:],normed_X[i][t_idx:],'o',markeredgecolor='dodgerblue',markerfacecolor='white',label='Raw Data',alpha=0.75)
# plot smoothed current
ax.plot(xvals,smoothed_c,color='royalblue',linewidth=2,label='Smoothed',alpha=0.7)


# transform derivative peak so that they can be ploted together.
derivative_transform = lambda x:(x - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c)

# plot plot the derivative peaks
ax.plot(xvals,derivative_transform(deri),'--',color='tomato',alpha=0.8,label='2nd Derivative')
# # plot linear fitting line
# ax.plot(xvals,thresholdline(xvals),'b-.',alpha=0.7)
# ax.plot([thresholdCt,thresholdCt],[0,2],'b-.',linewidth=1,alpha=0.7)    
# plot hyperbolic fitting line
hyperline = HyperCt.hyperF(None,hCtT_X[i][-4:-1])
ax.plot(xvals,hyperline(xvals),'--',color='fuchsia',alpha=0.7,linewidth=2,label='Hyperbolic Fit')

#plot ct line
# hyper ct
hyperCt = hCtT_X[i][-1]
ax.plot([hyperCt,hyperCt],[0,2],'k-.',alpha=0.7,linewidth=2, )
ax.text(hyperCt+0.25,0.45,f"Ct: {hyperCt:.1f}'",fontdict=dict(fontsize=14))




tp_n = '+' if pred_X[i][0] else '-'

hp_n = '+' if hCtpred_X[i][0] else '-'

ax.set_title('Negative Curve')
ax.set_ylabel('Electrochemical Signal (normalized)')
ax.set_xlabel('Time (Minutes)')

ax.legend()        
plt.tight_layout()
fig.savefig('full negative.svg')
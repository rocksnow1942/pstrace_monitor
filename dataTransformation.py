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


def export_tree_graph(clf,feature_names,class_names,filename='new_tree'):
    export_graphviz(clf,out_file='temp_tree.dot',
    feature_names=feature_names,class_names=class_names,rounded=True,filled=True)
    subprocess.run(['dot','-Tpng','temp_tree.dot','-o',filename+'.png'])

def findTimeVal(t,val,t0,dt):
    t0idx = int((t0 - t[0]) / (t[-1]-t[0]) * len(val))
    t1idx = int((t0 +dt - t[0]) / (t[-1]-t[0]) * len(val))
    return val[max(0,t0idx):t1idx]



    

def prediction(Ct,prominence):
    def predictor(X):
        return np.apply_along_axis(lambda x: int(x[0]<=Ct and x[1]>=prominence),1,X)
    return predictor
    
files = glob.glob('/Users/hui/AMS_RnD/Projects/LAMP-Covid Sensor/CapCaTTrainingData_DomeDesign/ProcessedData/!FronzenData_DONTCHANGE/*.picklez')
 
f1 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_0525_export.picklez"
f2 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210520_PnD_export.picklez"
f3 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_SelectiveExportWithPatientCurves.picklez"

f7 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210601_0602.picklez"
f8 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210603\20210603 NTC vs 100cp.picklez"
f9 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210604\20210604 NTC vs PTC.picklez"

dataSource = ViewerDataSource()
pickleFiles = [f7,f8,f9] #r"C:\Users\hui\Desktop\saved.picklez"
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

smoothT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('remove time', RemoveTime()),
])

deriT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    # ('remove time',RemoveTime()),
])


peaksT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak())
    # ('remove time',RemoveTime()),
])

tCtT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('thresholdCt',ThresholdCt())
    # ('remove time',RemoveTime()),
])

tCtPredictT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('thresholdCt',ThresholdCt()),
    ('predictor',CtPredictor(ct=25,prominence=0.2,sd=0.1))
])

smoothed_X = smoothT.transform(X)
deri_X = deriT.transform(X)
peaks_X = peaksT.transform(X)
tCt_X = tCtT.transform(X)

pred_X = tCtPredictT.transform(X)






col = int(len(y)**0.5)
col=2
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
    # plot the signal drop part
    ax.plot(np.linspace(left_ips,left_ips+peak_width,len(curvePeakRange)) ,curvePeakRange,linewidth=4,alpha=0.75 )
    ax.set_ylim([0.4,1.3])
    # deriviative = (smoothed_c[1:]-smoothed_c[0:-1]) / 0.3333333
    # secderivative = (deriviative[1:]-deriviative[0:-1]) / 0.3333333     
    ax.plot(xvals,(deri - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c),'--',alpha=0.8)
    p_n = 'Positive' if y[i] else 'Negative'
    ax.set_title(f'{i}-Ct:{left_ips:.1f} Pm:{peak_prominence:.2f} M:{p_n}',
    fontdict={'color':'red' if y[i] else 'green'})
    ax.set_xlabel(names[i],fontdict={'fontsize':8})
# ax.set_ylim([-1,1])
plt.tight_layout()

# fig.savefig(r"C:\Users\hui\Desktop\Data till 6/3.png")

 
 
# different way to determine Ct by curve fitting and intersection.
fitwindow = 4
smoothed_c = smoothed_X[i]
left_ips,peak_prominence,peak_width, *sd= peaks_X[i]
t,deri,_ =  deri_X[i]






 
# use the threshold method to calculate Ct without plotting
result = []
degree = 1
fitwindow = 4
for i,j in enumerate(y):        
    t,deri,smoothed_c =  deri_X[i]
    left_ips,peak_prominence,peak_width, *sd= peaks_X[i]
    
    tofit = findTimeVal(t,smoothed_c,left_ips-fitwindow,fitwindow)    
    # find the threshold Ct
    fitpara = np.polyfit(np.linspace(max(left_ips-4,t[0]),left_ips,len(tofit)),np.array(tofit,dtype=float),deg=degree)
    
    threshold = (tofit[-1]) * 0.05
    thresholdline = np.poly1d(fitpara + np.array([0]*degree +[-threshold] ))    
    tosearch = findTimeVal(t,smoothed_c,left_ips,t[-1])
    tosearchT = np.linspace(left_ips,30,len(tosearch))
    thresholdSearch = thresholdline(tosearchT) - findTimeVal(t,smoothed_c,left_ips,30)
    thresholdCt = left_ips
    for sT,sthre in zip(tosearchT,thresholdSearch):        
        if sthre > 0:
            break
        thresholdCt = sT            
    curvePeakRange = findTimeVal(t,smoothed_c,left_ips,peak_width)
    xvals = np.linspace(t[0],t[-1],len(deri))     
    p_n = 'Positive' if y[i] else 'Negative'    
    result.append([p_n,left_ips,thresholdCt,devices[i]])


tCt_X[0][-3:-1]

# use the threshold method to calculate Ct
col = int(len(y)**0.5)
col=4
row = int(np.ceil(len(y) / col))

result = []
fig,axes = plt.subplots(row,col,figsize=(col*4,row*3))
axes = [i for j in axes for i in j]
degree = 1
fitwindow = 4
for i,j in enumerate(y):
    ax = axes[i]
    ax.set_ylim([0.4,1.3])
    
    smoothed_c = smoothed_X[i]
    t,deri,_ =  deri_X[i]
    left_ips,peak_prominence,peak_width, *sd= peaks_X[i]
    
    tofit = findTimeVal(t,smoothed_c,left_ips-fitwindow,fitwindow)    
    # find the threshold Ct    
    thresholdline = np.poly1d(tCt_X[i][-3:-1])
    thresholdCt = tCt_X[i][-1]
    curvePeakRange = findTimeVal(t,smoothed_c,left_ips,peak_width)
    xvals = np.linspace(t[0],t[-1],len(deri)) 
    # plot smoothed current
    ax.plot(xvals,smoothed_c,color='red' if y[i] else 'green')
    # plot the signal drop part
    ax.plot(np.linspace(left_ips,left_ips+peak_width,len(curvePeakRange)) ,curvePeakRange,linewidth=4,alpha=0.75 )
    # plot plot the derivative peaks
    ax.plot(xvals,(deri - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c),'--',alpha=0.8)
    # ax.plot(xvals,fitres(xvals),'b-.')
    ax.plot(xvals,thresholdline(xvals),'b-.',alpha=0.7)
    ax.plot([thresholdCt,thresholdCt],[0,2],'k-')
    p_n = 'P' if pred_X[i][0] else 'N'
    ax.set_title(f'Ct:{left_ips:.1f} tCt:{thresholdCt:.1f} Pm:{peak_prominence:.2f} SD5:{sd[2]:.2f} P:{p_n}',
    fontdict={'color':'red' if y[i] else 'green','fontsize':10})
    ax.set_xlabel(names[i],fontdict={'fontsize':8})
    result.append([p_n,left_ips,thresholdCt,devices[i]])
# ax.set_ylim([-1,1])
plt.tight_layout()
fig.savefig('./alldata_tagential_predicted.svg')


import seaborn as sns
import pandas as pd
from collections import defaultdict

def jitter(values,j):
    return values + np.random.normal(0,j,values.shape)
 

dataframe = defaultdict(list)

for idx,(i,j,k,d) in enumerate(result):
    dataframe["label"].append(i)
    dataframe['delta'].append(k-j)
    dataframe['Ct'].append(j)
    dataframe['thresholdCt'].append(k)
    dataframe['prominence'].append(peaks_X[idx][1])
    dataframe['sdAt3min'].append(peaks_X[idx][4])
    dataframe['sdAt5min'].append(peaks_X[idx][5])
    dataframe['sdAt10min'].append(peaks_X[idx][6])
    dataframe['sdAt15min'].append(peaks_X[idx][7])
    dataframe['sdAtEnd'].append(peaks_X[idx][8])
    name = names[idx]
    dataframe['date'].append(name[0:8])
    
    if '100c' in name.lower():
        dataframe['copy'].append('100cp')
    elif '50cp' in name.lower():
        dataframe['copy'].append('50cp')
    elif '25cp' in name.lower():
        dataframe['copy'].append('25cp')
    elif 'ntc' in name.lower():
        dataframe['copy'].append('NTC')
    elif '300cp' in name.lower():
        dataframe['copy'].append('300cp')
    else:
        dataframe['copy'].append(name)


df = pd.DataFrame(dataframe)  


ax = sns.catplot(x="label",y="thresholdCt",data = df,hue='copy',kind='strip')
ax.savefig('thresholdCt_0604.svg')


fig,ax = plt.subplots(figsize=(8,6))
sns.swarmplot(x="label",y="thresholdCt",data = df,hue='Copy',size=2,dodge=True,ax=ax)
ax.legend(bbox_to_anchor=(1.2,0.95))





fig,ax = plt.subplots(figsize=(8,6))
sns.swarmplot(x="label",y=jitter(df["prominence"],0.02),data = df,hue='date',size=4,dodge=True,ax=ax)
ax.legend(bbox_to_anchor=(1.25,0.95))
ax.set_title('Prominence on different days')
plt.tight_layout()


df[''] = 'All Data'

fig,ax = plt.subplots(figsize=(8,6))
sns.swarmplot(x='',y=jitter(df["sdAt5min"],0.003),data = df,hue='copy',size=4,dodge=True,ax=ax)
ax.legend(bbox_to_anchor=(1.25,0.95))
ax.set_title('sdAt5min on different copy')
ax.grid()
ax.set_yticks(np.arange(0,0.35,0.02))
plt.tight_layout()



fig,ax = plt.subplots(figsize=(8,6))
sns.swarmplot(x="label",y="thresholdCt",data = df,hue='date',size=4,dodge=True,ax=ax)
ax.legend(bbox_to_anchor=(1.25,0.95))
ax.set_title('Threshold Ct on different days')
plt.tight_layout()


ax = sns.catplot(x="label",y="thresholdCt",data = df,hue='Copy',kind='strip')


ax = sns.catplot(x="label",y="CT",data = df,kind='swarm',hue='Copy')
ax.savefig('peakCt_0604.svg')


fig,ax = plt.subplots()
sns.swarmplot(y="label",x="Ct",data = df,ax=ax,hue='copy')



df[df.date=='20210604']["Ct"].shape

sns.scatterplot( x=jitter(df[df.date=='20210604']["Ct"],0.2), y=jitter(df[df.date=='20210604']["sdAt5min"],0.01), hue="copy" ,data=df)


sns.scatterplot( x=jitter(df[df.date.isin(['20210603'])]["thresholdCt"],0.1), y=jitter(df["sdAt5min"],0.0), hue="copy" ,data=df)


fig,ax = plt.subplots(figsize=(8,6))
sns.scatterplot( x=jitter(df[df.label=='Negative']["thresholdCt"],0.2), y=jitter(df["sdAt5min"],0.0), hue="copy" ,data=df,ax=ax)
ax.grid()
ax.set_title('Threshold Ct vs Signal drop at 5min all data')









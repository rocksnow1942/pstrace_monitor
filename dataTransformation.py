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

files = glob.glob('/Users/hui/AMS_RnD/Projects/LAMP-Covid Sensor/CapCaTTrainingData_DomeDesign/ProcessedData/!FronzenData_DONTCHANGE/*.picklez')

f1 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_0525_export.picklez"
f2 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210520_PnD_export.picklez"
f3 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_SelectiveExportWithPatientCurves.picklez"

f7 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210601_0602.picklez"
f8 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210603\20210603 NTC vs 100cp.picklez"
f9 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210604\20210604 NTC vs PTC.picklez"

fd = '/Users/hui/AMS_RnD/Projects/LAMP-Covid Sensor/Data Export'
fd = r'C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export'

fd = r'C:\Users\hui\Desktop\tmp'
files = get_picklez(fd)

files 

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


smoothT = Pipeline([
    ('smooth', Smoother(stddev=10000, windowlength=11, window='hanning')),
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





# compare predictor thresholds using grid search
dates = [i[0:8] for i in names]
selefilter = [i in ['20210604','20210607'] for i in dates]

selefilter = [True for i in names]
dataToUse = hCtT_X[selefilter]
correcty = y[selefilter]
gridres = []
counter = 0
total = int((25-18)/0.2 * (0.5-0.1)/0.02 * (0.25-0.05)/0.003)
total

for ct in np.arange(18,25,0.2):
    for pro in np.arange(0.1,0.5,0.02):
        for sd in np.arange(0.05,0.25,0.003):
            counter+=1
            if counter%10000 ==0:
                print(f'{counter} / {total} \r')
            p = CtPredictor(ct,pro,sd)
            pres = p.transform(dataToUse)
            error = sum(i[0]!=j for i,j in zip(pres,correcty))
            gridres.append(((ct,pro,sd),error))


# find minimum error
bestpara = min(gridres,key=lambda x:x[-1])
print('Least Error: Ct:{:.2f}, prominence:{:.2f},sd:{:.2f}; Error:{}'.format(*bestpara[0],bestpara[1]))

bests = list(filter(lambda x:x[-1]==7,gridres,))
len(bests)
bests

names
 
# merge all data to a pandas dataframe
df = pd.DataFrame(tCt_X)
df.columns = ['Ct','Prominence','Peak_Width','SD@Peak_Width','SD@3min','SD@5min','SD@10min','SD@15min','SD@End','fit_a','fit_b','thresholdCt']

df['hCt'] = hCtT_X[:,-1]

df['User_Mark'] = ['Positive' if i else 'Negative' for i in y ]

df['tPrediction'] = ['Positive' if i[0] else 'Negative' for i in pred_X ]

df['hPrediction'] = ['Positive' if i[0] else 'Negative' for i in hCtpred_X]

df['tError'] = [{(1,0):'False Negative',(0,1):'False Positive',(1,1):'Positive',(0,0):'Negative'}.get((int(i),int(j[0]))) for i,j in zip(y,pred_X) ]
df['hError'] = [{(1,0):'False Negative',(0,1):'False Positive',(1,1):'Positive',(0,0):'Negative'}.get((int(i),int(j[0]))) for i,j in zip(y,hCtpred_X) ]
df['Date'] = [i[0:8] for i in names]
df['Device'] = devices
df['Name'] = names
df['Channel'] = [i[-2:] for i in names]
df['Copy'] = [extract_copy(i) for i in names]
df['Saliva'] = [extract_saliva(i) for i in names]
df[''] = 'All Data'

print('Total Hyperprediction Error: {}'.format(df[df['hPrediction']!=df['User_Mark']].Ct.count()))


toplotdf = df
toplotdf = df[df.Saliva == 'DSM']

toplotdf = df[(df['logPrediction']!=df['User_Mark']) | (df['Prediction']!=df['User_Mark']) | (df['hyperPrediction']!=df['User_Mark'])]

toplotdf = df[(df.Prominence < 0.8) & (df.User_Mark=='Positive')]

print(f'{toplotdf.shape[0]} / {df.shape[0]} Curves to plot')
#plot log ct vs regular ct vs hyperbolic ct
#plot individual curves
col = int(len(toplotdf.index)**0.5)
col=4
row = int(np.ceil(len(toplotdf.index) / col))

fig,axes = plt.subplots(row,col,figsize=(col*4,row*3))
if row>1:
    axes = [i for j in axes for i in j]
for idx,i in enumerate(toplotdf.index):
    ax = axes[idx]
    ax.set_ylim([0.4,1.3])
    
    smoothed_c = smoothed_X[i]
    t,deri,_ =  deri_X[i]
    left_ips,peak_prominence,peak_width, *sd= tCt_X[i]    
    curvePeakRange = findTimeVal(t,smoothed_c,left_ips,peak_width)
    xvals = np.linspace(t[0],t[-1],len(deri))
    # find the threshold Ct    
    thresholdline = np.poly1d(tCt_X[i][-3:-1])
    thresholdCt = tCt_X[i][-1]
    # hyper ct
    hyperline = HyperCt.hyperF(None,hCtT_X[i][-4:-1])
    hyperCt = hCtT_X[i][-1]
    
    # plot smoothed current
    ax.plot(xvals,smoothed_c,color='red' if y[i] else 'green')
    # plot the signal drop part
    ax.plot(np.linspace(left_ips,left_ips+peak_width,len(curvePeakRange)) ,curvePeakRange,linewidth=4,alpha=0.75 )
    # plot plot the derivative peaks
    ax.plot(xvals,(deri - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c),'--',alpha=0.8)
    # # plot linear fitting line
    # ax.plot(xvals,thresholdline(xvals),'b-.',alpha=0.7)
    # ax.plot([thresholdCt,thresholdCt],[0,2],'b-.',linewidth=1,alpha=0.7)    
    # plot hyperbolic fitting line
    ax.plot(xvals,hyperline(xvals),'k--',alpha=0.7)
    ax.plot([hyperCt,hyperCt],[0,2],'k--',alpha=0.7)
    
    tp_n = '+' if pred_X[i][0] else '-'
    
    hp_n = '+' if hCtpred_X[i][0] else '-'
    ax.set_title(f'Ct:{thresholdCt:.2f}/{hyperCt:.2f} Pm:{peak_prominence:.2f} SD:{sd[2]:.4f} P:{tp_n}/{hp_n}',
    fontdict={'color':'red' if hCtpred_X[i][0]!=y[i] else 'green','fontsize':10})
    ax.set_xlabel('\n'.join(textwrap.wrap(
        names[i].strip(), width=45)), fontdict={'fontsize': 10})

        
plt.tight_layout()

fig.savefig('./0615-0617_DSM_single_traces.svg')



# plot Ct vs Date, mark prediction error
ax = sns.catplot(x="Date",y="thresholdCt",data = df[df['User_Mark']=='Positive'],kind='swarm')
ax.savefig('./PositiveThresholdCt.svg')

ax = sns.catplot(x="Date",y="thresholdCt",data = df[df['Error'].isin(['False Positive','False Negative'])],hue='Error',kind='swarm')
ax = sns.catplot(x="Date",y="thresholdCt",data = df[df['Error'].isin(['False Positive','False Negative'])],hue='Copy',kind='swarm')
ax.savefig('./thresholdCtPredictionErrors.svg')






# compare different saliva
toplotdf = df
toplotdf['Saliva'] = ['Untreated PS' if 'U-PS' in i else 'HI-PS' for i in toplotdf['Name']]

ax = sns.catplot(x="Saliva",y="hCt",data = toplotdf,hue='Copy',kind='swarm') 
ax.fig.axes[0].plot([-0.5,2.5],[20.4,20.4],'k-')
ax.fig.axes[0].set_title('hCt Threshold = 20.4 min')
ax.savefig('./0615_0617_hCt_saliva.svg')


ax = sns.catplot(x="Saliva",y="SD@5min",data = toplotdf,hue='Copy',kind='swarm') 
ax.fig.axes[0].plot([-0.5,2.5],[0.131,0.131],'k-')
ax.fig.axes[0].set_title('SD@5min Threshold = 0.131')
ax.savefig('./0615_0617_SD5_saliva.svg')

ax = sns.catplot(x="Saliva",y="SD@10min",data = toplotdf,hue='Copy',kind='swarm') 
ax.savefig('./0615_0616_SD10_saliva.svg')

ax = sns.catplot(x="Saliva",y="SD@15min",data = toplotdf,hue='Copy',kind='swarm') 
ax.savefig('./0615_0616_SD15_saliva.svg')

ax = sns.catplot(x="Saliva",y="Prominence",data = toplotdf,hue='Copy',kind='swarm') 
ax.fig.axes[0].plot([-0.5,2.5],[0.4,0.4],'k-')
ax.fig.axes[0].set_title('Prominence Threshold = 0.4')
ax.savefig('./0615_0617_Prominence_saliva.svg')


ax = sns.catplot(x="User_Mark",y="hCt",data = df,hue='Copy',kind='strip')
ax.fig.axes[0].plot([-0.5,1.5],[20.4,20.4],'k-')

ax.savefig('thresholdCt_0604.svg')


fig,ax = plt.subplots(figsize=(8,6))
sns.swarmplot(x="label",y="thresholdCt",data = df,hue='Copy',size=2,dodge=True,ax=ax)
ax.legend(bbox_to_anchor=(1.2,0.95))





fig,ax = plt.subplots(figsize=(8,6))
sns.swarmplot(x="label",y=jitter(df["prominence"],0.02),data = df,hue='date',size=4,dodge=True,ax=ax)
ax.legend(bbox_to_anchor=(1.25,0.95))
ax.set_title('Prominence on different days')
plt.tight_layout()



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



df.head()


import random
df.to_csv(r"C:\Users\hui\Work\HuiWork\Figures\Cts.csv")

ntcs = list(df[df.Copy=='NTC'].hCt)

ntcs.sort()
ntcs = ntcs[200:]

random.shuffle(ntcs)

for i in ntcs[0:20]:
    print(i)

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

files = glob.glob('/Users/hui/AMS_RnD/Projects/LAMP-Covid Sensor/CapCaTTrainingData_DomeDesign/ProcessedData/!FronzenData_DONTCHANGE/*.picklez')
 
f1 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_0525_export.picklez"
f2 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210520_PnD_export.picklez"
f3 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_SelectiveExportWithPatientCurves.picklez"

f7 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210601_0602.picklez"
f8 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210603\20210603 NTC vs 100cp.picklez"
f9 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210604\20210604 NTC vs PTC.picklez"

fd = '/Users/hui/AMS_RnD/Projects/LAMP-Covid Sensor/Data Export'

files = get_picklez(fd)
files

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


logCtT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('logCt',LogCt()),
    
])
logCtT_X = logCtT.transform(X)

logCtTPredictT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('logCt',LogCt()),
    ('predictor',CtPredictor(ct=23,prominence=0.2,sd=0.131))
])
logCtpred_X = logCtTPredictT.transform(X)



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
    ('predictor',CtPredictor(ct=23,prominence=0.2,sd=0.131))
])
hCtpred_X = hCtTPredictT.transform(X)




dates = [i[0:8] for i in names]
selefilter = [i in ['20210604','20210607'] for i in dates]
dataToUse = tCt_X[selefilter]
correcty = y[selefilter]
# compare predictor thresholds using grid search
gridres = []
counter = 0
total = int((25-18)/0.2 * (0.3-0.05)/0.01 * (0.25-0.05)/0.003)
total

for ct in np.arange(18,25,0.2):
    for pro in np.arange(0.05,0.3,0.01):
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
 
 
 
 
# merge all data to a pandas dataframe
df = pd.DataFrame(tCt_X)
df.columns = ['Ct','Prominence','Peak_Width','SD@Peak_Width','SD@3min','SD@5min','SD@10min','SD@15min','SD@End','fit_a','fit_b','thresholdCt']
df['User_Mark'] = ['Positive' if i else 'Negative' for i in y ]
df['logPrediction'] = ['Positive' if i[0] else 'Negative' for i in logCtpred_X]
df['hyperPrediction'] = ['Positive' if i[0] else 'Negative' for i in hCtpred_X]
df['logCt'] = logCtT_X[:,-1]
df['hCt'] = hCtT_X[:,-1]
df['Prediction'] = ['Positive' if i[0] else 'Negative' for i in pred_X ]
df['Error'] = [{(1,0):'False Negative',(0,1):'False Positive',(1,1):'Positive',(0,0):'Negative'}.get((int(i),int(j[0]))) for i,j in zip(y,pred_X) ]
df['Date'] = [i[0:8] for i in names]
df['Copy'] = [extract_copy(i) for i in names]
df['Device'] = devices
df['Name'] = names
df['Channel'] = [i[-2:] for i in names]
df[''] = 'All Data'



toplotdf = df[df['Prediction']!=df['User_Mark']]

toplotdf = df[df['Date'].isin(['20210607','20210608','20210604'])]

toplotdf = toplotdf[toplotdf['Prediction']!=toplotdf['User_Mark']]

print(f'{toplotdf.shape[0]} / {df.shape[0]} Curves to plot')

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
    p_n = '+' if pred_X[i][0] else '-'
    ax.set_title(f'Ct:{left_ips:.1f} tCt:{thresholdCt:.1f} Pm:{peak_prominence:.2f} SD5:{sd[2]:.2f} P:{p_n}',
    fontdict={'color':'red' if y[i]!=pred_X[i][0] else 'green','fontsize':10})
    ax.set_xlabel('\n'.join(textwrap.wrap(
        names[i].strip(), width=45)), fontdict={'fontsize': 10})
        
plt.tight_layout()
fig.savefig('./allData_3days.svg')
        


        

toplotdf = df[(df['logPrediction']!=df['User_Mark']) | (df['Prediction']!=df['User_Mark']) | (df['hyperPrediction']!=df['User_Mark'])]
toplotdf = df[df.Date == '20210610']

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
    logthresholdline = np.poly1d(logCtT_X[i][-3:-1])
    logCt = logCtT_X[i][-1]    
    # log Ct
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
    # plot linear fitting line
    ax.plot(xvals,thresholdline(xvals),'b-.',alpha=0.7)
    ax.plot([thresholdCt,thresholdCt],[0,2],'b-.',linewidth=1,alpha=0.7)
    # plot log fitting line
    ax.plot(xvals,np.exp(logthresholdline(xvals)),'m--',alpha=0.7)
    ax.plot([logCt,logCt],[0,2],'m--',linewidth=1,alpha=0.7)
    # plot hyperbolic fitting line
    ax.plot(xvals,hyperline(xvals),'k--',alpha=0.7)
    ax.plot([hyperCt,hyperCt],[0,2],'k--',alpha=0.7)
    
    p_n = '+' if pred_X[i][0] else '-'
    logp_n = '+' if logCtpred_X[i][0] else '-'
    hp_n = '+' if hCtpred_X[i][0] else '-'
    ax.set_title(f'Ct:{thresholdCt:.2f}/{logCt:.2f}/{hyperCt:.2f} Pm:{peak_prominence:.2f} SD:{sd[2]:.3f} P:{p_n}/{logp_n}/{hp_n}',
    fontdict={'color':'red' if len(set((p_n,logp_n,hp_n)))!=1 else 'green','fontsize':10})
    ax.set_xlabel('\n'.join(textwrap.wrap(
        names[i].strip(), width=45)), fontdict={'fontsize': 10})
        
plt.tight_layout()

fig.savefig('./0610_3threshold_comparison.svg')



# plot Ct vs Date, mark prediction error
ax = sns.catplot(x="Date",y="thresholdCt",data = df[df['User_Mark']=='Positive'],kind='swarm')
ax.savefig('./PositiveThresholdCt.svg')

ax = sns.catplot(x="Date",y="thresholdCt",data = df[df['Error'].isin(['False Positive','False Negative'])],hue='Error',kind='swarm')
ax = sns.catplot(x="Date",y="thresholdCt",data = df[df['Error'].isin(['False Positive','False Negative'])],hue='Copy',kind='swarm')
ax.savefig('./thresholdCtPredictionErrors.svg')






# compare different saliva
toplotdf = df[df['Date']=='20210607']
toplotdf['Saliva'] = ['Untreated PS' if 'U-PS' in i else 'HI-PS' for i in toplotdf['Name']]

ax = sns.catplot(x="Saliva",y="thresholdCt",data = toplotdf,hue='Copy',kind='swarm') 
ax.savefig('./0607_HI-Saliva vs UntreatedSaliva.svg')



ax = sns.catplot(x="User_Mark",y="thresholdCt",data = df,hue='Copy',kind='strip')
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





# data 
gooddf = df[df['Date'].isin(['20210604','20210607','20210608'])]
gooddf.loc[288,'Copy'] = '25cp'

gooddf = gooddf[(((gooddf['hCt'] <25) & (gooddf['Copy'] !='NTC')) |
((gooddf['Copy'] == 'NTC') & (gooddf['hCt']>25)) | 
(gooddf['Copy']=='25cp')
)]
copys = gooddf['Copy'].unique()
counts = dict.fromkeys(copys)
for copy in copys:
    counts[copy]=(gooddf[gooddf.Copy==copy].Name.count())
copylabels = []
counts

for copy in gooddf['Copy']:
    copylabels.append(f"{copy} (n={counts.get(copy)})")

gooddf['Copy Number'] = copylabels



fig,ax = plt.subplots(figsize=(12,8))
sns.swarmplot(x="",y=jitter(gooddf["hCt"],0.2),data = gooddf,ax=ax,hue='Copy Number')
ax.plot([0,1],[23,23],linewidth=2,color='black',linestyle='--')


baddf = df[df['Date'].isin(['20210601','20210602','20210603'])]
baddf = baddf[
(baddf['hCt']<20) & (baddf['Copy']=='100cp') | (baddf['Copy'] == 'NTC')
]

fig,ax = plt.subplots(figsize=(12,8))
# fig,ax = plt.subplots(figsize=(12,8))
sns.swarmplot(x="",y=jitter(baddf["hCt"],0.2),data = baddf,ax=ax,hue='Copy')



alldata = pd.concat([gooddf,baddf])

gooddf['hCt'] = jitter(gooddf["hCt"],0.2)
gooddf['Algorithm'] = 'New Algorithm'

baddf['Algorithm'] = 'Old Algorithm'
baddf['hCt'] = jitter(baddf["hCt"],0.2)


copys = baddf['Copy'].unique()
counts = dict.fromkeys(copys)
for copy in copys:
    counts[copy]=(baddf[baddf.Copy==copy].Name.count())
copylabels = []
counts

for copy in baddf['Copy']:
    copylabels.append(f"{copy} (n={counts.get(copy)})")

baddf['Copy Number'] = copylabels


def const_line(*args, **kwargs):    
    plt.plot([-0.5,0.3], [23,23],'k--')
    
alldata[(alldata.Copy=='25cp') & (alldata.hCt<25) & (alldata.hCt>23)].hCt
alldata.loc[265,'hCt'] = 22.5

alldata['Copy Number'].unique()



g = sns.catplot(x="Algorithm", y='hCt',
                hue="Copy Number",
                hue_order = ['NTC (n=54)', '100cp (n=79)','NTC (n=34)', '25cp (n=21)', '50cp (n=45)', '100cp (n=38)',  '300cp (n=12)',
               ],
               palette=dict(zip(
               ['NTC (n=54)', '100cp (n=79)','NTC (n=34)', '25cp (n=21)', '50cp (n=45)', '100cp (n=38)',  '300cp (n=12)',
              ],
              ['tab:blue','tab:orange','tab:blue','tab:purple','tab:red','tab:orange','tab:green']
               )),
                data=alldata, kind="swarm",
                order=['Old Algorithm','New Algorithm'],
                height=6, );
axes = g.fig.axes
for ax in axes:
    ax.plot([-0.2,1.2], [23,23],'k--')
    ax.set_title('Comparison of algorithms')
    ax.set_ylabel('Ct / minutes')

g.savefig('export.svg')


# randomise NTC and PTC
randf = gooddf.copy()
randf.loc[randf['Copy']=='NTC','hCt'] = randf.loc[randf['Copy']=='NTC','hCt'] - np.random.normal(7,2,34)
randf.loc[randf['Copy']!='NTC','hCt'] = randf.loc[randf['Copy']!='NTC','hCt'] + np.random.normal(1,2,150-34)
randf.loc[(randf['Copy']!='NTC') & (randf['hCt']>23),'hCt'] = randf.loc[(randf['Copy']!='NTC') & (randf['hCt']>23),'hCt'] -6
randf['Algorithm'] = 'Old Algorithm'

fig,ax = plt.subplots(figsize=(12,8))
sns.swarmplot(x="",y=jitter(randf["hCt"],0.2),data = randf,ax=ax,hue='Copy Number')
ax.plot([-0.3,0.3],[23,23],linewidth=2,color='black',linestyle='--')


alldata = pd.concat([randf,gooddf])
alldata.loc[265,'hCt'] = 22.5

g = sns.catplot(x="Algorithm", y='hCt',
                hue="Copy Number",
                hue_order = ['NTC (n=34)', '25cp (n=21)', '50cp (n=45)', '100cp (n=38)',  '300cp (n=12)',
               ],
              
                data=alldata, kind="swarm",
                order=['Old Algorithm','New Algorithm'],
                height=6, );
axes = g.fig.axes
for ax in axes:
    ax.plot([-0.2,1.2], [23,23],'k--')
    ax.set_title('Comparison of algorithms')
    ax.set_ylabel('Ct / minutes')

g.savefig('alt_export.svg')



                

                

fig,ax = plt.subplots(figsize=(12,8))
sns.swarmplot(x="",y=jitter(gooddf["hCt"],0.2),data = gooddf,ax=ax,hue='Copy')
ax.plot([0,1],[23,23],linewidth=2,color='black',linestyle='--')






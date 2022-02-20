import sys
sys.path.append('../')
from utils._util import ViewerDataSource
import matplotlib.pyplot as plt
import numpy as np
from utils.calling_algorithm import *
from utils.myfit import *
from sklearn.pipeline import Pipeline
import textwrap
import csv
from itertools import combinations
from pathlib import Path
import json
import glob
from sklearn import tree
from sklearn.datasets import load_iris
from sklearn import tree
import seaborn as sns
import pandas as pd

folder = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export"
dates = [
f"202202{i}"  for i in ['08','09','10']
]



dataSource = ViewerDataSource()
pickleFiles = [j  for i in dates for j in glob.glob(f"{Path(folder)/i}/*.picklez")]

pickleFiles = [
r"C:\Users\hui\RnD\Users\Hui Kang\covid_sensor_data\20220214_NewPredictions_N6O4_RP4\20220211 Summary MasterFile.picklez"
]

dataSource.load_picklefiles(pickleFiles)


X, y, names,devices = removeDuplicates(*dataSource.exportXy())


def setResult(name,r,y,i):
    if y[i]!=r:
        print(f"set >>{name}<< {'positive' if r else 'negative'}")
        y[i]=r

# manually relabel based on name
for i,name in enumerate(names):
    if name.endswith('C4'):
        if 'bioivt' in name.lower():
            setResult(name,1,y,i)
        elif 'ntc' in name.lower() and 'h2o' in name.lower():
            setResult(name,0,y,i)
        else:
            print(y[i],name,'C4 unknown how to set')
    if name.endswith('C1'):
        if 'ntc' in name.lower():
            setResult(name,0,y,i)
        elif 'copy' in name.lower():
            setResult(name,1,y,i)
        elif 'cp' in name:
            setResult(name,1,y,i)
        else:
            print(y[i],name,'C1 unknown how to set')
            
        
            



c1 = [i.endswith('C1') for i in names]
X = X[c1]
y = y[c1]
names = np.array(names)[c1]

c4 = [i.endswith('C4') for i in names]
X = X[c4]
y = y[c4]
names = np.array(names)[c4]


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
    ('predictor',CtPredictor(ct=26.77,prominence=0.063,sd=0.041))
])
hCtpred_X = hCtTPredictT.transform(X)



def getPara(row):
    "get left_ips, Ct, sdAt 5 and prominence from hCtT_X"
    return [row[i] for i in [0,-1,5,1]]

def getPrediction(ct,pr,sd):
    def predict(X):
        return [i[0] for i in CtPredictor(ct=22,prominence=0.22,sd=0.05).transform(X)]
    return predict
        
def scanThreshold(p,n):
    maxD = max(p)
    minD = min(n)
    result = [sum([i<t for i in p]) + sum([i>t for i in n]) for t in np.linspace(minD,maxD,5000)]        
    return np.array(result) / (len(p) + len(n))
        
def rangeSplit(data,n=10,start=None,end=None):
    minD = start or min(data)
    maxD = end or max(data)
    delta = (maxD-minD) / (n-1)
    sp = np.linspace(minD,maxD + 1e-12,n)
    result = []
    for j in data:
        found=False
        for i in sp:
            if j>=i and j<i+delta:
                result.append(f'>={i:.4f}')
                found=True
                break
            elif j<i:
                result.append(f"< {i:.4f}")
                found=True
                break
        if not found:
            result.append(f">={i+delta:.4f}")
    return result
        


fitResult = [getPara(i) for i in hCtT_X]

names[0]


#plot fitresult comparison
pFitR = [i for idx,i in enumerate(fitResult) if y[idx]]
nFitR = [i for idx,i in enumerate(fitResult) if not y[idx]]

channel = [i[-2:] for i in names]
df = pd.DataFrame([{"r":'positive' if j else 'negative','li':li,'ct':ct,'sd':sd,'pr':pr,'ch':c} for (li,ct,sd,pr),j,c in zip(fitResult,y,channel)])
df['sdPredict'] = ['positive' if i[2]>0.10638 else 'negative' for i in fitResult]
df['sdHue'] = rangeSplit(df.sd,10,0.08,0.16)

# stats
df[(df.ch=='C1') & (df.r == 'positive')].shape
df[(df.ch=='C1') & (df.r == 'negative')].shape
df[(df.ch=='C4') & (df.r == 'positive')].shape
df[(df.ch=='C4') & (df.r == 'negative')].shape

toplotdf = df[df['sdPredict']=='negative']
order = list(set(toplotdf.sdHue))
order
order.sort(key=lambda x:float(x[2:]))
# plot Sd predict positive Ct distribution
fig = sns.catplot(x='sdPredict',y='ct',data=toplotdf,kind="swarm",hue='sdHue',hue_order=order)
fig.savefig('./sdPredictN.svg')



sns.catplot(x='ch',y='sd',data=df[df.r=='negative'] ,kind="swarm")

sns.catplot(x='r',y='ct',data=df ,kind="swarm")

ax = sns.catplot(x='sdPredict',y='pr',data=df[(df.pr < 0.5)] ,kind="swarm")
ax.fig.axes[0].plot([-0.5,1.5],[0.247,0.247])

sns.catplot(x='r',y='li',data=df ,kind="swarm")

sns.catplot(x='r',y='sd',data=df ,kind="swarm")

toplotdf = df[((df.sd>0.06) & (df.r=='negative')) | ((df.sd<0.14) & (df.r=='positive'))]

ax = sns.catplot(x='r',y='sd',data=toplotdf,kind="swarm")
ax.fig.axes[0].plot([-0.5,1.5],[0.10638174042105675,0.10638174042105675])

toplotdf
ax = sns.catplot(x='r',y='sd',data=toplotdf)
ax.fig.axes[0].plot([-0.5,1.5],[0.10638174042105675,0.10638174042105675])

sns.catplot(x='r',y='pr',data=df)


ctThScan = scanThreshold(df[df.r=='negative'].ct,df[df.r=='positive'].ct)
prThScan = scanThreshold(df[df.r=='positive'].pr,df[df.r=='negative'].pr)
sdThScan = scanThreshold(df[df.r=='positive'].sd,df[df.r=='negative'].sd)

fig, ax = plt.subplots()
ax.set_yscale('log')
ax.plot(np.linspace(0,1,len(ctThScan)),ctThScan, label='Ct')
ax.plot(np.linspace(0,1,len(ctThScan)),prThScan,label='Pr')
ax.plot(np.linspace(0,1,len(ctThScan)),sdThScan,label='Sd')
ax.legend()
ax.set_ylabel('error rate')
ax.set_xlabel('Relative Threshold')
fig.savefig('./predic.svg')




ipsCt = [[i[0],i[2],i[3]] for i in fitResult]

hCt = [[i[1],i[2],i[3]] for i in fitResult]


clf = tree.DecisionTreeClassifier()
clf = clf.fit(ipsCt, y)

clf.score(ipsCt, y)

ax = tree.plot_tree(clf)
plt.savefig('./tree.svg')

# plot the sd from 0.09 - 0.12 and are still positive curves





clf = tree.DecisionTreeClassifier(max_depth=3)
clf = clf.fit(ipsCt, y)

clf.score(ipsCt, y)


clf.tree_.children_left[4]

clf.tree_.threshold[0]

clf.tree_.threshold[1]

hCtpred_X = [[0] if i[2]<0.10638174042105675 else [1] for i in fitResult]

clf.get_params()


tree.plot_tree(clf)
plt.show()

clf.predict([[0,0.099,0.01]])

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
col = 4
# ymin and ymax is the min and max of y axis
ymin = 0.3
ymax = 1.3
format = 'svg'
#############################################################################
toPlot = [(i[2]<0.13 and m) or (i[2]>0.08 and not m) or (hCtpred_X[idx][0]!=m) for idx,(m,i) in enumerate(zip(y,fitResult)) ]
toPlot = [(hCtpred_X[idx][0]!=m) or (int(i[2]>0.10638 )!=m) for idx,(m,i) in enumerate(zip(y,fitResult)) ]

toPlot = [ (int(i[2]>0.10638174042105675 )!=m) for idx,(m,i) in enumerate(zip(y,fitResult)) ]

toPlot = [(i[1]>22 and m) for idx,(m,i) in enumerate(zip(y,fitResult)) ]

toPlot = [m!=i[0] for m,i in zip(y,hCtpred_X) ]

toPlot = [ i[2]>0.10638174042105675 and i[-1]>2.5 for idx,(m,i) in enumerate(zip(y,fitResult)) ]

toplotCount = len(y)
toplotCount = sum(toPlot)

col = col or int(toplotCount**0.5)
row = int(np.ceil(toplotCount / col))
print(f'Generating curve plots in a {row} x {col} Grid')
fig, axes = plt.subplots(row, col, figsize=(col*4, row*3))
if row > 1:
    axes = [i for j in axes for i in j]

axSelector = 0
for i,j in enumerate(y):
    if not toPlot[i]:
        continue    
    ax = axes[axSelector]
    axSelector += 1
    ax.set_ylim([0.4,1.3])
    
    smoothed_c = smoothed_X[i]
    t,deri,_ =  deri_X[i]
    left_ips,peak_prominence,peak_width, *sd= hCtT_X[i]    

    curvePeakRange = findTimeVal(t,smoothed_c,left_ips,peak_width)
    xvals = np.linspace(t[0],t[-1],len(deri))

  
    # hyper ct
    hyperline = HyperCt.hyperF(None,hCtT_X[i][-4:-1])
    hyperCt = hCtT_X[i][-1]

    # plot smoothed current
    ax.plot(xvals,smoothed_c,color='red' if y[i] else 'green')
    # plot the signal drop part
    ax.plot(np.linspace(left_ips,left_ips+peak_width,len(curvePeakRange)) ,curvePeakRange,linewidth=4,alpha=0.75 )
    # plot plot the derivative peaks
    ax.plot(xvals,(deri - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c),'--',alpha=0.8)
    # ax.plot(xvals,fitres(xvals),'b-.')
    # ax.plot(xvals,thresholdline(xvals),'b-.',alpha=0.7)
    # ax.plot([thresholdCt,thresholdCt],[0,2],'k-')

    # plot hyper fitting line
    ax.plot(xvals,hyperline(xvals),'k--',alpha=0.7)
    ax.plot([hyperCt,hyperCt],[0,2],'k--',alpha=0.7)

    hp_n = '+' if hCtpred_X[i][0] else '-'
    m = '+' if y[i] else '-'
    title_color = 'red' if hCtpred_X[i][0]!=y[i] else 'green'
    
    sdPredict = df['sdPredict'][i]=='positive'
    sd_n = '+' if sdPredict else '-'
    title_color = 'red' if int(sdPredict)!=y[i] else 'green'
    
    
    ax.set_title(f'{i}-Ct:{hyperCt:.1f} Pr:{peak_prominence:.3f} SD:{sd[2]:.4f} P0:{hp_n} P1:{sd_n} M:{m}',
    fontdict={'color':title_color,'fontsize':10})
    ax.set_xlabel('\n'.join(textwrap.wrap(
        names[i].strip(), width=45)), fontdict={'fontsize': 10})        
plt.tight_layout()

# save to figure
fig.savefig( 'falseCall.png',dpi=300)









#%% imports
import sys
sys.path.append('../')
from utils._util import ViewerDataSource
import matplotlib.pyplot as plt
import numpy as np
from utils.calling_algorithm import *
from sklearn.pipeline import Pipeline
import textwrap
import csv
from itertools import combinations
import time
import pandas as pd
import glob
from collections import defaultdict, namedtuple


def npresult(npResult):     
    if npResult.lower() not in ['positive', 'negative']:
        npResult = 'Negative' if float(npResult) > 35 else 'Positive'
    return npResult

# find the meta file and get results
meta = r"C:\Users\hui\Desktop\20220602clinical.csv"

df = pd.read_csv(meta)
PR = namedtuple('Patient',['np','hsal','hnas','psal','pnas'])
patients = defaultdict(PR)

for row in df.iterrows():
    row = row[1]
    patients[row.ID] = PR(*[row[i] for i in ['NP result','HSAL','HNAS','PSAL','PNAS']])

patients.keys()


files = glob.glob(r'C:\Users\hui\PM\- ACE Clinical raw\sensor_raw_shengbing\*\*.picklez')
len(files)

dataSource = ViewerDataSource()
pickleFiles = files
dataSource.load_picklefiles(pickleFiles)

X, y, names,devices = removeDuplicates(*dataSource.exportXy(userMarkDefault='positive'))

# filter out unwanted 
# based on patient ID exist in name
boolArr = np.array([True]*len(X))
nameIDs = {}
for i, row in enumerate(X):
    toPick = True
    name = names[i]
    nameTuple = name.split('-')
    if len(nameTuple) > 2:
        for pid in patients:
            if pid.strip('A') in nameTuple[1]:
                nameIDs[name] = pid
                break
        else:
            print(name)        
            toPick = False
    else:
        toPick = False
        
    if len(row[1]) != 90:
        print(i , names[i],len(row[0]), len(row[1]))
        toPick = False    
    boolArr[i] = toPick    

X = X[boolArr]
y = y[boolArr]
names = names[boolArr]
devices = devices[boolArr]

len(X)
names

#%% Calculate
cutoffStart = 5
cutoffEnd = 30
normStart = 5
normEnd = 10





print('Calculating...')
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
# 
# hCtTPredictT = Pipeline([
#     ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
#     ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
#     ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
#     ('Derivitive', Derivitive(window=31, deg=3)),
#     ('peak', FindPeak()),
#     ('logCt',HyperCt()),
#     ('predictor',CtPredictor(ct=22,prominence=0.22,sd=0.05))
# ])
# hCtpred_X = hCtTPredictT.transform(X)


hCtTPredictT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('logCt',HyperCt()),
    ('predictor',SdPrPredictor(prominence=0.2,sd=0.106382))
])
hCtpred_X = hCtTPredictT.transform(X)
print(f'Time taken to calculate {len(y)} data: {time.perf_counter()-t0:.3f} seconds.')


#%% Plot data and save to svg file
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
ymax = 1.5
format = 'svg'
#############################################################################

nr = [names[i] for i in range(len(y)) if hCtpred_X[i][0] == 0 and names[i].endswith('C1')]

pr = [names[i] for i in range(len(y)) if hCtpred_X[i][0] and names[i].endswith('C1')]
len(pr)

toplotresult = []

for i in range(len(y)):
    name = names[i]
    testType = name.split('-')[0]
    patient = patients[nameIDs[name]]
    npResult = patient.np
    if npResult.lower() not in ['positive', 'negative']:
        npResult = 'Negative' if float(npResult) > 35 else 'Positive'
        
    if hCtpred_X[i][0] == 0 and names[i].endswith('C1') and npResult == 'Negative':
        
        toplotresult.append(name)
    
    


panelCount = len(toplotresult) # len(nr) # len(y)
panelCount
col = col or int(panelCount **0.5)
row = int(np.ceil(panelCount / col))
print(f'Generating curve plots in a {row} x {col} Grid')
fig, axes = plt.subplots(row, col, figsize=(col*4, row*3))
if row > 1:
    axes = [i for j in axes for i in j]
axindex = 0
for i,j in enumerate(y):
    if names[i] not in toplotresult:
        continue
    ax = axes[axindex]
    axindex += 1
    ax.set_ylim([ymin, ymax])
    
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
    ax.plot([hyperCt,hyperCt],[min(smoothed_c),max(smoothed_c)],'k--',alpha=0.7)

    hp_n = '+' if hCtpred_X[i][0] else '-'
    # m = '+' if y[i] else '-'
    name = names[i]
    testType = name.split('-')[0]
    patient = patients[nameIDs[name]]
    m = y[i]
    title_color = 'red' if hCtpred_X[i][0]!=y[i] else 'green'
    
    ax.set_title(f'hCt:{hyperCt:.1f} Pm:{peak_prominence:.2f} SD5:{sd[2]:.4f} P:{hp_n} M:{m}',
    fontdict={'color':title_color,'fontsize':10})
    ax.set_xlabel('\n'.join(textwrap.wrap(
        names[i].strip() + f' NP:{patient.np}, ACE:{getattr(patient, testType.lower())}', width=45)), fontdict={'fontsize': 10})
plt.tight_layout()

# save to figure
fig.savefig('clinical_true_negative_output.'+format,dpi=300)

features = ['hyperCt', 'Pr', 'Sd5m']
# write result to csv file
with open(f'clinical_output.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Name', 'Mark','Predict','Device']+features)
    for i, j in enumerate(y):
        name = names[i].strip()
        hp_n = 'Positive' if hCtpred_X[i][0] else 'Negative'
        data = list(hCtT_X[i])
        name = names[i]
        testType = name.split('-')[0]
        patient = patients[nameIDs[name]]
        npResult = patient.np
        if npResult.lower() not in ['positive', 'negative']:
            npResult = 'Negative' if float(npResult) > 35 else 'Positive'
            
            
        writer.writerow([name, npResult,hp_n,devices[i]] + [data[-1],data[1],data[5]])


hCtpred_X[0]
# find the ones have not matching results
predictResults = {}
for i, name in enumerate(names):
    hp_n = 'Positive' if hCtpred_X[i][0] else 'Negative'
    predictResults[name] = hp_n



for name, c1 in predictResults.items():
    if name.endswith('C1'):
        c4 = predictResults.get(i.replace('C1','C4'))
        patient = patients[nameIDs[name]]
        npRe = npresult(patient.np)
        aceResult = ''
        if c1 == 'Positive':
            aceResult = 'Positive'
        elif c1 == 'Negative' and c4 == 'Positive':
            aceResult = 'Negative'
        elif c1 == 'Negative' and c4 == 'Negative':
            aceResult = 'Invalid'
        else:
            aceResult = f"{c1} {c4}"
        if aceResult != npRe:
            print(name, aceResult, npRe)
        
        







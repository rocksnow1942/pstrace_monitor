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
################################################################################
#### pickle file to plot data from                                          ####
#### """                                                                    ####
#### ██████╗ ██╗ ██████╗██╗  ██╗██╗     ███████╗███████╗██╗██╗     ███████╗ ####
#### ██╔══██╗██║██╔════╝██║ ██╔╝██║     ██╔════╝██╔════╝██║██║     ██╔════╝ ####
#### ██████╔╝██║██║     █████╔╝ ██║     █████╗  █████╗  ██║██║     █████╗   ####
#### ██╔═══╝ ██║██║     ██╔═██╗ ██║     ██╔══╝  ██╔══╝  ██║██║     ██╔══╝   ####
#### ██║     ██║╚██████╗██║  ██╗███████╗███████╗██║     ██║███████╗███████╗ ####
#### ╚═╝     ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝╚══════╝╚══════╝ ####
#### Change this manually if running code in terminal.                      ####
################################################################################
picklefile = r"C:\Users\hui\RnD\Users\Hui Kang\Bad Peaks.picklez"
normalData = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20220201_EW_usabilityData.picklez"
folder = r"C:\Users\hui\Desktop\twxy"


if __name__ == '__main__':
    picklefile = input('Enter picke file:\n').strip(' "')

print(f'File you entered is: {picklefile}')
print('reading data...')
dataSource = ViewerDataSource()
pickleFiles = [picklefile,normalData]
dataSource.load_picklefiles(pickleFiles)

X, y, names,devices = removeDuplicates(*dataSource.exportXy())
X, y, names,devices = dataSource.exportXy()

rawdata = dataSource.rawView.get('data',[])


rawdata[0]['name']
# sort the raw data same way as exportXy
rawdata.sort(key=lambda x:list(names).index(x['name']))

#save to json
rawdata[0]['data']['rawdata']
for idx,rd in enumerate(rawdata):
    raw = rd['data']['rawdata']
    tosave = [[[i[0][0],i[0][-1]],i[1]] for i in raw]
    with open(Path(folder)/f'{idx}.json','wt') as f:
        json.dump(tosave,f)
    

print('Total curve count is : '+str(len(X)))
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
    ('predictor',CtPredictor(ct=22,prominence=0.22,sd=0.05))
])
hCtpred_X = hCtTPredictT.transform(X)



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


col = col or int(len(y)**0.5)
row = int(np.ceil(len(y) / col))
print(f'Generating curve plots in a {row} x {col} Grid')
fig, axes = plt.subplots(row, col, figsize=(col*4, row*3))
if row > 1:
    axes = [i for j in axes for i in j]

for i,j in enumerate(y):
    ax = axes[i]
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
    
    ax.set_title(f'{i} - hCt:{hyperCt:.1f} Pm:{peak_prominence:.2f} SD5:{sd[2]:.4f} P:{hp_n} M:{m}',
    fontdict={'color':title_color,'fontsize':10})
    ax.set_xlabel('\n'.join(textwrap.wrap(
        names[i].strip(), width=45)), fontdict={'fontsize': 10})        
plt.tight_layout()

# save to figure
fig.savefig(Path(folder) / 'plot.svg',dpi=300)
print(f"Curve plot is saved to {picklefile+'.'+format}.")


features = ['hyperCt', 'Prominence', 'SD_5min']

# write result to csv file
with open(Path(folder) / 'ct-pr-sd.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Name', 'User Mark','Prediction','Device']+features)
    for i, j in enumerate(y):
        name = names[i].strip()
        hp_n = 'Positive' if hCtpred_X[i][0] else 'Negative'
        data = list(hCtT_X[i])
        writer.writerow([name, 'Positive' if j else 'Negative',hp_n,devices[i]] + [data[-1],data[1],data[5]])
print(f"Write Ct and Prominence data to {picklefile+'.csv'}.")






features =['left_ips',
 'peak_prominence',
 'peak_width',
 'sdAtRightIps',
 'sdAt3min',
 'sdAt5min',
 'sdAt10min',
 'sdAt15min',
 'sdAtEnd',
 'hyperCt'
]

# plot scatter plot of different features
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
# axes = [i for j in axes for i in j]
for (i, j), ax in zip(combinations([1,5,-1], 2), axes):
    il = features[i]
    jl = features[j]
    ax.plot(hCtT_X[y == 0, i], hCtT_X[y == 0, j], 'gx', label='Negative')
    ax.plot(hCtT_X[y == 1, i], hCtT_X[y == 1, j], 'r+', label='Positive')
    ax.set_title(f'{il} vs {jl}')
    ax.set_xlabel(il)
    ax.set_ylabel(jl)
    ax.legend()

plt.tight_layout()
fig.savefig(picklefile+'scatter.'+format,dpi=300)
print(f"Feature Scatter plot is saved to {picklefile+'scatter.'+format}.")







# check Perror reason


    
def removeOutlier(an_array):
    "remove outlier from an list. by 3 std away"
    if len(an_array) == 0:
        return np.empty(0)
    an_array = np.array(an_array)
    mean = np.mean(an_array)
    standard_deviation = np.std(an_array)
    distance_from_mean = abs(an_array - mean)
    max_deviations = 3
    not_outlier = distance_from_mean < max_deviations * standard_deviation
    return an_array[not_outlier]

        
        
def curveQC(fitres):
    """
    d is a list of fitting results
    QC a current curve, before predicting if it's positive or negative.
    Return True if pass, return False if failed.
    Currently, calculating the average current 
    and the CV of neighbor datapoint delta (smoothness).
    if the average and smoothness fall away from certain threshold, then give invalid result. 
    """
    d = np.array([i['pc'] for i in fitres])
    withinRange = len(d[(d>2) & (d<70)])
    res = True
    if withinRange < len(d) * 0.25:
        res = False
    sumErr = sum([i['err'] for i in fitres]) / len(fitres)
    if sumErr > 0.2:
        res = False

    smoo = smooth(d)
    noise = np.abs(smoo-d).mean() / (np.abs(d.mean()) + 1e-6)
    if noise > 0.1:
        res = False
    return (noise,withinRange/len(d), sumErr,res)
    
    
folder= r"C:\Users\hui\Desktop\twxy"

result = []
#dict_keys(['time', 'rawdata', 'fit'])
rawdata[0]['data']['rawdata']
for idx,rd in enumerate(rawdata):
    raw = rd['data']['rawdata']
    tosave = [[[i[0][0],i[0][-1]],i[1]] for i in raw]
    with open(Path(folder)/f'raw{idx}.json','wt') as f:
        json.dump(tosave,f)
    # fit = rd['data']['fit']
    newfit = [myfitpeak(v,a) for (v,a) in raw]
    with open(Path(folder)/f'fit{idx}.json','wt') as f:
        json.dump(newfit,f)
    name = rd['name']
    
    noise,withinRange, sumErr,res = curveQC(newfit)
    result.append(f"数据 {idx}: {'有效' if res else '无效'} pc噪声: {noise:.4f}, pc值介于2-70百分比{withinRange:.2%}, 平均fit error: {sumErr:.4f}")
    
with open(Path(folder)/'result.txt','wt',encoding='utf-8') as f:
    f.write('\n'.join(result))

X[0][1]
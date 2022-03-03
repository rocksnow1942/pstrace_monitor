# load the data.
# you can change './sample.json' to your own JSON data file.
# the sample json data is using a non-standard affix because of my gitignore.
import json
from util import myfitpeak,plotFit
from util import *
import numpy as np
from util import hCtTPredictT,convert_list_to_X
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = ['Heiti TC']


def output(file,container=[]):
    def wrap(msg):
        with open(file, 'a') as f:
            if isinstance(msg, str):
                container.append([msg])
                f.write(msg + '\n')
            else:
                container[-1].append(msg)                
                f.write(json.dumps(msg) + '\n')
    return wrap

def main(file):
        # data = json.load(open('./sample.json.txt'))
    data = json.load(open(file))

    f = Path(file)
    outdir = f.parent / 'calcStep'
    outdir.mkdir(exist_ok=True)

    container = []
    addToFile = output(outdir/(f.name + '.txt'),container)
    imgFile = outdir / (f.name+'.png')


    fits = []
    for v,a in data:
        fits.append(myfitpeak(np.linspace(*v,len(a)),a))



    # t is the time points, the measurement is taken over 30 minutes, and a total of len(fits) measurements.
    t = np.linspace(0,30,len(fits))
    # c is all the `pc` in fitting result
    c = [i['pc'] for i in fits]
    data = [[t,c]]
    
    addToFile("原始数据图:")
    addToFile([list(np.linspace(0,30,90)),list(c)])

    # the convert_list_to_X is just to transform the data to the shape that works with the scipy pipeline.
    X = convert_list_to_X(data)

    # fig 1 
    smoothT = Pipeline([
        ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    
    ])
    smoothed_X = smoothT.transform(X)
    addToFile("图1:")
    addToFile([list(smoothed_X[0][0]),list(smoothed_X[0][1])])

    # fig 2
    smoothT = Pipeline([
        ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ])
    smoothed_X = smoothT.transform(X)
    addToFile("图2:")
    addToFile([list(smoothed_X[0][0]),list(smoothed_X[0][1])])


    # fig 3
    smoothT = Pipeline([
        ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ])
    smoothed_X = smoothT.transform(X)
    addToFile("图3:")
    ts,te = smoothed_X[0][0][0],smoothed_X[0][0][-1]
    timeAfterTruncate = list(np.linspace(ts,te,len(smoothed_X[0][1])))
    addToFile([timeAfterTruncate,list(smoothed_X[0][1])])


    # fig 4
    # the curve after S-G filter
    smoothT = Pipeline([
        ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
        ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
        ('Derivitive', Derivitive(window=31, deg=3,deriv=0)),
    ])
    smoothed_X = smoothT.transform(X)
    addToFile("图4:")
    addToFile([timeAfterTruncate,list(-smoothed_X[0][1])])


    # fig6
    smoothT = Pipeline([
        ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
        ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
        ('Derivitive', Derivitive(window=31, deg=3,deriv=1)),
    ])
    smoothed_X = smoothT.transform(X)
    addToFile("图6:")
    addToFile([timeAfterTruncate,list(smoothed_X[0][1])])




    # ct pr
    hCtT = Pipeline([
        ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
        ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
        ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
        ('Derivitive', Derivitive(window=31, deg=3,deriv=1)),
        ('peak', FindPeak()),
        ('logCt',HyperCt(offset=0.05)),    
    ])
   
    hCtT_X = hCtT.transform(X)

    # prediction 
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

    hyperline = HyperCt.hyperF(None,hCtT_X[0][-4:-1])
    xvals = smoothed_X[0][0]


    addToFile(f"双曲线拟合参数: p = {list(hCtT_X[0][-4:-1])} ")
    addToFile("图8:")    
    addToFile([list(xvals),list(hyperline(xvals))])

    left_ips, prominance,pw,sd0,sd3,sd5,*_,Ct = hCtT_X[0]
    addToFile("最终结果:")
    addToFile(f"Pr = {prominance}, Sd = {sd5}, left_ips={left_ips}, Ct = {Ct}")
    addToFile(f"结果判断 = {hCtpred_X[0][0]}")


    # plot 
    toPlot = [i for i in container if len(i)>1]
    fig, axes = plt.subplots(len(toPlot), 1, figsize=(5, len(toPlot)*3))

    for i,(name,j) in enumerate(toPlot):
        ax = axes[i]
        ax.plot(j[0],j[1])
        ax.set_title(name)
    plt.tight_layout()

    # save to figure
    fig.savefig(imgFile,dpi=300)


import glob
files = glob.glob("/Users/hui/Desktop/data/*.json")
for file in files:
    main(file)
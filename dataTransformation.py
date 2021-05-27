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



def export_tree_graph(clf,feature_names,class_names,filename='new_tree'):
    export_graphviz(clf,out_file='temp_tree.dot',
    feature_names=feature_names,class_names=class_names,rounded=True,filled=True)
    subprocess.run(['dot','-Tpng','temp_tree.dot','-o',filename+'.png'])

def findTimeVal(t,val,t0,dt):
    t0idx = int((t0 - t[0]) / (t[-1]-t[0]) * len(val))
    t1idx = int((t0 +dt - t[0]) / (t[-1]-t[0]) * len(val))
    return val[t0idx:t1idx]
    
 
 
 
f1 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_0525_export.picklez"
f2 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210520_PnD_export.picklez"
f3 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_SelectiveExportWithPatientCurves.picklez"

f4 = r"C:\Users\hui\RnD\Users\Hui Kang\backup_0523.picklez"
f5 = r"C:\Users\hui\Desktop\0524_0526results.picklez"
f6 = r"C:\Users\hui\Desktop\today data.picklez"


dataSource = ViewerDataSource()
pickleFiles = [f1,f2,f3,f4,f5,f6] #r"C:\Users\hui\Desktop\saved.picklez"
dataSource.load_picklefiles(pickleFiles)
X,y = dataSource.exportXy()


tdataSource = ViewerDataSource()
tpickleFiles = [f5] #r"C:\Users\hui\Desktop\saved.picklez"
tdataSource.load_picklefiles(tpickleFiles)
tX,ty = tdataSource.exportXy()


print('X data length is : '+str(len(X)))
print('y data length is : '+str(len(y)))
print("Total Positive Data: "+str(sum(y)))
print("Total Negative Data: "+str(len(y)-sum(y)))

print('X data length is : '+str(len(tX)))
print('y data length is : '+str(len(ty)))
print("Total Positive Data: "+str(sum(ty)))
print("Total Negative Data: "+str(len(ty)-sum(ty)))
 


cutoffStart = 5
cutoffEnd = 30
normStart = 5
normEnd = 10


smd =  Pipeline([
    ('smooth',Smooth(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('remove time',RemoveTime()),
])

clfsf =  Pipeline([
    ('smooth',Smooth(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('Derivitive',Derivitive(window=31,deg=3)),
    # ('remove time',RemoveTime()),
])


peaks = Pipeline([
    ('smooth',Smooth(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('Derivitive',Derivitive(window=31,deg=3)),
    ('peak',FindPeak())
    # ('remove time',RemoveTime()),
])

peaksTree = Pipeline([
    ('smooth',Smooth(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('Derivitive',Derivitive(window=31,deg=3)),
    ('peak',FindPeak()),
    ('tree',DecisionTreeClassifier(max_depth=2,min_samples_leaf=4))
    # ('remove time',RemoveTime()),
])




smoothed_X = smd.fit_transform(X)
deri_X = clfsf.fit_transform(X)
peaks_X = peaks.fit_transform(X)

peaksTree.fit(X,y)

p = peaksTree.predict(X)

print(f"Total prediction errors: {abs(p-y).sum()} / {len(y)}")


tp = peaksTree.predict(tX)
print(f"Total prediction errors: {abs(tp-ty).sum()} / {len(ty)}")

export_graphviz(peaksTree[-1],out_file='./tree.dot')
(graph,) = pydot.graph_from_dot_file('tree.dot')
# Write graph to a png file
subprocess.run(['dot','-Tpng',r'C:\Users\hui\codes\pstrace_monitor\tree.dot','-o','test'+'.png'])
graph.write_png('out.png')

peaks_X[0]

len(smoothed_X)

smoothed_X[0]

t,gradient = deri_X[0]
gradient = -gradient

heightlimit = np.quantile(np.absolute(gradient[0:-1] - gradient[1:]), 0.8)

heightlimit
peaks,props = signal.find_peaks(gradient,prominence=heightlimit,width= len(gradient) / 20, rel_height=0.5)
maxpeak_index = props['prominences'].argmax()

tspan = t[-1]-t[0]
peak_pos = peaks[maxpeak_index] / len(gradient) * tspan
peak_pos

peaks
props

plt.plot(gradient)
t

peaks_X[0]

peaks_X

for i in range(0,123):
    smoothed_c = smoothed_X[i]
    t,deri =  deri_X[i]
    left_ips,peak_prominence,peak_width = peaks_X[i]
    curvePeakRange = findTimeVal(t,smoothed_c,left_ips,peak_width)
    xvals = np.linspace(t[0],t[-1],len(deri))
    predictRes = p[i]==y[i]
    fig,ax = plt.subplots()
    ax.plot(xvals,smoothed_c)
    ax.plot(np.linspace(left_ips,left_ips+peak_width,len(curvePeakRange)) ,curvePeakRange )
    ax.set_ylim([0,1.5])
    # deriviative = (smoothed_c[1:]-smoothed_c[0:-1]) / 0.3333333
    # secderivative = (deriviative[1:]-deriviative[0:-1]) / 0.3333333     
    ax.plot(xvals,(deri - np.min(deri) ) / (np.max(deri) -np.min(deri) ) )
    ax.set_title(f'Pm:{peak_prominence:.4f} Prediction {predictRes} P:{p[i]} M:{y[i]}')
# ax.set_ylim([-1,1])


x = np.linspace(-10,10)

y = 1/(1+np.e**x)

plt.plot(y)





len(y)
peaks_X
len(peaks_X)





tpeaks_X = peaks.fit_transform(X)


positive = tpeaks_X[y==1]
negative = tpeaks_X[y==0]
len(negative)
len(positive)

fig,ax = plt.subplots()
ax.plot([i[0] for i in negative],[i[1] for i in negative],'g.')
ax.plot([i[0] for i in positive],[i[1] for i in positive],'r.')
ax.set_xlabel('Ct')
ax.set_ylabel('Peak Prominance')







fig,ax = plt.subplots()
ax.plot([i[0] for i in negative],[i[2] for i in negative],'g.')
ax.plot([i[0] for i in positive],[i[2] for i in positive],'r.')
ax.set_xlabel('Ct')
ax.set_ylabel('Peak Width')
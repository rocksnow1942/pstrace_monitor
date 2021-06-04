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
    return val[t0idx:t1idx]

def removeDuplicates(X,y):
    currents = set()
    ids = []
    for t,c in X:
        if sum(c) in currents:
            ids.append(False)
        else:
            ids.append(True)
            currents.add(sum(c))
    return X[ids],y[ids]
        
    
    

def prediction(Ct,prominence):
    def predictor(X):
        return np.apply_along_axis(lambda x: int(x[0]<=Ct and x[1]>=prominence),1,X)
    return predictor
    
files = glob.glob('/Users/hui/AMS_RnD/Projects/LAMP-Covid Sensor/CapCaTTrainingData_DomeDesign/ProcessedData/!FronzenData_DONTCHANGE/*.picklez')
 
f1 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_0525_export.picklez"
f2 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210520_PnD_export.picklez"
f3 = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCaTTrainingData_DomeDesign\ProcessedData\!FronzenData_DONTCHANGE\20210524_SelectiveExportWithPatientCurves.picklez"

f4 = r"C:\Users\hui\RnD\Users\Hui Kang\backup_0523.picklez"
f5 = r"C:\Users\hui\Desktop\0524_0526results.picklez"
f6 = r"C:\Users\hui\Desktop\today data.picklez"
f7 = r"C:\Users\hui\Desktop\capcat2.picklez"
f8 = r"C:\Users\hui\Desktop\temp\Capcat_0527.picklez"
f9 = r"C:\Users\hui\Desktop\non dtt buffer.picklez"

dataSource = ViewerDataSource()
pickleFiles = [f9] #r"C:\Users\hui\Desktop\saved.picklez"
dataSource.load_picklefiles(pickleFiles)
X,y,names = dataSource.exportXy()

X,y = removeDuplicates(X,y)


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
    ('smooth',Smoother(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('remove time',RemoveTime()),
])

clfsf =  Pipeline([
    ('smooth',Smoother(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('Derivitive',Derivitive(window=31,deg=3)),
    # ('remove time',RemoveTime()),
])


peaks = Pipeline([
    ('smooth',Smoother(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('Derivitive',Derivitive(window=31,deg=3)),
    ('peak',FindPeak())
    # ('remove time',RemoveTime()),
])

peaksPredictor = Pipeline([
    ('smooth',Smoother(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('Derivitive',Derivitive(window=31,deg=3)),
    ('peak',FindPeak()),
    ('predictor',CtPredictor(ct=18.9,prominence=0.01))    
])

peaksTree = Pipeline([
    ('smooth',Smoother(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=90)),
    ('Derivitive',Derivitive(window=31,deg=3)),
    ('peak',FindPeak()),
    ('tree',DecisionTreeClassifier(max_depth=2,min_samples_leaf=4))
    # ('remove time',RemoveTime()),
])
 

smoothed_X = smd.transform(X)
deri_X = clfsf.transform(X)
peaks_X = peaks.transform(X)
peaks_X[0]

peaksTree.fit(X,y)


#my prediction



p = peaksTree.predict(X)

p [0]
for i in p:
    print(i)

errorc = []

for i in np.arange(0.001,0.1,0.001):
    for j in np.arange(15,25,0.1):
        p = prediction(Ct=j,prominence=i)(peaks_X)
        errorc.append((i,j,abs(p-y).sum()))


p = prediction(Ct=19,prominence=0.01)(peaks_X)

p=peaksPredictor.transform(X)

print(f"Total prediction errors: {abs(p-y).sum()} / {len(y)}")


tp = peaksTree.predict(tX)
print(f"Total prediction errors: {abs(tp-ty).sum()} / {len(ty)}")



# export the graph
export_graphviz(peaksTree[-1],out_file='./tree.dot')
(graph,) = pydot.graph_from_dot_file('tree.dot')
# Write graph to a png file

graph.write_png('out.png')

 

col = int(len(p)**0.5)
col=2
row = int(np.ceil(len(p) / col))


fig,axes = plt.subplots(row,col,figsize=(col*4,row*3))
axes = [i for j in axes for i in j]

for i,j in enumerate(y):
    ax = axes[i]
    smoothed_c = smoothed_X[i]
    t,deri,_ =  deri_X[i]
    left_ips,peak_prominence,peak_width, *sd= peaks_X[i]
    curvePeakRange = findTimeVal(t,smoothed_c,left_ips,peak_width)
    xvals = np.linspace(t[0],t[-1],len(deri))
    predictRes = p[i]==y[i]
 
    ax.plot(xvals,smoothed_c,color='red' if y[i] else 'green')
    # plot the signal drop part
    ax.plot(np.linspace(left_ips,left_ips+peak_width,len(curvePeakRange)) ,curvePeakRange,linewidth=4,alpha=0.75 )
    ax.set_ylim([0.4,1.3])
    # deriviative = (smoothed_c[1:]-smoothed_c[0:-1]) / 0.3333333
    # secderivative = (deriviative[1:]-deriviative[0:-1]) / 0.3333333     
    ax.plot(xvals,(deri - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c),'--',alpha=0.8)
    p_n = 'Positive' if y[i] else 'Negative'
    ax.set_title(f'Ct:{left_ips:.1f} Pm:{peak_prominence:.2f} M:{p_n}',
    fontdict={'color':'red' if y[i] else 'green'})
    ax.set_xlabel(names[i],fontdict={'fontsize':8})
# ax.set_ylim([-1,1])
plt.tight_layout()

fig.savefig(r"C:\Users\hui\Desktop\Data till 6/3.png")



x = np.linspace(-10,10)

y = 1/(1+np.e**x)

plt.plot(y)





len(y)
peaks_X
len(peaks_X)





tpeaks_X = peaks.transform(X)


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
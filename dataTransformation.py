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

f4 = r"C:\Users\hui\RnD\Users\Hui Kang\backup_0523.picklez"
f5 = r"C:\Users\hui\Desktop\0524_0526results.picklez"
f6 = r"C:\Users\hui\Desktop\today data.picklez"
f7 = r"C:\Users\hui\Desktop\capcat2.picklez"
f8 = r"C:\Users\hui\Desktop\temp\Capcat_0527.picklez"
f9 = r"C:\Users\hui\Desktop\tmp\non dtt buffer.picklez"

dataSource = ViewerDataSource()
pickleFiles = [f9] #r"C:\Users\hui\Desktop\saved.picklez"
dataSource.load_picklefiles(pickleFiles)
X,y,names,devices = dataSource.exportXy()

X,y,names = removeDuplicates(X,y,names)


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


smoothed_X = smoothT.transform(X)
deri_X = deriT.transform(X)
peaks_X = peaksT.transform(X)


#my prediction

p = prediction(Ct=19,prominence=0.01)(peaks_X)

print(f"Total prediction errors: {abs(p-y).sum()} / {len(y)}")





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




fig,ax = plt.subplots()
i = 46
smoothed_c = smoothed_X[i]
t,deri,_ =  deri_X[i]
left_ips,peak_prominence,peak_width, *sd= peaks_X[i]

tofit = findTimeVal(t,smoothed_c,left_ips-fitwindow,fitwindow)

# find the threshold Ct
fitpara = np.polyfit(np.linspace(max(left_ips-4,t[0]),left_ips,len(tofit)),np.array(tofit,dtype=float),deg=1)
fitres = np.poly1d(fitpara)
threshold = (tofit[-1]) * 0.03
thresholdline = np.poly1d(fitpara + np.array([0,-threshold] ))

tosearch = findTimeVal(t,smoothed_c,left_ips,30)
tosearchT = np.linspace(left_ips,30,len(tosearch))
thresholdSearch = thresholdline(tosearchT) - findTimeVal(t,smoothed_c,left_ips,30)
thresholdCt = left_ips
for sT,sthre in zip(tosearchT,thresholdSearch):
    if sthre > 0:
        thresholdCt = sT
        break
        
curvePeakRange = findTimeVal(t,smoothed_c,left_ips,peak_width)
xvals = np.linspace(t[0],t[-1],len(deri)) 
ax.plot(xvals,smoothed_c,color='red' if y[i] else 'green')
# plot the signal drop part
ax.plot(np.linspace(left_ips,left_ips+peak_width,len(curvePeakRange)) ,curvePeakRange,linewidth=4,alpha=0.75 )
ax.set_ylim([0.4,1.3])
# deriviative = (smoothed_c[1:]-smoothed_c[0:-1]) / 0.3333333
# secderivative = (deriviative[1:]-deriviative[0:-1]) / 0.3333333     
ax.plot(xvals,(deri - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c),'--',alpha=0.8)
# ax.plot(xvals,fitres(xvals),'b-.')
ax.plot(xvals,thresholdline(xvals),'b-.',alpha=0.7)
ax.plot([thresholdCt,thresholdCt],[0,2],'k-')
p_n = 'Positive' if y[i] else 'Negative'
ax.set_title(f'{i}-Ct:{left_ips:.1f} tCt:{thresholdCt:.1f} Pm:{peak_prominence:.2f} M:{p_n}',
fontdict={'color':'red' if y[i] else 'green'})
ax.set_xlabel(names[i],fontdict={'fontsize':8})

np.linspace(left_ips-4,left_ips,len(tofit))
tofit





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
    smoothed_c = smoothed_X[i]
    t,deri,_ =  deri_X[i]
    left_ips,peak_prominence,peak_width, *sd= peaks_X[i]
    
    tofit = findTimeVal(t,smoothed_c,left_ips-fitwindow,fitwindow)    
    # find the threshold Ct
    fitpara = np.polyfit(np.linspace(max(left_ips-4,t[0]),left_ips,len(tofit)),np.array(tofit,dtype=float),deg=degree)
    fitres = np.poly1d(fitpara)
    threshold = (tofit[-1]) * 0.05
    thresholdline = np.poly1d(fitpara + np.array(list(range(degree)) +[-threshold] ))
    
    tosearch = findTimeVal(t,smoothed_c,left_ips,30)
    tosearchT = np.linspace(left_ips,30,len(tosearch))
    thresholdSearch = thresholdline(tosearchT) - findTimeVal(t,smoothed_c,left_ips,30)
    thresholdCt = left_ips
    for sT,sthre in zip(tosearchT,thresholdSearch):        
        if sthre > 0:
            break
        thresholdCt = sT
            
    curvePeakRange = findTimeVal(t,smoothed_c,left_ips,peak_width)
    xvals = np.linspace(t[0],t[-1],len(deri)) 
    ax.plot(xvals,smoothed_c,color='red' if y[i] else 'green')
    # plot the signal drop part
    ax.plot(np.linspace(left_ips,left_ips+peak_width,len(curvePeakRange)) ,curvePeakRange,linewidth=4,alpha=0.75 )
    ax.set_ylim([0.4,1.3])
    # deriviative = (smoothed_c[1:]-smoothed_c[0:-1]) / 0.3333333
    # secderivative = (deriviative[1:]-deriviative[0:-1]) / 0.3333333     
    ax.plot(xvals,(deri - np.min(deri) ) / (np.max(deri) -np.min(deri) ) * (np.max(smoothed_c)-np.min(smoothed_c)) + np.min(smoothed_c),'--',alpha=0.8)
    # ax.plot(xvals,fitres(xvals),'b-.')
    ax.plot(xvals,thresholdline(xvals),'b-.',alpha=0.7)
    ax.plot([thresholdCt,thresholdCt],[0,2],'k-')
    p_n = 'Positive' if y[i] else 'Negative'
    ax.set_title(f'{i}-Ct:{left_ips:.1f} tCt:{thresholdCt:.1f} Pm:{peak_prominence:.2f} M:{p_n}',
    fontdict={'color':'red' if y[i] else 'green'})
    ax.set_xlabel(names[i],fontdict={'fontsize':8})
    result.append([p_n,left_ips,thresholdCt,devices[i]])
# ax.set_ylim([-1,1])
plt.tight_layout()



import seaborn as sns
import pandas as pd


label = []
data = []
Ct = []
thresholdCt = []


for i,j,k,d in result:
    label.append(i)
    data.append(k-j)
    Ct.append(j)
    thresholdCt.append(k)
    print(f"{i}, {k-j:.2f}")


df = pd.DataFrame({'label':label,'data':data,'CT':Ct,'ThreshldCt':thresholdCt,'Device':devices})  
sns.violinplot(x=label,y=data)




ax = sns.catplot(x="label",y="ThreshldCt",data = df,kind='swarm',hue='Device')

fig,ax = plt.subplots()
sns.swarmplot(y="label",x="CT",data = df,ax=ax)


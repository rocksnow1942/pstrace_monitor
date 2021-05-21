from utils._util import ViewerDataSource
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from utils.calling_algorithm import traceProcessPipe,Smooth,LinearSVC,SmoothScale,train_model,cross_validation
from sklearn.metrics import precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score,StratifiedKFold
from sklearn.base import BaseEstimator, TransformerMixin, clone
 
 
f = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\CapCadTrainingData_DomeDesign\ProcessedData\20210518_CapCadTraining 0513-0518 N7 Model.picklez"



dataSource = ViewerDataSource()
pickleFiles = [f] #r"C:\Users\hui\Desktop\saved.picklez"
dataSource.load_picklefiles(pickleFiles)
X,y = dataSource.exportXy()


print('X data length is : '+str(len(X)))
print('y data length is : '+str(len(y)))
print("Total Positive Data: "+str(sum(y)))
print("Total Negative Data: "+str(len(y)-sum(y)))
X[0]
y[0]
t,c = X[0]
fig,ax = plt.subplots()
ax.plot(t,c)
ax.set_ylim([0,30])


plt.plot(t,c,)

smoother = Smooth(outlier_para={"stddev":2,},
smooth_para={"windowlenth":15,"window":'hanning'},
extractTP_para={"cutoffStart":0,"cutoffEnd":30,"n":90})

smoothed_X = smoother.transform(X)
len(smoothed_X)
for i in range(0,109):
    smoothed_c = smoothed_X[i]

    fig,ax = plt.subplots()
    ax.plot(np.linspace(0,30,90),smoothed_c)
    ax.set_ylim([0,1])

    deriviative = (smoothed_c[1:]-smoothed_c[0:-1]) / 0.3333333
    secderivative = (deriviative[1:]-deriviative[0:-1]) / 0.3333333



    fig,ax = plt.subplots()
    # ax.plot(np.linspace(0,30,90),smoothed_c)
    ax.plot(np.linspace(0,30,89),-deriviative)
# ax.set_ylim([-1,1])


x = np.linspace(-10,10)

y = 1/(1+np.e**x)

plt.plot(y)
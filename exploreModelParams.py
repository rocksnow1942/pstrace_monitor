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
import joblib
 
 
f1 = r"C:\Users\hui\Desktop\0518Data Remove Outlier.picklez"
f2 = r"C:\Users\hui\Desktop\0518Data No Remove Outlier.picklez"
f3 = "/Users/hui/AMS_RnD/Projects/LAMP-Covid Sensor/CapCadTrainingData_DomeDesign/ProcessedData/!FronzenData_DONTCHANGE/20210519_JP garage data exported.picklez"
f4 = "/Users/hui/Desktop/20210520_PnD_export.picklez"
f5 = "/Users/hui/Desktop/0521PatientData.picklez"


dataSource = ViewerDataSource()
pickleFiles = [f3,f4,f5] #r"C:\Users\hui\Desktop\saved.picklez"
dataSource.load_picklefiles(pickleFiles)
X,y = dataSource.exportXy()

print('X data length is : '+str(len(X)))
print('y data length is : '+str(len(y)))
print("Total Positive Data: "+str(sum(y)))
print("Total Negative Data: "+str(len(y)-sum(y)))


#load testing dataSource
testDataSource = ViewerDataSource()
testDataSource.load_picklefiles([
f5
])
tX,ty = testDataSource.exportXy()


# draw figures
def drawFig(X,y,saveas=None):
    fig,axes = plt.subplots(12,16,figsize=(32,20))
    axes = [i for j in axes for i in j]
    for d,c,ax in zip(X,y,axes):
        if len(d) == 2:
            ax.plot(d[0],d[1])
        else:
            ax.plot(d)
            ax.set_ylim([-2,2])
        ax.set_title('Positive' if c else 'Negative')
    plt.tight_layout()    
    if saveas:
        plt.savefig(f'{saveas}.svg')
    else:
        plt.show()

        
        
def k_fold_validation(clfsf):        
    # k-fold cross_validation
    skfold = StratifiedKFold(n_splits=10,random_state=42, shuffle=True)
    precision = []
    recall = []
    for train_idx, test_idx in skfold.split(X,y):    
        cloneclf = clone(clfsf)
        X_train_fold = X[train_idx]
        y_train_fold = y[train_idx]
        print(f'total tran {len(y_train_fold)}, total positive {y_train_fold.sum()}')
        X_test_fold = X[test_idx]
        y_test_fold = y[test_idx]
        cloneclf.fit(X_train_fold,y_train_fold)    
        precision.append(precision_score(y_test_fold,cloneclf.predict(X_test_fold),))
        recall.append(recall_score(y_test_fold,cloneclf.predict(X_test_fold),))

    fig,axes = plt.subplots(2,1,figsize=(4,6))
    axes[0].hist(precision)
    axes[0].set_title('precision')
    axes[1].set_title('recall')
    axes[1].hist(recall)
    plt.tight_layout()
    return fig






# train with the smooth-Scale method. 
# the training result doesn't make sense most of the time.
clfsf = Pipeline([('smoothScale',SmoothScale(extractTP_para={'cutoffStart':5,'cutoffEnd':20,'n':50})),
                ('svc',LinearSVC(max_iter=100000))])
# train the transformer
scT = clfsf[0:-1]
Xs = scT.fit_transform(X)
clfsf.fit(X,y)    

# joblib.dump(clfsc,'smooth 10-40.model')

p = clfsf.predict(X)

print(f"Total prediction errors: {abs(p-y).sum()} / {len(y)}")




# train with the LinearSVC and smooth. 
cutoffStart = 5
cutoffEnd = 30
clfsf =  Pipeline([('smooth',SmoothTruncateNormalize(extractTP_para={'cutoffStart':cutoffStart,'cutoffEnd':cutoffEnd,'n':50})),
    ('svc',LinearSVC(max_iter=100000))])
    
tF = clfsf[0:-1]

Xs = tF.transform(X)

clfsf.fit(X,y)

p = clfsf.predict(X)

print(f"Total prediction errors: {abs(p-y).sum()} / {len(y)}")

tp = clfsf.predict(tX)

print(f"Total prediction errors: {abs(tp-ty).sum()} / {len(ty)}")

# plot k fold validation 
fig=k_fold_validation(clfsf)


joblib.dump(clfsf,'smooth 5-25.model')





# train with the LinearSVC and stepwise methods. 
cutoffStart = 5
cutoffEnd = 30
normStart = 5
normEnd = 10
clfsf =  Pipeline([
    ('smooth',Smooth(stddev=2,windowlength=11,window='hanning')),
    ('normalize', Normalize(mode='mean',normalizeRange=(normStart,normEnd))),
    ('truncate',Truncate(cutoffStart=cutoffStart,cutoffEnd=cutoffEnd,n=50)),
    ('remove time',RemoveTime()),
    ('svc',LinearSVC(max_iter=100000))])
    


clfsf.fit(X,y)
tF = clfsf[0:-1]
Xs = tF.transform(X)

p = clfsf.predict(X)

print(f"Total prediction errors: {abs(p-y).sum()} / {len(y)}")

fig=k_fold_validation(clfsf)



# calculate scores and dertermine vector
coef = clfsf[-1].coef_
intercept = clfsf[-1].intercept_
calc = Xs*coef

df = clfsf.decision_function(X)





# plot each training data point. 
# will plot each transformed data, then plot predicted errors as red,
# user marked Negative as green usermarked positive as blue.
total = len(X)
l = np.ceil( total**0.5 )
h = np.ceil(total / l)
fig,axes = plt.subplots(int(l),int(h),figsize=(l*2,h*1.92))
axes = [i for j in axes for i in j]
for x,d,c,n,ax,dfi,calci in zip(X,Xs,y,p,axes,df,calc):    
    # ax.set_ylim([0.2,1.05])
    ax.set_ylim([0,30])
    uv = 'M:P' if c else 'M:N'
    pv = 'P:P' if n else 'P:N'
    if c!=n:
        color='red' 
    else:
        color = 'blue' if c else 'green'        
    ax.plot(np.linspace(cutoffStart,cutoffEnd,len(d)),
            d*(max(x[1][cutoffStart*3:cutoffEnd*3])) - 4 ,'-',color=color)
    # ax.plot(np.linspace(cutoffStart,cutoffEnd,len(calci)) ,calci,'-',color='purple')
    ax.plot(np.linspace(0,30,len(x[1])),x[1],'-',color=color)
    ax.set_title(f"{uv} {pv} Score:{dfi:.2f}")
plt.tight_layout()

plt.savefig('20210523_Nmodelnorm5_10.png',dpi=100)


 
joblib.dump(clfsf,'0519_56data.model')











model = joblib.load('smooth 5-20.model')

abs(model.predict(X) - y).sum()




# plot all transformed data in 1 plot.

fig,ax = plt.subplots()
labels = set()
for x,d,c,n in zip(X,Xs,y,p):    
    # ax.set_ylim([0.2,1.05])
    ax.set_ylim([0.3,1.3])
    uv = 'M:P' if c else 'M:N'
    pv = 'P:P' if n else 'P:N'
    if c!=n:
        color='red' if c else 'purple'
        label='FN' if c else 'FP'
        alpha=1
    else:
        color = 'blue' if c else 'green'        
        label = 'P' if c else 'N'
        alpha=0.25
    if label in labels:
        label=None
    else:
        labels.add(label)
    
    ax.plot(np.linspace(cutoffStart,cutoffEnd,len(d)),
            d ,'-',alpha=alpha,color=color,label=label)
    # ax.plot(np.linspace(0,30,len(x[1])),x[1],'-',color=color)
    # ax.set_title(f"{uv} {pv}")
ax.legend()
ax.set_title('20210523_Nmodel-normlize 5-10min')
plt.tight_layout()


plt.savefig('./20210523_Nmodel_norm5-10.png')























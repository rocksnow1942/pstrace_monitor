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
from sklearn.metrics import precision_score, recall_score
from sklearn.svm import LinearSVC
from sklearn.preprocessing import StandardScaler
import joblib
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score,StratifiedKFold
from sklearn.metrics import precision_score, recall_score
import math

f1 = r"C:\Users\hui\RnD\Projects\Device Data Archive\Positive (Real NTC as Positive).picklez"
f2 = r"C:\Users\hui\RnD\Projects\Device Data Archive\Negative (Real NTC as Positive).picklez"

f3 = r"C:\Users\hui\RnD\Projects\Device Data Archive\Positive (Real NTC as Negative).picklez"
f4 = r"C:\Users\hui\RnD\Projects\Device Data Archive\Negative (Real NTC as Negative).picklez"

file = r"C:\Users\hui\Desktop\saved.picklez"

ds = ViewerDataSource()

ds.load_picklefiles([file])

X,y = ds.exportXy()

len(X)



X=[list(i) for i in X ]

with open ('X.json','wt') as f:
    json.dump(X,f)

with open ('y.json','wt') as f:
    json.dump([int(i) for i in y],f)

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


sT = Smooth(extractTP_para={'cutoffStart':0,'cutoffEnd':40,'n':90})

len



Xs = sT.fit_transform(X)


sT1 = Smooth(extractTP_para={'cutoffStart':0,'cutoffEnd':60,'n':90})
Xs1 = sT1.fit_transform(X)


plt.plot(X[0][0],X[0][1])

plt.plot(Xs1[0])


plt.plot(Xs[0])




# train with the smooth-Scale method. 
# the training result doesn't make sense most of the time.
clfsc = Pipeline([('smoothScale',SmoothScale(extractTP_para={'cutoffStart':0,'cutoffEnd':30,'n':90})),
                ('svc',LinearSVC(max_iter=100000))])
# train the transformer
scT = clfsc[0:-1]
Xs = scT.fit_transform(X)
clfsc.fit(X,y)    

joblib.dump(clfsc,'smooth 10-40.model')

p = clfsc.predict(X)

print(f"Total prediction errors: {abs(p-y).sum()} / {len(y)}")




# train with the LinearSVC and smooth. 
clfsf =  Pipeline([('smooth',Smooth(extractTP_para={'cutoffStart':0,'cutoffEnd':30,'n':90})),
    ('svc',LinearSVC(max_iter=100000))])
    
tF = clfsf[0:-1]

Xs = tF.fit_transform(X)

clfsf.fit(X,y)

p = clfsf.predict(X)
print(f"Total prediction errors: {abs(p-y).sum()} / {len(y)}")
# save classifier.
joblib.dump(clfsf,'smooth 10-40.model')


# plot each training data point. 
# will plot each transformed data, then plot predicted errors as red,
# user marked Negative as green usermarked positive as blue.
total = len(X)
l = np.ceil( total**0.5 )
h = np.ceil(total / l)
fig,axes = plt.subplots(int(l),int(h),figsize=(l*2,h*1.62))
axes = [i for j in axes for i in j]
for d,c,n,ax in zip(Xs,y,p,axes):    
    ax.set_ylim([0.2,1.05])
    uv = 'M:P' if c else 'M:N'
    pv = 'P:P' if n else 'P:N'
    if c!=n:
        color='red' 
    else:
        color = 'blue' if c else 'green'        
    ax.plot(np.linspace(0,30,len(d)),d,'-',color=color)
    ax.set_title(f"{uv} {pv}")
plt.tight_layout()    

plt.savefig('20210428 Smooth 0-30 predict.png',dpi=100)


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
plt.savefig('SmoothScale 10-40 score.png')

 










































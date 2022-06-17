import pandas as pd
import seaborn as sns
import scipy.stats as stat
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from itertools import chain, islice
import json

file = r"C:\Users\hui\Desktop\data.csv"
file = r"C:\Users\hui\Desktop\echemdata\RIdata.csv"

file = r"C:\Users\hui\Desktop\echemdata\DSI_data.csv"

file = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\DSI_data_export.csv"

file = r"C:\Users\hui\codes\pstrace_monitor\plottingScripts\clinical_output.csv"

df = pd.read_csv(file)

df = df.fillna("")


df['channel'] = [name.split('-')[-1] for name in df.Name]

toplotdf = df[df.Sindex != ""  ]


toplotdf.to_csv(r"C:\Users\hui\Desktop\test.CSV",index = False, )


toplotdf = df[(df.Predict == 'Positive') & (df['channel'] == 'C1')  ]

toplotdf = df[(df.Predict == 'Negative') & (df['channel'] == 'C1')]

negdf[negdf.Mark == 'Positive']


(df[(df.Mark == 'Negative') & (df.Predict == 'Negative') & (df['channel'] == 'C1')]).shape


c1df = df[df['channel'] == 'C1']
 


toplotdf = df[df.Copy!=100]
toplotdf = df[ (df.Date>=722) & (df.Copy=='50')]
toplotdf = df[ (df.Date>=726) & (df.Target == 'N7') ]

toplotdf = df[(df.Target == 'N7')  & (df.Method=='VNFI') ] # & (df.Copy !='NTC')

toplotdf = df[(df.Target == 'RP4') & (df.Method=='VNFI') ]

toplotdf = df[df.Target=='RP4']

toplotdf = df[ (df.Date>=722) & (df.Target == 'RP4') & (df.Copy != 'NTC') ]

toplotdf = df[ (df.Date>=727) & (df.Target == 'N7') ]

toplotdf = df[ (df.Date>=727) & (df.Target == 'N7') & (df.Saliva == 'Fresh727') ]

toplotdf = df[ (df.Date>=728) & (df.Target=='N7') ] 

toplotdf = df[(df.Date==730) & (df.Saliva == 'DSI') & (df.Target=='RP4')]

toplotdf = df[(df.OD > 0) & ( df.Copy > 0) & (df.Target=='N7') & (df.Saliva.isin(['DSI','Fresh727','Fresh728']))]
toplotdf



toplotdf = df[(df.Date==730) & (df.Saliva == 'DSI') & (df.Target=='N7') & (df.Copy == 50)]

# kind can be box, violin, boxen, point, bar, swarm, strip
# category plot
var_name = 'Who'
value_name = 'SD'
f = sns.catplot(x=var_name,y=value_name,data=toplotdf,kind='swarm',hue='RIM', height=3,aspect=1.2,)
f.fig.axes[0].set_title('N7 SD')



toplotdf.to_csv('./predict_positive.csv')


# scatter plot
sns.scatterplot(x='OD',y='CT', data=toplotdf,hue='Method',legend="auto")
plt.legend(bbox_to_anchor=(1.02, 0.01), loc='lower left', borderaxespad=0)

toplotdf.head()

# scatter plot
sns.catplot(x='Mark',y='Sd5m', data=toplotdf,hue='Predict',legend="auto", kind='swarm')



plt.legend(bbox_to_anchor=(1.02, 0.01), loc='lower left', borderaxespad=0)

toplotdf[toplotdf.Mark == 'Positive']

fig, ax = plt.subplots(figsize=(8,8))
sns.scatterplot(x='Pr',y='Sd5m', data=toplotdf,hue='Mark', ax=ax)


plt.legend(bbox_to_anchor=(1.02, 0.01), loc='lower left', borderaxespad=0)




# 
# 
# f = sns.catplot(x=var_name,y=value_name,data=toplotdf,kind='swarm',hue='Method', height=3,aspect=1.2)
# f.fig.axes[0].set_title('N7 SD')
# 
# 
# f = sns.catplot(x=var_name,y=value_name,data=toplotdf,kind='swarm',hue='Copy', height=3,aspect=1.2)
# 
# f.fig.axes[0].set_title('CT')
# 
# 
# # f.savefig('tosave.svg')
# 
# 
# toplotdf
# 
# stat.ttest_ind(toplotdf[toplotdf.Method=='AF'].PR,toplotdf[toplotdf.Method=='AF2FF'].PR)
# 
# 
# toplotdf[toplotdf.Method=='Normal'].Value.mean()
# toplotdf[toplotdf.Method=='Vortex'].Value.mean()



df = pd.read_csv(r"C:\Users\hui\Desktop\Download.CSV",thousands=',')


from datetime import datetime



agg.index
agg = df[df.Type!='General Withdrawal'].groupby(pd.to_datetime(df.Date).apply(lambda x:x.strftime('%m'))).sum()

agg['Date'] = [datetime(2000,int(i),1).strftime('%B') for i in agg.index.tolist()]


ax = sns.barplot(x='Date',y='Net',data=agg, )
ax = ax.figure.axes[0]
ax.set_xticklabels(agg.Date,rotation=45)
ax.set_ylabel('Net income')
ax.set_yticks([i*1e4 for i in range(8)])
ax.set_yticklabels([f"{i*10}k" for i in range(8)])





set_xticklabels

df[df.Type!='General Withdrawal'].Net.sum()





c1df = df[(df.channel == 'C1')]

 

def predictor(ctThreshold, sdThreshold, prThreshold):
    def wrap(df):
        result = []
        for row in df.iterrows():
            data = row[1]
            ct, pr, sd = data.hyperCt, data.Pr, data.Sd5m
            if pr < prThreshold:
                result.append('Negative')
            else:
                if sd >= sdThreshold and ct < ctThreshold:
                    result.append('Positive')
                else:
                    result.append('Negative')
        return result
    return wrap

with open('matrixFull.json','wt') as f:
    json.dump(resultMatrix.tolist(), f)

ctT = 30
sdT = 0.106382
prT = 0.2


ctRange = np.linspace(15, 30, 200)
sdRange = np.linspace(0.06, 0.18, 200)
resultMatrix = np.zeros(shape = (6,len(sdRange), len(ctRange)))
 
for i, ctT in enumerate(ctRange):
    for j, sdT in enumerate(sdRange):
        predict = predictor(ctT, sdT, prT)(c1df)
        labels = ['Positive','Negative']
        cfmatrix = confusion_matrix (c1df.Mark, predict, labels=labels)
        result = precision_recall_fscore_support(c1df.Mark, predict, labels=labels)
        tmp = np.array(list(islice(chain(*result),0,6)))
        resultMatrix[:, j, i] = tmp
        
        # print(f'Ct={ctT}, SD={sdT:.3f}, Pr={prT:.3f}')
        # for name, i in zip(['Precision','Recall','F1 Score'],result):
        #     print(f"{name} , {i[0]:.4f} , {i[1]:.4f}")
        # print('')
        #  
 

 
fig, axes = plt.subplots(2, 3, figsize=(12, 8))

axes = [i for j in zip(*axes) for i in j]

labels = ['Positive','Negative']
items = ['Precision', 'Recall', 'F1 Score']
for i, ax in enumerate(axes):
    itemIdx, labelIdx = divmod(i, 2)
    label = labels[labelIdx]
    item = items[itemIdx]
    ax.imshow(resultMatrix[i], aspect=0.1)
    ax.set_title(f'{label} {item}')
    
    xtick = [int(i) for i in np.linspace(0, len(ctRange)-1, 10)]
    
    ax.set_xticks(xtick)
    ax.set_xticklabels([f"{ctRange[i]:.1f}" for i in xtick], rotation=45)
    ax.set_xlabel('Ct / min' )
    
    ytick = [int(i) for i in np.linspace(0, len(sdRange)-1, 8)]
    ax.set_yticks(ytick)
    ax.set_yticklabels([f"{sdRange[i]:.3f}" for i in ytick])
    ax.set_ylabel('SD')
    
plt.tight_layout()
plt.show()














import pandas as pd
import seaborn as sns
import scipy.stats as stat
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from itertools import chain, islice
import json
import time

file = r"C:\Users\hui\Work\HuiWork\Covid_Reader\clinical_data_analysis\20220609\clinical_output.csv"

adjusted = r"C:\Users\hui\Work\HuiWork\Covid_Reader\clinical_data_analysis\20220609\20220602clinical_adjusted.csv"

df = pd.read_csv(file)

adjdf = pd.read_csv(adjusted, dtype='str').fillna('')
touseIDs = set([i for i in adjdf.ID if i])

rowbool = [i.split('-')[1] in touseIDs for i in df.Name]




df = df[rowbool]




df.loc[:,'channel'] = [name.split('-')[-1] for name in df.Name]

 

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


 








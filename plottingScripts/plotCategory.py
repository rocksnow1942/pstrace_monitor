import pandas as pd
import seaborn as sns
import scipy.stats as stat
import matplotlib.pyplot as plt
import numpy as np

file = r"C:\Users\hui\Desktop\data.csv"
file = r"C:\Users\hui\Desktop\echemdata\RIdata.csv"

file = r"C:\Users\hui\Desktop\echemdata\DSI_data.csv"

file = r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\DSI_data_export.csv"


df = pd.read_csv(file)
df
df = df.fillna("")

toplotdf = df[df.Sindex != ""  ]


toplotdf.to_csv(r"C:\Users\hui\Desktop\test.CSV",index = False, )




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






# scatter plot
sns.scatterplot(x='OD',y='CT', data=toplotdf,hue='Method',legend="auto")
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
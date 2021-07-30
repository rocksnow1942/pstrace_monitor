import pandas as pd
import seaborn as sns
import scipy.stats as stat

"""
plot category scatter plot from data in a table.

Step 1:
generate a csv file like this: (first row is categorical label)
   VS	 VINS	  VNS	Copy
0.268	0.241	0.167	300
0.250	0.261	0.204	300
0.247	0.223	0.185	300
0.278	0.201	0.209	300
0.172	0.250	0.086	100
0.189	0.190	0.170	100
0.232	0.281	0.220	100
0.250	0.248	0.174	100

Step 2: change parameters below then run script.
To save figure, uncomment the f.savefig() line.

"""



file = r"C:\Users\hui\Desktop\data.csv"
file = r"C:\Users\hui\Desktop\echemdata\RIdata.csv"

file = r"C:\Users\hui\Desktop\echemdata\DSI_data.csv"


df = pd.read_csv(file)

df




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

toplotdf = df[(df.Date==729) & (df.Saliva == 'DSI')] 


var_name = 'Funnel'
value_name = 'CT'


# kind can be box, violin, boxen, point, bar, swarm, strip
f = sns.catplot(x=var_name,y=value_name,data=toplotdf,kind='swarm',hue='Target', height=3,aspect=1.2)
f.fig.axes[0].set_title(' CT')
















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





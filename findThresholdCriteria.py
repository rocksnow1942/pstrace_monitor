import pandas as pd
import seaborn as sns
from utils.calling_algorithm import *
import numpy as np



def extractSaliva(row):
    if 'OD10.5' in row:
        return 'OD10.5'
    elif 'OD6' in row:
        return 'OD6'
    elif 'HI-PS' in row:
        return 'HI-PS'
    
def removeRP4(row):
    return not ( ('RP4' in row) and row.endswith('C4'))



df = pd.read_csv('/Users/hui/AMS_RnD/Projects/LAMP-Covid Sensor/Data Export/0706_0709DSMData.csv',skip_blank_lines=True)

df = df.dropna()

df.Saliva = list(df.Name.apply(extractSaliva))

df = df.loc[df.Name.apply(removeRP4),:]
labels = [int(i=='Positive') for i in df['User Mark']]


list(df.Saliva)

ax = sns.catplot(x='User Mark',y='hyperCt',data=df,hue='Saliva',kind='swarm')
ax.fig.axes[0].plot([-.2,1.2],[22,22],'k-')
ax.fig.axes[0].set_title('CT threshold = 22min')
ax.savefig('Ctthreshold.png')





ax = sns.catplot(x='User Mark',y='Prominence',data=df,hue='Saliva',kind='swarm')
ax.fig.axes[0].plot([-.2,1.2],[0.22,0.22],'k-')
ax.fig.axes[0].set_title('Prominence threshold = 0.22')
ax.savefig('ProminenceThreshold.png')




ax = sns.catplot(x='User Mark',y='SD_5min',data=df,hue='Saliva',kind='swarm')
ax.fig.axes[0].plot([-.2,1.2],[0.05,0.05],'k-')
ax.fig.axes[0].set_title('SD@5 threshold = 0.05')
ax.savefig('SDthre.png')



# compare predictor thresholds using grid search
# fetch a df to predict, in predictor, last data is ct, 5th data is sd@5, 1st data is prominence

testdf = df[['Name','Prominence','hyperCt','Name','Name','SD_5min','hyperCt']]


gridres = []
counter = 0
total = int((25-18)/0.2 * (0.5-0.1)/0.02 * (0.25-0.05)/0.003)
print(f'Total testing conditions: {total}')

for ct in np.arange(18,25,0.2):
    for pro in np.arange(0.1,0.5,0.02):
        for sd in np.arange(0.05,0.25,0.003):
            counter+=1
            if counter%10000 ==0:
                print(f'{counter} / {total} \r')
            p = CtPredictor(ct,pro,sd)
            
            error = (p.transform(testdf)[:,0] != labels).sum()
            gridres.append(((ct,pro,sd),error))






            
# find minimum error
bestpara = min(gridres,key=lambda x:x[-1])
print('Least Error: Ct:{:.2f}, prominence:{:.2f},sd:{:.2f}; Error:{}'.format(*bestpara[0],bestpara[1]))

bests = list(filter(lambda x:x[-1]==bestpara[1],gridres,))
len(bests)
bests[-1]




# print optimal result:
p = CtPredictor(22, 0.22, 0.05)
error = (p.transform(testdf)[:,0] != labels).sum()
error
p.transform(testdf)[:,0]


df.Prediction = list(p.transform(testdf)[:,0])

df.to_csv('~/Desktop/prediction.csv')







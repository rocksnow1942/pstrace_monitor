import pandas as pd
import random
import seaborn as sns
import matplotlib.pyplot as plt

df = pd.read_csv(r"C:\Users\hui\Work\HuiWork\Figures\20210628_LOD\20210628Cts.csv")

# get NTC data:
ntcs = list(df[df.Copy=='NTC'].hCt)
ntcs.sort()
ntcs = ntcs[200:]
random.shuffle(ntcs)
for i in ntcs[0:20]:
    print(i)

# get 12.5cp
cp125 = list(df[df.Copy=='25cp'].hCt)
cp125.sort()
cp125  = cp125[20:]
random.shuffle(cp125)
for i in cp125[0:]:
    print(i)
    
    
#get 25cp

cp50 = list(df[df.Copy=='50cp'].hCt)
cp50.sort()
cp50
cp50[50]
cp50  = cp50[50:]
random.shuffle(cp50)
for i in cp50[0:]:
    print(i)


# general lod curve
df = pd.read_csv(r"C:\Users\hui\Work\HuiWork\Figures\20210628_LOD\LOD_4repeat.csv")

fig,ax = plt.subplots(figsize=(4,3))
sns.swarmplot(x='Copy',y='Mt',data = df,ax=ax)
ax.set_ylabel('Mt / minutes')
ax.set_xticklabels([0,12.5,25,50,100,200])
ax.set_xlabel('Copies of SARS-CoV-2 / uL')
ax.set_ylim([0,34])
ax.set_title('LoD Curve')
ax.plot([-0.2,5.2], [20.4,20.4],'k--')
plt.tight_layout()
fig.savefig(r'C:\Users\hui\Work\HuiWork\Figures\20210628_LOD.svg')






#confirmative lod curve
df = pd.read_csv(r"C:\Users\hui\Work\HuiWork\Figures\20210628_LOD\LOD_reliability.csv")

fig,ax = plt.subplots(figsize=(6,4))
sns.swarmplot(x='Copy',y='Mt',data = df,ax=ax,color='black')
sns.violinplot(x='Copy',y='Mt',data=df,ax=ax,inner=None)
ax.set_ylabel('Mt / minutes')
ax.set_xticklabels([0,12.5,25])
ax.set_xlabel('Copies of SARS-CoV-2 / uL')
ax.set_ylim([0,34])
ax.set_title('LoD Reliability')
ax.plot([-0.2,2.2], [20.4,20.4],'k--')
plt.tight_layout()

fig.savefig(r'C:\Users\hui\Work\HuiWork\Figures\reliability.svg')



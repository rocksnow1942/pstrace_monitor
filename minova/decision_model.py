"""
better model:
PCA on descd1 and descd2, from current data, this two combination seems to be better. 
"""
from sklearn.datasets import load_iris
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.tree import export_graphviz
import subprocess
from feature_generation import generate_feature_from_col,gather_all_data
import matplotlib.pyplot as plt
from itertools import combinations
from mymodule import ft 
import pydot

(graph,) = pydot.graph_from_dot_file('myclf.dot')
# Write graph to a png file
graph.write_png('new tree.png')

def target(name):
    if 'iNTC' in name or 'EP' in name:
        return 0
    else:return 1

def export_tree_graph(clf,feature_names,class_names,filename='new_tree'):
    export_graphviz(clf,out_file='temp_tree.dot',
    feature_names=feature_names,class_names=class_names,rounded=True,filled=True)
    subprocess.run(['dot','-Tpng','temp_tree.dot','-o',filename+'.png'])
    
def feature_plot(df,x_feature,y_feature,threshold,ax=None):
    if ax==None:
        fig,ax = plt.subplots()
    ax.plot(df.loc[df['target']==0,x_feature],df.loc[df['target']==0,y_feature],'.',label='Negative')
    ax.plot(df.loc[df['target']==1,x_feature],df.loc[df['target']==1,y_feature],'.',label='Positive')
    ymin = df.loc[:,y_feature].min()
    ymax = df.loc[:,y_feature].max()
    ax.plot([threshold,threshold],[ymin,ymax])
    ax.set_xlabel(x_feature)
    ax.set_ylabel(y_feature)
    ax.legend()
    return ax
    
def predict(res):
    if res['descd1'] <= -0.07:
        return 1 
    else:
        return 0 

def predict_with_time(df):
    fig,axes = plt.subplots(9,9,figsize=(18,18))
    axes = [i for j in axes for i in j]        
    for c,ax in zip(df.columns,axes):
        col = df[c]
        timepoints = []
        prediction = []
        for i in range(55,col.shape[0],10):
            subcol = col.iloc[0:i]
            res = predict(generate_feature_from_col(subcol))
            prediction.append(res)
            timepoints.append(col.index[i])
        predictcol = pd.Series(prediction,index =pd.Index(timepoints,name='Time/min'),name = col.name)
        predictcol.plot(linestyle = '',marker='.',ax=ax)
        ax.set_title(predictcol.name)
        ax.set_xlim([0,43])
        ax.set_xlabel('Time/min')
        ax.set_ylabel('Prediction')
        ax.set_ylim([-0.2,1.2])
        ax.set_yticks([0,1])
        ax.set_yticklabels(['Neg','Pos'])
        
    plt.tight_layout()
    fig.savefig('Prediction_time_descd1.png',dpi=100)

data =  gather_all_data()
ft(generate_feature_from_col,args=(data.iloc[:,1],),number=100)
col = data.iloc[:,1]





df = pd.read_csv('features.csv',index_col=0)

df.head()

print(df['name'].to_list())

df.head()
X = df.iloc[:,0:-2]
Y = df.iloc[:,-1]


my_clf = DecisionTreeClassifier(max_depth=4)
my_clf.fit(X,Y)
export_graphviz(my_clf,out_file='myclf.dot',feature_names=X.columns,
class_names=['Negative','Positive'],rounded=True,filled=True)


export_tree_graph(my_clf,X.columns,['Negative','Positive'])



my_clf.predict_proba([df.iloc[1,0:-2]])

my_clf.predict([df.iloc[1,0:-2]])



X2 = df.iloc[:,0:-5]
clf2 = DecisionTreeClassifier(max_depth=4,min_samples_leaf=4)
clf2.fit(X2,Y)
export_tree_graph(clf2,X2.columns,['Negative','Positive'],'only Peak features.png')

ax = feature_plot(df,'descd1','peak1_pos',-0.07)
plt.tight_layout()
plt.savefig('descd1 threshold.png')


X2 = df.iloc[:,list(range(5)) + [7,8] ]
clf2 = DecisionTreeClassifier(max_depth=4,min_samples_leaf=4)
clf2.fit(X2,Y)
export_tree_graph(clf2,X2.columns,['Negative','Positive'],'no descd1 features.png')
df['avg_descd'] = df[['descd1','descd2','descd3']].mean(axis=1)
df['max_descd'] = df[['descd1','descd2','descd3']].max(axis=1)
df['min_descd'] = df[['descd1','descd2','descd3']].min(axis=1)
len(df.columns[0:-2])

fig,axes = plt.subplots(6,6,figsize=(22,18))
axes = [i for j in axes for i in j]
for (x,y ),ax in zip(combinations(df.columns[0:-2],2),axes):
    feature_plot(df,x,y,None,ax=ax)
plt.tight_layout()
plt.savefig('feature interaction.svg')
    









fig = feature_plot(df,'peak2_prominence','peak1_pos',None)



fig.savefig('descd2 threshold.png')






df.loc[df['target']==0,'descd1']
import pandas as pd
import seaborn as sns
import scipy.stats as stat
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from itertools import chain, islice
import json
import time

# read DF and set channel
file = r"C:\Users\hui\Work\HuiWork\Covid_Reader\clinical_data_analysis\20220609\clinical_output.csv"
df = pd.read_csv(file)
df.loc[:,'channel'] = [name.split('-')[-1] for name in df.Name]

# used adjust df to filter out only the wanted records
adjusted = r"C:\Users\hui\Work\HuiWork\Covid_Reader\clinical_data_analysis\20220609\20220602clinical_adjusted.csv"
adjdf = pd.read_csv(adjusted, dtype='str').fillna('')
touseIDs = set([i for i in adjdf.ID if i])
rowbool = [i.split('-')[1] in touseIDs for i in df.Name]
df = df[rowbool]



c1df = df[(df.channel == 'C1')]



def getPredictor(ctThreshold, sdThreshold, prThreshold):
    def callresult(data):
        ct, pr, sd = data.hyperCt, data.Pr, data.Sd5m
        if pr < prThreshold:
            return 'Negative'
        else:
            if sd >= sdThreshold and ct < ctThreshold:
                return 'Positive'
            else:
                return 'Negative'
    return callresult

 


# print out a single confusion matrix and 
# precision recall from a given set of thresholds
ctT = 30
sdT = 0.106382
prT = 0.2
predict = c1df.apply(getPredictor(ctT, sdT, prT), axis=1)
labels = ['Positive','Negative']
cfmatrix = confusion_matrix (c1df.Mark, predict, labels=labels)
result = precision_recall_fscore_support(c1df.Mark, predict, labels=labels)
print(f'Ct={ctT}, SD={sdT:.3f}, Pr={prT:.3f}')
for name, i in zip(['Precision','Recall','F1 Score'],result):
    print(f"{name} , {i[0]:.4f} , {i[1]:.4f}")


 


# generate grid data for a range scan of different
# combinations of CT and SD.
ctRange = np.linspace(15, 30, 200)
sdRange = np.linspace(0.06, 0.18, 200)
resultMatrix = np.zeros(shape = (6,len(sdRange), len(ctRange))) 
labels = ['Positive','Negative']

for i, ctT in enumerate(ctRange):
    for j, sdT in enumerate(sdRange):
        predict = c1df.apply(getPredictor(ctT, sdT, prT), axis=1)
        result = precision_recall_fscore_support(c1df.Mark, predict, labels=labels)        
        resultMatrix[:, j, i] = np.array(result).flatten()[0:6]
        
        # print(f'Ct={ctT}, SD={sdT:.3f}, Pr={prT:.3f}')
        # for name, i in zip(['Precision','Recall','F1 Score'],result):
        #     print(f"{name} , {i[0]:.4f} , {i[1]:.4f}")
        # print('')




# save result to json
with open('matrix_output.json','wt') as f:
    json.dump(resultMatrix.tolist(), f)
 

 
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

















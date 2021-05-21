"""
Load data from a labeled picklez file with ViewerDataSource;
Then output the positve and negative data to a Json format.
Data Format:
X:
[
    [[0,0.3,0.6,1...],[12.5,15.6,...]],
    [[0,0.3,0.6,1...],[12.5,15.6,...]],
] ;
X is a nested list, each element consist of 2 list, first is time, second is current.
y: [1,0,1,1,0...] ; 0 is negative, 1 is positive.
"""
from utils._util import ViewerDataSource
import json

dataSource = ViewerDataSource()

folder = "C:/Users/hui/Desktop"
# labelded picke file that contain positve/negative label.
pickleFiles = [

r"C:\Users\hui\Desktop\20210519_JP garage data exported.picklez",

]
dataSource.load_picklefiles(pickleFiles)


X,y = dataSource.exportXy()



print('X data length is : '+str(len(X)))
print('y data length is : '+str(len(y)))
print("Total Positive Data: "+str(sum(y)))
print("Total Negative Data: "+str(len(y)-sum(y)))




# save X data to json
xdata = [ [i[0],i[1]] for i in X]
with open(f'{folder}/Xdata.json','wt') as f:
    json.dump(xdata,f)


# save y data to json

with open(f'{folder}/ydata.json','wt') as f:
    json.dump([int(i) for i in y],f)















    
    
    
    
dataSource

data = dataSource.rawView.get('data')

fits = []

for d in data:
    fit = d['data']['fit']
    for i in fit:
        if i['err']:
            fits.append(fit)
            break
    # fits.append(d['data']['fit'])






import numpy as np

d = X[0][1]

def removeOutlier(an_array):
    an_array = np.array(an_array)
    mean = np.mean(an_array)
    standard_deviation = np.std(an_array)
    distance_from_mean = abs(an_array - mean)
    max_deviations = 3
    not_outlier = distance_from_mean < max_deviations * standard_deviation
    return an_array[not_outlier]

def qc(d):
    delta = np.array(d[0:-1])-np.array(d[1:])
    avg =abs( np.array(d).mean())
    cv = np.std(delta) / (avg + 1e-6)
    return avg,cv
    
    
avgs = []
cvs =[]
for i in X:
    a,c = qc(i[1])
    print(f"Average {a:.2f}, CV {c:.2%}")
    avgs.append(a)
    cvs.append(c)
    
fd = X[1][1]    
qc(fd)
fd

fd[0]=0

len(fd)
fd

len(removeOutlier(fd))

qc(fd)
    
max(avgs)
min(avgs)


max(cvs)
min(cvs)








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


# labelded picke file that contain positve/negative label.
pickleFiles = [r"C:\Users\hui\Desktop\saved.picklez"]
dataSource.load_picklefiles(pickleFiles)


X,y = dataSource.exportXy()

print('X data length is : '+str(len(X)))
print('y data length is : '+str(len(y)))
print("Total Positive Data: "+str(sum(y)))
print("Total Negative Data: "+str(len(y)-sum(y)))


# save X data to json
xdata = [ [i[0],i[1]] for i in X]
with open('Xdata.json','wt') as f:
    json.dump(xdata,f)


# save y data to json

with open('ydata.json','wt') as f:
    json.dump([int(i) for i in y],f)



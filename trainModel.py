from utils._util import ViewerDataSource


import json


dataSource = ViewerDataSource()


# labelded picke file that contain positve/negative label.
pickleFiles = ['/Users/hui/AMS_RnD/Users/Hui Kang/echem Data/ReaderData.picklez']
dataSource.load_picklefiles(pickleFiles)


X,y = dataSource.exportXy()

print('X data length is : '+str(len(X)))
print('y data length is : '+str(len(y)))



# save X data to json
xdata = [ [i[0],i[1]] for i in X]
with open('Xdata.json','wt') as f:
    json.dump(xdata,f)


# save y data to json

with open('ydata.json','wt') as f:
    json.dump([int(i) for i in y],f)



    












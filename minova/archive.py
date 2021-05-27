import joblib
from preprocess import MyTransformer
from compress_pickle import load,dump
from preprocess import smooth,timeseries_to_axis,reject_outliers,extract_timepionts
import numpy as np
res = joblib.load('svm_clf.joblib')


def getDataFromPicklez(data,refit=None):
    """pull the data from picklez file. 
    return the [time,pc] in a list and userMarkedAs.
    if refit is provided, refit the raw data.
    """
    ps = data['pstraces']
    traces=[]
    userMark = []
    for k,value in ps.items():
        print(f'====> {k}')
        for d in value:
            t = timeseries_to_axis(d['data']['time'])
            pc = [i['pc'] for i in d['data']['fit']]
            traces.append((t,pc))
            userMark.append(int(d['userMarkedAs']=='positive'))            
    return traces,userMark

positive = "/Users/hui/Aptitude_Cloud/Aptitude Users/R&D/Users/Hui Kang/echem Data/positiveExport.picklez"
negative = "/Users/hui/Aptitude_Cloud/Aptitude Users/R&D/Users/Hui Kang/echem Data/negativeExport.picklez"

p = load(open(positive,'rb'),compression='gzip')
n = load(open(negative,'rb'),compression='gzip')

t,m = getDataFromPicklez(p)
t[]
res
transformer = MyTransformer()

tA = np.array(t)
tA.shape

first = np.empty((1,2),dtype=list)
first
first[0]=t[0]

first.shape

np.array([t[0]])


transformer.transform(first)



res.predict(first)


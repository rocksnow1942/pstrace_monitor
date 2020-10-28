import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import precision_score, recall_score
from sklearn.svm import LinearSVC
import joblib

def smooth(x,windowlenth=11,window='hanning'):
    "windowlenth need to be an odd number"
    s = np.r_[x[windowlenth-1:0:-1],x,x[-2:-windowlenth-1:-1]]
    w = getattr(np,window)(windowlenth)
    return np.convolve(w/w.sum(),s,mode='valid')[windowlenth//2:-(windowlenth//2)]
    
def timeseries_to_axis(timeseries):
    "convert datetime series to time series in minutes"
    return [(d-timeseries[0]).seconds/60 for d in timeseries]

def traceProcessPipe(
        outlier_para={"stddev":2,},
        smooth_para={"windowlenth":11,"window":'hanning'},
        extractTP_para={"cutoff":60,"n":150}):
    """
    process the [time,pc] data and 
    return the processed value to be used for prediction
    """
    def pipe(row):
        t,pc = row
        t,pc = reject_outliers(t,pc,**outlier_para)
        pc = smooth(pc,**smooth_para)
        row = extract_timepionts(t,pc,**extractTP_para)
        row = normalize(row)
        return row
    return pipe

def normalize(row):
    return row/np.max(row)

def reject_outliers(time,data, stddev=2):
    '''remove the outlier from time series data, 
    stddev is the number of stddev for rejection.
    '''
    sli = abs(data - np.mean(data)) < stddev * np.std(data)
    return np.array(time)[sli], np.array(data)[sli]



def extract_timepionts(time,data,cutoff=60,n=150):
    '''
    extract time and data with time<=cutoff
    n points of data will be returned.
    unknown values are from interpolation. 
    '''
    tp = 0
    datalength = len(data)
    newdata = []
    endslope = np.polyfit(time[-11:],data[-11:],deg=1)
    for i in np.linspace(0,cutoff,n):
        for t in time[tp:]:
            if t>=i:
                break
            tp+=1
        if tp+1>= datalength:
            #if the new timepoint is outside of known range, use last 11 points to fit the curve.
            newdata.append(i*endslope[0]+endslope[1])
        else:
            #otherwise interpolate the data.
            x1 = time[tp]
            y1 = data[tp]
            x2 = time[tp+1]
            y2 = data[tp+1]        
            newdata.append( y1 + (i-x1)*(y2-y1)/(x2-x1) )
    return np.array(newdata)
    
    
    
class MyTransformer(BaseEstimator,TransformerMixin):
    def __init__(self,**params):
        self.params=params        
    def fit(self,X,y=None):
        return self 
    def transform(self,X,y=None):
        "transform my data."
        return np.apply_along_axis(traceProcessPipe(**self.params),1,X,)


transformers = {'MyTransformer': MyTransformer}

algorithm = {'LinearSVC':None}
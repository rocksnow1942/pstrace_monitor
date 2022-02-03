import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
"""
my fit for echem data.
it's ~ 6.6 fold faster than fitpeak2; 180 fold faster than oldmethod.
TODO:
1. test on more messy data.
2. heuristic for finding tangent.
3. ways to measure fitting error by the angle between tangent line and curve slope at contact point.
update 6/29: added myright and myleft in findtangent
update 6/9:
change intercept to account for min(0,) in whole
change peak finding prominence requirements.
"""


def smooth(x, windowlenth=11, window='hanning'):
    "windowlenth need to be an odd number"
    s = np.r_[x[windowlenth-1:0:-1], x, x[-2:-windowlenth-1:-1]]
    w = getattr(np, window)(windowlenth)
    return np.convolve(w/w.sum(), s, mode='valid')[windowlenth//2:-(windowlenth//2)]


def intercept(x, x1, x2, whole=False):
    """
    determine whether the line that cross x1 and x2 and x[x1],x[x2] will intercept x.
    if whole == False, will only consider one side.
    Only consider the direction from x2 -> x1,
    that is:
    if x1 > x2; consider the right side of x2
    if x1 < x2; consider the left side of x2
    """
    # set tolerance to be 1/1e6 of the amplitude
    xtol = - (x.max() - x.min())/1e6
    y1 = x[x1]
    y2 = x[x2]
    k = (y2-y1)/(x2-x1)
    b = -k*x2 + y2
    maxlength = len(x)
    res = x - k*(np.array(range(maxlength)))-b
    if whole:
        return np.any(res[max(0, x1 - maxlength//20 - 5):x2 + maxlength//20 + 5] < xtol)
    if x1 > x2:
        return np.any(res[x2: x1 + maxlength//20 + 5] < xtol)
    else:
        # only consider extra half max width; make sure at least 5 points
        return np.any(res[max(0, x1 - maxlength//20 - 5):x2] < xtol)


def sway(x, center, step, fixpoint):
    if center == 0 or center == len(x):
        return center

    if not intercept(x, center, fixpoint):
        return center
    return sway(x, center+step, step, fixpoint)


def find_tangent(x, center):
    newleft = left = center - 1
    newright = right = center + 1
    while intercept(x, left, right, True):
        if intercept(x, left, right):
            newleft = sway(x, left, -1, right)

        if intercept(x, right, left):
            newright = sway(x, right, 1, newleft)

        if newleft == left and newright == right:
            break
        left = newleft
        right = newright
    return left, right


def pickpeaks(peaks, props, totalpoints):
    "the way to pick a peak"
    if len(peaks) == 1:
        return peaks[0]
    # scores = np.zeros(len(peaks))
    # heights = np.sort(props['peak_heights'])
    # prominences = np.sort(props['prominences'])
    # widths = np.sort(props['widths'])
    normheights = props['peak_heights']/(props['peak_heights']).max()
    normprominences = props['prominences']/(props['prominences']).max()
    normwidths = props['widths']/(props['widths']).max()
    # bases = ((props['left_ips'] == props['left_ips'].min()) &
    #      (props['right_ips'] == props['right_ips'].max()))
    leftbases = props['left_ips'] < totalpoints/10

    scores = normheights + normprominences + normwidths - 2*leftbases  # - 2*bases
    topick = scores.argmax()
    return peaks[topick]
    

def diffNorm(v,a,fx,fy,pc,pv):    
    mask = (v>=fx[0] )&( v<=fx[1])    
    width =(fx[1]-fx[0]) / 2
    height = pc
    delta = sum(fy) / 2
    s = max(width / 3,1e-6)
    c = pv 
    norm = height*np.exp(-0.5*(((v[mask]-c)/s)**2)) + delta    
    diff = a[mask]-norm
    return ((np.abs(diff)) /(max(pc,1e-6)) ).mean()

def myfitpeak(v, a):
    """
    This method has been modified to use dict output, to work with API for upload data.
    """
    x = np.array(v)  # voltage
    y = np.array(a)  # current

    y = smooth(y)
    # limit peak width to 1/50 of the totoal scan length to entire scan.
    # limit minimum peak height to be over 0.2 percentile of all neighbors
    heightlimit = np.quantile(np.absolute(y[0:-1] - y[1:]), 0.8) * 3
    
    # heightlimit = np.absolute(y[0:-1] - y[1:]).mean() * 3
    # set height limit so that props return limits
    peaks, props = signal.find_peaks(
        y, height=heightlimit, prominence=heightlimit, width=len(y) / 30, rel_height=0.5)

    # return if no peaks found.
    if len(peaks) == 0:
        return {'fx': [v[0], v[1]], 'fy': [0, 0], 'pc': 0, 'pv': 0, 'err': 1}

    peak = pickpeaks(peaks, props, len(y))

    # find tagent to 3X peak width window
    x1, x2 = find_tangent(y, peak)

    y1 = y[x1]
    y2 = y[x2]
    k = (y2-y1)/(x2-x1)
    b = -k*x2 + y2

    peakcurrent = y[peak] - (k*peak + b)
    peakvoltage = x[peak]

    twopointx = np.array([x[x1], x[x2]]).tolist()
    twopointy = np.array([y[x1], y[x2]]).tolist()
    
    err = diffNorm(x,y,twopointx,twopointy,peakcurrent,peakvoltage)
    # for compatibility return the same length tuple of results.
    # currently, no error is calculated.
    return {'fx': twopointx, 'fy': twopointy, 'pc': float(peakcurrent), 'pv': float(peakvoltage), 'err': err}



    
    
def plotFit(v,a,f=None,ax=None):
    "simple plot of fittting result."
    if not ax:
        fig,ax = plt.subplots()    
    ax.plot( v,a,'.')
    if f:
        x1, x2 = f['fx']
        y1, y2 = f['fy']
        peakvoltage = f['pv']
        peakcurrent = f['pc']
        k = (y2-y1)/(x2-x1)
        b = -k*x2 + y2
        baselineatpeak = k * f['pv'] + b
        ax.plot(f['fx'], f['fy'], [peakvoltage, peakvoltage], [baselineatpeak, baselineatpeak+peakcurrent])
    plt.show()
    






# Data analysis related functions
 
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from scipy.signal import savgol_filter
from scipy import signal
from scipy.optimize import least_squares

def convert_list_to_X(data):
    """
    data is the format of:
    [[ [t1,t2...],[c1,c2...]],...]
    convert to numpy arry, retain the list of t1,t2... and c1,c2...
    """
    if not data:
        return np.array([])
    X = np.empty((len(data), 2), dtype=list)
    X[:] = data
    return X

def smooth(x, windowlenth=11, window='hanning'):
    "windowlenth need to be an odd number"
    s = np.r_[x[windowlenth-1:0:-1], x, x[-2:-windowlenth-1:-1]]
    w = getattr(np, window)(windowlenth)
    return np.convolve(w/w.sum(), s, mode='valid')[windowlenth//2:-(windowlenth//2)]


def timeseries_to_axis(timeseries):
    "convert datetime series to time series in minutes"
    return [(d-timeseries[0]).seconds/60 for d in timeseries]




def normalize(row):
    return row/np.max(row)


def reject_outliers(time, data, stddev=2):
    '''remove the outlier from time series data, 
    stddev is the number of stddev for rejection.
    '''
    sli = abs(data - np.mean(data)) < stddev * np.std(data)
    return np.array(time)[sli], np.array(data)[sli]


def extract_timepionts(time, data, cutoffStart, cutoffEnd=60, n=150):
    '''
    extract time and data with time<=cutoff
    n points of data will be returned.
    unknown values are from interpolation. 
    '''
    tp = 0
    datalength = len(data)
    newdata = []
    endslope = np.polyfit(time[-11:], data[-11:], deg=1)
    for i in np.linspace(cutoffStart, cutoffEnd, n):
        for t in time[tp:]:
            if t >= i:
                break
            tp += 1
        if tp+1 >= datalength:
            # if the new timepoint is outside of known range, use last 11 points to fit the curve.
            newdata.append(i*endslope[0]+endslope[1])
        else:
            # otherwise interpolate the data.
            x1 = time[tp]
            y1 = data[tp]
            x2 = time[tp+1]
            y2 = data[tp+1]
            newdata.append(y1 + (i-x1)*(y2-y1)/(x2-x1))
    return np.array(newdata)


def findTimeVal(t,val,t0,dt):
    """
    t:   [.............]
    val: [.............]
    t0:       |      ; if t0 is less than 0, then start from 0
    dt:       |---|  ; must > 0
    return:  [.....]
    find the fragment of time series data,
    based on starting time t0 and time length to extract
    assuming t is an evenly spaced time series
    """
    t0idx = int((t0 - t[0]) / (t[-1]-t[0]) * len(val))
    t1idx = int((t0 +dt - t[0]) / (t[-1]-t[0]) * len(val))
    return val[max(0,t0idx):t1idx]


class RemoveTime(BaseEstimator,TransformerMixin):
    """
    Transformer to Truncate and interpolate data, 
    input X is a time and current 2d array. 
    [0,0.3,0.6...] in minutes,
    [10,11,12...] current in uA.
    return a 1d data array, with n data points, start from cutoffStart time, 
    end at cutoffEnd time. Time are all in minutes.
    """
    def __init__(self,):
        pass
    def fit(self,X,y=None):
        return self 
    def transformer(self,X):
        t,pc = X        
        return pc
    def transform(self,X,y=None):        
        return np.array([self.transformer(i) for i in X],dtype='object')




class Smoother(BaseEstimator,TransformerMixin):
   def __init__(self,stddev=2,windowlength=11,window='hanning'):
       self.stddev = stddev
       self.windowlength = windowlength
       self.window = window
   def fit(self,X,y=None):
       return self 
   def transformer(self,X):
       t,pc = X
       t,pc = reject_outliers(t,pc,stddev=self.stddev)
       pc = smooth(pc,windowlenth=self.windowlength,window=self.window)
       return [t,pc]
   def transform(self,X,y=None):        
       # return np.apply_along_axis(self.transformer,1,X,)
       return np.array([self.transformer(i) for i in X],dtype='object')


class Derivitive(BaseEstimator,TransformerMixin):
   def __init__(self,window=31,deg=3,deriv=1):
       self.window = window
       self.deg = deg
       self.deri = deriv
       
       
   def fit(self,X,y=None):
       return self 
   def transformer(self,X):
       t,pc = X
       ss = savgol_filter(pc,window_length=self.window,polyorder=self.deg,deriv=self.deri)        
       return [t,-ss,pc]
   def transform(self,X,y=None):        
       # return np.apply_along_axis(self.transformer,1,X,)
       return np.array([self.transformer(i) for i in X],dtype='object')


class FindPeak(BaseEstimator,TransformerMixin):
   def __init__(self,heightlimit=0.9,widthlimit=0.05):
       self.heightlimit = heightlimit
       self.widthlimit = widthlimit
       
   def fit(self,X,y=None):
       return self 
   def transformer(self,X):
       
       t,gradient,pc = X
       heightlimit = np.quantile(np.absolute(gradient[0:-1] - gradient[1:]), self.heightlimit)
       peaks,props = signal.find_peaks(gradient,prominence=heightlimit,width= len(gradient) * self.widthlimit, rel_height=0.5)
       
       
       peak_pos,left_ips,peak_prominence,peak_width = (t[-1],t[-1],0,0)
       sdAtRightIps,sdAt3min,sdAt5min,sdAt10min,sdAt15min,sdAtEnd = (0,0,0,0,0,0)
       if len(peaks) != 0:            
       # most prominent peak in props 
           tspan = t[-1]-t[0]
           normalizer =  tspan / len(gradient) 
           maxpeak_index = props['prominences'].argmax()
           peak_pos = peaks[maxpeak_index] * normalizer + t[0]
           peak_prominence = props['prominences'][maxpeak_index] 
           peak_width = props['widths'][maxpeak_index] * normalizer 
           left_ips = props['left_ips'][maxpeak_index] * normalizer  + t[0]

           pcMaxIdx = len(pc) - 1

           # siganl at left_ips:
           startPosition = int(props['left_ips'][maxpeak_index])
           sStart = pc[startPosition]
           # find signal drop at different positions:
           # sigal drop at peak_width 
           sdAtRightIps = sStart - pc[min(int(props['right_ips'][maxpeak_index]), pcMaxIdx)]
           # signal drop at 3 min later
           sdAt3min = sStart - pc[min(startPosition + int(3 / normalizer), pcMaxIdx)]
           # signal drop at 5 min later
           sdAt5min = sStart - pc[min(startPosition + int(5 / normalizer), pcMaxIdx)]
           # signal drop at 10 min later
           sdAt10min = sStart - pc[min(startPosition + int(10 / normalizer), pcMaxIdx)]
           # siganl drop at 15 min later
           sdAt15min = sStart - pc[min(startPosition + int(15 / normalizer), pcMaxIdx)]
           # signal drop at end       
           sdAtEnd = sStart - pc[-1]            
       return [left_ips,peak_prominence*100,peak_width,sdAtRightIps,sdAt3min,sdAt5min,sdAt10min,sdAt15min,sdAtEnd,t,gradient,pc]

   def transform(self,X,y=None):        
       # return np.apply_along_axis(self.transformer,1,X,)
       return np.array([self.transformer(i) for i in X],dtype='object')


class HyperCt(BaseEstimator,TransformerMixin):
   "calculate the Ct from threshold method,the threshold line is from a hyperbolic fitting"
   def __init__(self,offset=0.05):
       """        
       offset is how much the fitted curve shifts down. this is in relative scale to the intial fitting point.
       """        
       self.offset = offset
               
   def fit(self,X,y=None):        
       return self    
   
   def hyper(self,p,x,y):
       return p[0]/(x+p[1]) +p[2] -y
   def hyperF(self,p):
       return lambda x:p[0]/(x+p[1]) +p[2]

   def transformer(self,X):        
       offset = self.offset
       t,deri,smoothed_c = X[-3:]
       left_ips,peak_prominence,peak_width = X[0:3]
       tofit = findTimeVal(t,smoothed_c,t[0],left_ips - t[0])
       
       fitres = least_squares(self.hyper,x0=[5,5,0.5],
                   args=(np.linspace(t[0],left_ips,len(tofit)),tofit))
       fitpara = fitres.x
       
       thresholdpara = fitpara - np.array([0,0,(tofit[-1]) * offset])
       thresholdline = self.hyperF(thresholdpara)
       tosearch = findTimeVal(t,smoothed_c,left_ips,t[-1])        
       tosearchT = np.linspace(left_ips,t[-1],len(tosearch))
       thresholdSearch = thresholdline(tosearchT) - tosearch
       thresholdCt = left_ips
       for sT,sthre in zip(tosearchT,thresholdSearch):        
           if sthre > 0:
               break
           thresholdCt = sT
       return  [*X[0:-3],*thresholdpara,thresholdCt]
         
   def transform(self,X,y=None):        
       return np.array([self.transformer(i) for i in X])    
       

class Normalize(BaseEstimator,TransformerMixin):
   """
   Transformer to normalize an array with given parameters
   params: 
   mode: str, can be 'max', 'mean', 
   dataTimeRange: float, describe the total length of data in minutes.
   normalzieToTrange: (), tuple, describe from and to time in minutes it will normalize to.
   
   """
   def __init__(self,mode='max',normalizeRange=(5,20)):
       self.mode=mode
       self.normalizeRange = normalizeRange
       self.q_ = {'max':np.max,'mean':np.mean}.get(self.mode,None)    
       self.from_ = self.normalizeRange [0] 
       self.to_ = self.normalizeRange [1] 
           
   def fit(self,X,y=None):        
       return self
       
   def transformer(self,X):
       
       time,pc = X
       f = np.abs(np.array(time) - self.from_).argmin()
       t = np.abs(np.array(time) - self.to_).argmin()                
       normalizer = max(self.q_(pc[f:t]), 1e-3)
       return time,pc/normalizer
       
   def transform(self,X,y=None):        
       return np.array([self.transformer(i) for i in X],dtype='object')

       
class Truncate(BaseEstimator,TransformerMixin):
   """
   Transformer to Truncate and interpolate data, 
   input X is a time and current 2d array. 
   [0,0.3,0.6...] in minutes,
   [10,11,12...] current in uA.
   return a 1d data array, with n data points, start from cutoffStart time, 
   end at cutoffEnd time. Time are all in minutes.
   """
   def __init__(self,cutoffStart,cutoffEnd,n):
       self.cutoffStart = cutoffStart 
       self.cutoffEnd = cutoffEnd      
       self.n = n
   def fit(self,X,y=None):
       return self 
   def transformer(self,X,y=None):
       t,pc = X
       c = (self.cutoffEnd - self.cutoffStart) / (t[-1] - t[0]) * len(t)
       # i have to do this float conversion, otherwise I got dtype inexact problem in polyfit.
       newcurrent = extract_timepionts(np.array([float(i) for i in t]), 
                                       np.array([float(i) for i in pc]),self.cutoffStart,self.cutoffEnd,self.n)        
       return np.linspace(self.cutoffStart,self.cutoffEnd,int(c)),newcurrent
   def transform(self,X,y=None):
       return np.array([self.transformer(i) for i in X],dtype='object')


class CtPredictor(BaseEstimator,TransformerMixin):
   "a predictor to predict result based on ct and prominence threshold from FindPeak"
   def __init__(self,ct=25,prominence=0.2,sd=0.1):
       self.ct=ct
       self.prominence = prominence
       self.sd=sd
               
   def fit(self,X,y=None):        
       return self    
       
   def transformer(self,x):
       "return 0,1 flag, ct, prominence, signal drop at 5min"
       return int(x[-1]<=self.ct and x[1]>=self.prominence and x[5]>=self.sd),x[-1],x[1],x[5]
       
   def transform(self,X,y=None):        
       return np.apply_along_axis(self.transformer,1,X)



cutoffStart = 5
cutoffEnd = 30
normStart = 5
normEnd = 10
hCtTPredictT = Pipeline([
    ('smooth', Smoother(stddev=2, windowlength=11, window='hanning')),
    ('normalize', Normalize(mode='mean', normalizeRange=(normStart, normEnd))),
    ('truncate', Truncate(cutoffStart=cutoffStart, cutoffEnd=cutoffEnd, n=90)),
    ('Derivitive', Derivitive(window=31, deg=3)),
    ('peak', FindPeak()),
    ('logCt',HyperCt()),
    ('predictor',CtPredictor(ct=22,prominence=0.22,sd=0.05))
])
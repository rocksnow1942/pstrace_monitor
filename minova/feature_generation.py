import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from pprint import PrettyPrinter 
import glob
from scipy.signal import savgol_filter

pprint = PrettyPrinter(indent=2).pprint

def gather_all_data():
    "get all data, convert to 1000 nA data, set time to 0.09min"
    def normalize_to_1K(df):
        if df.mean().mean()<500:
            return df*1000 
        return df
            
    files = glob.glob('data/*.xlsx')
    dfs = [pd.read_excel(file,index_col=0) for file in files]
    shapes = [df.shape[0] for df in dfs]
    maxindex = shapes.index(max(shapes))
    maxdf = dfs.pop(maxindex)
    maxdf = normalize_to_1K(maxdf)
    T = np.arange(0,0.09*(maxdf.shape[0]-1)+1e-9,0.09)
    maxdf = maxdf.set_index(pd.Index(T,name='time'))
    for df in dfs:
        df = df.set_index(maxdf.index[0:df.shape[0]])
        
        df = normalize_to_1K(df)
        colnames = []
        for colname in df.columns:
            while colname in maxdf.columns:
                colname += '+'
            colnames.append(colname)
        df.columns = colnames
        maxdf = pd.concat([maxdf,df],axis=1)
    return maxdf

def fillcolumnna(col,linear_count=50):
    "fill column na with a liner fit of last 50 data point"
    regcol = col.loc[col.map( lambda x: not np.isnan(x))]
    nancol = col.loc[col.map(np.isnan)]
    nancol[nancol.index] = nancol.index
    res = np.polyfit(regcol.index[-linear_count:],np.array(regcol.iloc[-linear_count:]),deg=1)
    newdata = np.array(nancol.index)*res[0] + res[1]
    col[nancol.index]= newdata
    return col

def plot_col_to_grid( df, size=(9,9),ylim=[1000,3500], process_func=None):
    fig,axes = plt.subplots(size[0],size[1],figsize=(2*size[1],2*size[0]))
    axes = [i for j in axes for i in j]
    for ax,col in zip(axes, df.columns):
        col = df[col]
        if process_func:
            for func in process_func:
                col = func(col)
        col.plot(ax=ax,color='k')
        ax.set_title(col.name)
        ax.set_ylim( ylim)
    plt.tight_layout()
    return fig

def smooth_col(col,windowlenth=11,window='hanning'):
    "windowlenth need to be an odd number"
    if isinstance(col,np.ndarray):
        x=col
    x= np.array(col)
    s = np.r_[x[windowlenth-1:0:-1],x,x[-2:-windowlenth-1:-1]]
    w = getattr(np,window)(windowlenth)
    res = np.convolve(w/w.sum(),s,mode='valid')[windowlenth//2:-(windowlenth//2)]
    if isinstance(col,np.ndarray):
        return res
    return pd.Series(res,index=col.index ,name=col.name) 
    
def normalize_col(col,sub_min=False):
   max_ = col.max()
   min_ = col.min() if sub_min else 0.0
   col = col.map(lambda x: (x-min_)/(max_-min_) )
   return col

   
def my_gradient_slow(col,window=31,deg=3,):
   """
   calculate gradient along the column, with polynomial fitting.
   this is similar to a savgol_filter in scipy.signal. (Savitzky–Golay filter)
   window: length of data to fit polynomial function. better to use an odd number. 
   deg: degree of polynomial function.  
   return the smoothed curve and gradient curve. 
   this is much slower than using savgol_filter. 
   0.044s vs 0.0024s
   """
   # non_nan = np.array(col)
   non_nan = np.array(col.loc[col.map(lambda x: not np.isnan(x))])
   time_index =  col.index
   non_nan_length = len(non_nan)
   polyfit_gradients=[]
   polyfit_values=[]
   polyfit_deg = deg
   for i in range(non_nan_length):
       start = max(0,(i-window//2))
       end = window + start
       if end>non_nan_length:
           end = non_nan_length
           start = non_nan_length-window
       # fitwindows.append(non_nan[start:end])
       p = np.polyfit(time_index[start:end],non_nan[start:end],polyfit_deg)
       time_point = time_index[i]
       gradient = (np.array([i* (time_point**(i-1)) for i in range(polyfit_deg,0,-1)]) * (p[0:polyfit_deg])).sum()
       value = (np.array([(time_point**(i)) for i in range(polyfit_deg,-1,-1)]) * p).sum()
       polyfit_gradients.append(gradient)
       polyfit_values.append(value)
   
   gradient_with_nan = np.append(polyfit_gradients, np.full( time_index.shape[0] - len(polyfit_gradients), np.nan ))
   value_with_nan = np.append(polyfit_values, np.full( time_index.shape[0] - len(polyfit_values), np.nan ))
   gradientcol = pd.Series(gradient_with_nan,index=time_index,name=col.name)
   valuecol = pd.Series(value_with_nan,index=time_index,name=col.name)
   return valuecol,gradientcol

   
def my_gradient(col,window=31,deg=3,):
    """
    calculate gradient along the column, with polynomial fitting.
    this is implementation uses savgol_filter in scipy.signal. (Savitzky–Golay filter)
    window: length of data to fit polynomial function. better to use an odd number. 
    deg: degree of polynomial function.  
    return the smoothed curve and 1st gradient curve. 
    0.044s vs 0.0024s
    return smoothed value, 1st derivative, 2nd derivative
    """
    non_nan = np.array(col.loc[col.map(lambda x: not np.isnan(x))])
    time_index = col.index
    ss = savgol_filter(non_nan,window_length=window,polyorder=deg)
    sg = savgol_filter(non_nan,window_length=window,polyorder=deg,deriv=1)
    smthsg = smooth_col(sg,windowlenth=47)
    sg2 = savgol_filter(smthsg,window_length=window,polyorder=deg,deriv=1)
    gra_nan = np.append(smthsg, np.full( time_index.shape[0] - len(smthsg), np.nan )) / (time_index[1]-time_index[0])
    value_with_nan = np.append(ss, np.full( time_index.shape[0] - len(ss), np.nan ))
    sg2_nan = np.append(sg2, np.full( time_index.shape[0] - len(sg2), np.nan ))
    valuecol = pd.Series(value_with_nan,index=time_index,name=col.name)
    gracol = pd.Series(gra_nan,index=time_index,name=col.name)
    sg2_col = pd.Series(sg2_nan,index=time_index,name=col.name)
    return valuecol,gracol,sg2_col



def generate_feature_from_col(col,returndata=False):
    """
    generate feature for column in dataframe.
    current time: 0.0067 second / column. 
    # on raspberry pi 4, averge time for one col is ~ 0.030 s
    """
    # fill na with linear fit, then normalize to 0-1, then smooth it
    fillnacol = fillcolumnna(col,) #linear_count=col.shape[0]//7
    fillnacol = normalize_col(fillnacol,True)
    fillnacol = smooth_col(fillnacol,windowlenth=21)
    timestep = fillnacol.index[1]-fillnacol.index[0]
    # calculate gradient at each point with qudruatic fit
    smoothedcol,smoothed_gradientcol,secondgradientcol = my_gradient(fillnacol, window=31,deg=2)
    # # smooth gradient with a moving window
    # smoothed_gradientcol = smooth_col(gradientcol,windowlenth=47)
    # 
    # #calc 2nd derivitive 
    # secondsmoothcol,secondgradientcol = my_gradient(smoothed_gradientcol,window=31,deg=2) 
    
    # normalize 1st and 2nd gradient to 0-1 and reverse second gradient
    smoothed_gradientcol = normalize_col(smoothed_gradientcol,True)
    secondgradientcol = normalize_col(- secondgradientcol,True)
    
    # find the most prominent peak in 1st derivitive
    gradient = np.array(smoothed_gradientcol) 
    heightlimit = np.quantile(np.absolute(gradient[0:-1] - gradient[1:]), 0.8)
    peaks,props = signal.find_peaks(gradient,prominence=heightlimit,width= len(gradient) / 50, rel_height=0.5)
    
    gradient2 = np.array(secondgradientcol)
    heightlimit2 = np.quantile(np.absolute(gradient2[0:-1] - gradient2[1:]), 0.8)
    peaks2,props2 = signal.find_peaks(gradient2,
        prominence=heightlimit2,width= len(gradient2) / 50, rel_height=0.5)
        
    # if no peaks found:
    if len(peaks) == 0 or len(peaks2) == 0:
        features = {'peak1_pos':0,'peak2_pos':0,'peak1_prominence':0,
        'peak2_prominence':0,'peak1_width':0,'peak2_width':0,
        'descd1':0,'descd2':0,'descd3':0 ,'name':col.name}
        if returndata:
            return (smoothedcol,smoothed_gradientcol,secondgradientcol,),features
        return features
        
    # find 2nd derivitive peaks 
        
    maxpeak_index2 = props2['prominences'].argmax()
    
    # most prominent peak in props 
    maxpeak_index = props['prominences'].argmax()
    peak_pos = smoothed_gradientcol.index[peaks[maxpeak_index]]
    peak_prominence = props['prominences'][maxpeak_index]
    peak_width = props['widths'][maxpeak_index]
    
    # find next peak in 2nd derivitive 
    for k,i in enumerate(peaks2):
        if i >= peaks[maxpeak_index]:
            break
    maxpeak_index2 = k 
    peak2_pos = secondgradientcol.index[peaks2[maxpeak_index2]]
    peak2_prominence = props2['prominences'][maxpeak_index2]
    peak2_width = props2['widths'][maxpeak_index2]
    
    # find singal at different positions 
    peakcurrent = fillnacol.loc[peak2_pos]
    peak2_width_number = int(peak2_width)
    getindex = lambda x:fillnacol.index[ min(x,fillnacol.shape[0]-1)]
    peakcurrent_1 = fillnacol.loc[ getindex(peaks2[maxpeak_index2] + peak2_width_number) ]
    peakcurrent_2 = fillnacol.loc[ getindex(peaks2[maxpeak_index2] + 2*peak2_width_number)]
    peakcurrent_3 = fillnacol.loc[ getindex(peaks2[maxpeak_index2] + 3*peak2_width_number)]
    descd1 = peakcurrent_1 - peakcurrent 
    descd2 = peakcurrent_2 - peakcurrent_1 
    descd3 = peakcurrent_3 - peakcurrent_2 
    
    features = {'peak1_pos':peak_pos,'peak2_pos':peak2_pos,'peak1_prominence':peak_prominence,
    'peak2_prominence':peak2_prominence,'peak1_width':peak_width*timestep,'peak2_width':peak2_width*timestep,
    'descd1':descd1,'descd2':descd2,'descd3':descd3,'name':col.name
    }
    
    if returndata:
        features.update(descd1_pos = getindex(peaks2[maxpeak_index2] + peak2_width_number) )
        features.update(descd2_pos = getindex(peaks2[maxpeak_index2] + 2*peak2_width_number) )
        features.update(descd3_pos = getindex(peaks2[maxpeak_index2] + 3*peak2_width_number))
        return (smoothedcol,smoothed_gradientcol,secondgradientcol),features
    return features

def plot_features_to_ax(ax,data):
    "plot data returned from generate_feature_from_col to ax"
    (scol,sgcol,ssgcol),feature = data 
    if ax==None:
        ax = scol.plot(color='green',ax=ax)
    else:
        scol.plot(color='green',ax=ax)
    sgcol.plot(color='blue',ax=ax,alpha=0.9,linewidth=0.5)
    ssgcol.plot(color='red',ax=ax,alpha=0.9,linewidth=0.5) 
    ax.arrow(feature['peak1_pos'],sgcol.loc[feature['peak1_pos']],0, -feature['peak1_prominence'],color='b')
    ax.arrow(feature['peak2_pos'],ssgcol.loc[feature['peak2_pos']],0,-feature['peak2_prominence'],color='r')
    if feature.get('descd1_pos',None):
        for f in ('descd1_pos','descd2_pos','descd3_pos','peak2_pos'):
            ax.arrow(feature[f], scol.loc[feature[f]],0 , -scol.loc[feature[f]],color='g',linewidth=0.5)    
    ax.set_title(scol.name)

def generate_feature_from_df(df):
    "return features dataframe from data frame."
    features = []
    for c in df.columns:
        features.append(generate_feature_from_col(df[c]))
    return pd.DataFrame(features)


if __name__ == '__main__':
    
    df = gather_all_data()
    d=df.iloc[:,1]

    res = generate_feature_from_col(df.iloc[:,1],returndata=True)


    fig,axes = plt.subplots(9,9,figsize=(18,18))
    axes = [i for j in axes for i in j]
    for col,ax in zip(df.columns,axes):
        col = df[col]
        res = generate_feature_from_col(col,returndata=True)
        plot_features_to_ax(ax,res)
    fig.tight_layout()
        
    fig.savefig('features.svg')

    features = pd.read_csv('features.csv',index_col=0)
    features.head()
























































































































































































import numpy as np
from scipy import signal



def smooth(x, windowlenth=11, window='hanning'):
    "汉宁窗光滑"
    s = np.r_[x[windowlenth-1:0:-1], x, x[-2:-windowlenth-1:-1]]
    w = getattr(np, window)(windowlenth)
    return np.convolve(w/w.sum(), s, mode='valid')[windowlenth//2:-(windowlenth//2)]


def intercept(x, x1, x2, whole=False):
    """
    判断x1 x2两点是否与曲线x相交.
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
    """
    计算切线的位置
    """
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
    """
    从不同的峰中找到该用的峰
    """
    if len(peaks) == 1:
        # 如果只有一个峰, 直接返回
        return peaks[0]
    
    normheights = props['peak_heights']/(props['peak_heights']).max()
    normprominences = props['prominences']/(props['prominences']).max()
    normwidths = props['widths']/(props['widths']).max()
    leftbases = props['left_ips'] < totalpoints/10

    # 找峰的标准是, 峰的高度, 峰的峭度, 峰的宽度, 越大越好,  峰的左边界 靠右边更好    
    # 用这个标准来给每个峰打分.
    scores = normheights + normprominences + normwidths - 2*leftbases  # - 2*bases
    
    # 选择得分最高的峰 返回
    topick = scores.argmax()
    
    return peaks[topick]
    

    
def diffNorm(v,a,fx,fy,pc,pv):   
    """
    计算找到的峰和正态分布的误差值
    """ 
    mask = (v>=fx[0] )&( v<=fx[1])    
    width =(fx[1]-fx[0]) / 2
    height = pc    
    s = max(width / 3,1e-6)
    c = pv 
    norm = height*np.exp(-0.5*(((v[mask]-c)/s)**2))
    dx = max(fx[1]-fx[0], 1e-6)
    line = (fy[1]-fy[0]) /dx * v[mask] - (fy[1]-fy[0]) / dx * fx[0] + fy[0]    
    diff = a[mask]- norm - line
    return ((np.abs(diff)) / (max(pc,1e-6)) ).mean()
 

def fitPeak(v, a):
    """
    我的 pc 获取算法
    """
    x = np.array(v) #电压
    y = np.array(a)    #电流
    sy = smooth(y) # hanning 平滑
    
    noise = np.absolute(y - sy) # 噪声

    # 估算一个高度的阈值, 将来找峰的时候,峰高低于这个阈值就不要了; 这个高度的阈值是3倍95%噪音的高度
    heightlimit = np.quantile(noise, 0.95) * 3
    

    # 找到峰的位置; 用的是scipy的find_peaks函数
    peaks, props = signal.find_peaks(
        sy, height=heightlimit, prominence=heightlimit, width=len(sy) / 30, rel_height=0.5)

    # return if no peaks found.
    if len(peaks) == 0:
        return {'fx': [v[0], v[1]], 'fy': [0, 0], 'pc': 0, 'pv': 0, 'err': 1}

    # 有可能会有几个不同的峰会被找到, 我们用下面的函数来判断应该选择哪个峰
    peak = pickpeaks(peaks, props, len(sy))

    # 从找到的峰的位置, 来计算切线的位置
    x1, x2 = find_tangent(y, peak)

    # 计算切线的直线方程
    y1 = sy[x1]
    y2 = sy[x2]
    k = (y2-y1)/(x2-x1)
    b = -k*x2 + y2

    # 从直线方程计算出峰电流 pc, 峰电压 pv. pc 是从峰的顶点到切线的纵坐标距离.
    peakcurrent = sy[peak] - (k*peak + b)
    peakvoltage = x[peak]

    twopointx = np.array([x[x1], x[x2]]).tolist()
    twopointy = np.array([sy[x1], sy[x2]]).tolist()

    # 计算找到的峰和正态分布的误差值
    err = diffNorm(x,sy,twopointx,twopointy,peakcurrent,peakvoltage)
    
    return {'fx': twopointx, 'fy': twopointy, 'pc': float(peakcurrent), 'pv': float(peakvoltage), 'err': round(err,4)}


def _local_maxima_1d(x):
    """
    从1维数组中找到峰的位置, source : scipy 库
    """
    
    # Preallocate, there can't be more maxima than half the size of `x`
    midpoints = np.empty(x.shape[0] // 2, dtype=np.intp)
    left_edges = np.empty(x.shape[0] // 2, dtype=np.intp)
    right_edges = np.empty(x.shape[0] // 2, dtype=np.intp)
    m = 0  # Pointer to the end of valid area in allocated arrays

    
    i = 1  # Pointer to current sample, first one can't be maxima
    i_max = x.shape[0] - 1  # Last sample can't be maxima
    while i < i_max:
        # Test if previous sample is smaller
        if x[i - 1] < x[i]:
            i_ahead = i + 1  # Index to look ahead of current sample

            # Find next sample that is unequal to x[i]
            while i_ahead < i_max and x[i_ahead] == x[i]:
                i_ahead += 1

            # Maxima is found if next unequal sample is smaller than x[i]
            if x[i_ahead] < x[i]:
                left_edges[m] = i
                right_edges[m] = i_ahead - 1
                midpoints[m] = (left_edges[m] + right_edges[m]) // 2
                m += 1
                # Skip samples that can't be maximum
                i = i_ahead
        i += 1

    # Keep only valid part of array memory.
    midpoints.base.resize(m, refcheck=False)
    left_edges.base.resize(m, refcheck=False)
    right_edges.base.resize(m, refcheck=False)

    return midpoints.base, left_edges.base, right_edges.base



def find_peaks(x, height=None, threshold=None, distance=None,
               prominence=None, width=None, wlen=None, rel_height=0.5,
               plateau_size=None):
    """
    scipy 的find_peaks函数
    """
    # _argmaxima1d expects array of dtype 'float64'
    x = _arg_x_as_expected(x)
    if distance is not None and distance < 1:
        raise ValueError('`distance` must be greater or equal to 1')

    peaks, left_edges, right_edges = _local_maxima_1d(x)
    properties = {}

    if plateau_size is not None:
        # Evaluate plateau size
        plateau_sizes = right_edges - left_edges + 1
        pmin, pmax = _unpack_condition_args(plateau_size, x, peaks)
        keep = _select_by_property(plateau_sizes, pmin, pmax)
        peaks = peaks[keep]
        properties["plateau_sizes"] = plateau_sizes
        properties["left_edges"] = left_edges
        properties["right_edges"] = right_edges
        properties = {key: array[keep] for key, array in properties.items()}

    if height is not None:
        # Evaluate height condition
        peak_heights = x[peaks]
        hmin, hmax = _unpack_condition_args(height, x, peaks)
        keep = _select_by_property(peak_heights, hmin, hmax)
        peaks = peaks[keep]
        properties["peak_heights"] = peak_heights
        properties = {key: array[keep] for key, array in properties.items()}

    if threshold is not None:
        # Evaluate threshold condition
        tmin, tmax = _unpack_condition_args(threshold, x, peaks)
        keep, left_thresholds, right_thresholds = _select_by_peak_threshold(
            x, peaks, tmin, tmax)
        peaks = peaks[keep]
        properties["left_thresholds"] = left_thresholds
        properties["right_thresholds"] = right_thresholds
        properties = {key: array[keep] for key, array in properties.items()}

    if distance is not None:
        # Evaluate distance condition
        keep = _select_by_peak_distance(peaks, x[peaks], distance)
        peaks = peaks[keep]
        properties = {key: array[keep] for key, array in properties.items()}

    if prominence is not None or width is not None:
        # Calculate prominence (required for both conditions)
        wlen = _arg_wlen_as_expected(wlen)
        properties.update(zip(
            ['prominences', 'left_bases', 'right_bases'],
            _peak_prominences(x, peaks, wlen=wlen)
        ))

    if prominence is not None:
        # Evaluate prominence condition
        pmin, pmax = _unpack_condition_args(prominence, x, peaks)
        keep = _select_by_property(properties['prominences'], pmin, pmax)
        peaks = peaks[keep]
        properties = {key: array[keep] for key, array in properties.items()}

    if width is not None:
        # Calculate widths
        properties.update(zip(
            ['widths', 'width_heights', 'left_ips', 'right_ips'],
            _peak_widths(x, peaks, rel_height, properties['prominences'],
                         properties['left_bases'], properties['right_bases'])
        ))
        # Evaluate width condition
        wmin, wmax = _unpack_condition_args(width, x, peaks)
        keep = _select_by_property(properties['widths'], wmin, wmax)
        peaks = peaks[keep]
        properties = {key: array[keep] for key, array in properties.items()}

    return peaks, properties    

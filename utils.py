import numpy as np
import os
from matplotlib.figure import Figure

def timeseries_to_axis(timeseries):
    "convert datetime series to time series in minutes"
    return [(d-timeseries[0]).seconds/60 for d in timeseries]


def plot_experiment(dataset, interval, savepath):
    """
    plot data into grid axes,
    dataset should be the format of mongodb datapack.
    {
        name:,
        desc:,
        exp:,
        dtype: 'covid=trace',
        data:{
            time: [datetime(),...]
            rawdata: [[v,a]...]
            fit:[ {'fx': , 'fy': , 'pc': , 'pv': , 'err': 0}...]
        }
    }
    interval: the interval for timepoints to be plotted.
    savepath: folder to save the file.
    """
    name = dataset['name']
    times = timeseries_to_axis(dataset['data']['time'][::interval])
    raw = dataset['data']['rawdata'][::interval]
    fit = dataset['data']['fit'][::interval]

    cols = int(np.ceil(np.sqrt(len(times))))
    rows = int(np.ceil(len(times) / cols))

    fig = Figure(figsize=(1.5*cols, 1.5*rows))
    axes = fig.subplots(rows, cols)
    axes = np.ravel([axes])

    for ax in axes:
        ax.axis('off')

    for t, r, f, ax in zip(times, raw, fit, axes):
        x1, x2 = f['fx']
        y1, y2 = f['fy']
        peakvoltage = f['pv']
        peakcurrent = f['pc']
        k = (y2-y1)/(x2-x1)
        b = -k*x2 + y2
        baselineatpeak = k * f['pv'] + b
        v, a = r
        color = 'r' if f['err'] else 'b'
        ax.plot(v, a,  f['fx'], f['fy'],
                [peakvoltage, peakvoltage], [baselineatpeak, baselineatpeak+peakcurrent])
        ax.set_title("{:.1f}m {:.2f}nA".format(t, peakcurrent),
                     fontsize=10, color=color)
        ax.axis('on')

    fig.set_tight_layout(True) 
    
    fig.savefig(savepath)

"""
This script try to find a good threshold for calling a fitting good or bad for the peak.

The idea is, use the current peak finding algorithm,
then compare the real curve to a normal distribution curve, find the percent error
error = delta(curve -normal distribution)/ Peak current.

Finding:
normally, this error is around 5%. extream cases where the peak is not centered, the error can go 
to 12%.
Decided to set the threshold at 15% for final prediction QC, where 
all the fitting errors for the 30' measurement is averaged.
For the QC before test started, use 20%. if the first tested fitting error is over 20%, signal an error.
"""
import zlib
import glob
from compress_pickle import load,load,get_default_compression_mapping
import matplotlib.pyplot as plt
from utils.myfit import *
import numpy as np
from utils.calling_algorithm import *

def norm(f):
    width =(f['fx'][1]-f['fx'][0]) / 2
    height = f['pc']
    delta = sum(f['fy']) / 2
    s = max(width / 3,1e-6)
    c = f['pv']    
    def nF(x):
        x = np.array(x)
        return height*np.exp(-0.5*(((x-c)/s)**2)) + delta
    return nF

def diffNorm(v,a,f):
    v = np.array(v)
    a = np.array(a)
    mask = (v>=f['fx'][0] )&( v<=f['fx'][1])
    diff = a[mask]-norm(f)(v[mask])
    return ((np.abs(diff)) /(max(f['pc'],1e-6)) ).mean()

file = r"C:\Users\hui\Work\HuiWork\Covid_Reader\CapCAT\20210701\DMVdecoded.picklez"

files = get_picklez(r'C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export')


d = load(file,compression='gzip',set_default_extension =False)

d2 = load(r"C:\Users\hui\RnD\Projects\LAMP-Covid Sensor\Data Export\20210629\20210629 MC NTC vs PTC.picklez",compression='gzip',set_default_extension=False)


files[-10]
d = load(files[-10],compression='gzip',set_default_extension =False)

data = d2['pstraces']


data = d['pstraces']

total = 0
for d in data:
    total += len(data[d])


for i in range(24):
    idx = i
    t = 2
    c = data[idx]['data']
    v,a = c['rawdata'][t]
    f = myfitpeak(v,a)
    # 
    # ax = plotFit(v,a,f)
    # ax.plot(v,norm(f)(v))
    # ax.set_title(f['err'])

data.keys()




fitres = []
for d in data:
    print(d)
    for t in data[d]:        
        c = t['data']
        cf = []
        for p in c['rawdata']:
            v,a = p
            f = myfitpeak(v,a)                
            cf.append(f)
        avgerr = sum([i['err'] for i in cf]) / len(cf)
        fitres.append((t['name'],avgerr)) 


sorted(fitres,key=lambda x:x[1],reverse=1)[0:5]


len(fitres)



"Maximum diffNorm Error on average from normal peaks"
r'C:\\Users\\hui\\RnD\\Projects\\LAMP-Covid Sensor\\Data Export\\20210601_0602.picklez'
('20210602_175um_NB-DTT_U-PS_C1EvicC4Biolyph_NTC_(E2-1) -C4', 0.12401327471824351),


r'C:\\Users\\hui\\RnD\\Projects\\LAMP-Covid Sensor\\Data Export\\20210603\\20210603 NTC vs 100cp.picklez'
('20210603 175um Acry: 6/3 NB 5/28 Chips ET 100cp(MC1-3)-C4', 0.05797503702364579)

r"C:\Users\hui\Work\HuiWork\Covid_Reader\CapCAT\20210701\DMVdecoded.picklez"
('Test On 20210630-15:54-C1 Negative11:56', 0.05587269475497658),
('Test On 20210630-16:40-C1 Invalid12:40', 0.18191981846181038),
 
            
r'C:\\Users\\hui\\RnD\\Projects\\LAMP-Covid Sensor\\Data Export\\20210604\\20210604 NTC vs PTC.picklez'
('20210604 175um Acry: 6/3 NB 6/3 Chip 300CP-1 (MC1-23)-C4',0.06594709364099867),

r'C:\\Users\\hui\\RnD\\Projects\\LAMP-Covid Sensor\\Data Export\\20210625\\20210625 NTC vs PTC.picklez'
('20210625 8A 50um FunFil: Evik N7 DSM 300cp-1 (MC2-5)-C4',0.058901330438176115)

r'C:\\Users\\hui\\RnD\\Projects\\LAMP-Covid Sensor\\Data Export\\20210701\\20210701 MC NTC vs PTC.picklez'
('20210625 8A 50um FunFil: Evik N7 DSM 300cp-1 (MC2-5)-C4',0.058901330438176115)

r'C:\\Users\\hui\\RnD\\Projects\\LAMP-Covid Sensor\\Data Export\\20210623\\20210623 MC NTC vs PTC.picklez' 
66
('20210625 8A 50um FunFil: Evik N7 DSM 300cp-1 (MC2-5)-C4',0.058901330438176115)
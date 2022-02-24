
import json

raw = r"C:\Users\hui\Desktop\TWXY_Raw2.txt"


data = open(raw,'rt',encoding='utf-8').read().split('\n')

raw = {0:[],3:[]}

ch = 0
for d in data:
    if len(d) > 120:
        i0=d.index('{')
        i1=d.index('}')
        j = json.loads(d[i0:i1+1])
        raw[ch].append([[-0.5,0.1],j['c']])
        ch = 0 if ch else 3
        

for ch in [0,3]:
    with open(f'twx2{ch}.json','wt') as f:
        json.dump(raw[ch],f)




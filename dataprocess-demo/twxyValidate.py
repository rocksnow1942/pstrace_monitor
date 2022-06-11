import json


# files = """/Users/hui/Desktop/20220302-TWXY-PCBA-data/20220302-CH0=negative, CH3=postive-Raw1.txt
# /Users/hui/Desktop/20220302-TWXY-PCBA-data/20220302-CH0=negative, CH3=postive-Raw2.txt
# /Users/hui/Desktop/20220302-TWXY-PCBA-data/20220302-CH0=negative, CH3=postive-Raw3.txt
# /Users/hui/Desktop/20220302-TWXY-PCBA-data/20220302-CH0=negative, CH3=postive-Raw4.txt
# /Users/hui/Desktop/20220302-TWXY-PCBA-data/20220302-CH0CH3-both-postive-Raw1.txt
# /Users/hui/Desktop/20220302-TWXY-PCBA-data/20220302-CH0CH3-both-postive-Raw2.txt""".split('\n')

files = [r"C:\Users\hui\Downloads\TWXY_Raw1.txt"]

for f in files:
    data = open(f,'rt',encoding='utf-8').read().split('\n')

    raw = {0:[],3:[]}

    ch = 0
    for i,d in enumerate(data):
        if '{' in d:                    
            i0=d.index('{')
            if '}' in d:
                i1=d.index('}')
                jd = d[i0:i1+1]
            else:
                i1=data[i+1].index('}')
                jd = d[i0:] + data[i+1][i0:i1+1]                
            j = json.loads(jd)            
            jc = j.get('c',[])
            if (len(jc))> 50:
                raw[ch].append([[-0.5,0.1],j['c']])
                ch = 0 if ch else 3
            

    for ch in [0,3]:
        with open(f'test_ch{ch}.json','wt') as fobj:
            json.dump(raw[ch],fobj)




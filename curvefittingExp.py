"read the log and raw data downloaded from covid reader"
import zlib
import glob
from compress_pickle import load,loads,get_default_compression_mapping
file = r"C:\Users\hui\Work\HuiWork\Covid_Reader\CapCAT\20210701\DMVdecoded.picklez"

with open(file,'rb') as f:
    data = f.read()


d = loads(data,compression='gzip')

d = load(file,compression='gzip',set_default_extension =False)

files = glob.glob(r"C:\Users\hui\Desktop\tmp\*.gz")
print(files)


# file = r"C:\Users\hui\Desktop\logs.gz"

def decodeReaderData(file):
    with open(file,'rb') as f:
        data = f.read()
        
        
    log = zlib.decompress(data)

    out = file.split('.')[0]+'decoded'+'.gz'

    with open(out,'wb') as f:
        f.write(log)

for file in files:
    decodeReaderData(file)



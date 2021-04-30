"read the log and raw data downloaded from covid reader"
import zlib

file = r"C:\Users\hui\Desktop\logs.gz"


with open(file,'rb') as f:
    data = f.read()
    
    
log = zlib.decompress(data)

out = r'C:\Users\hui\Desktop\logs.txt'

with open(out,'wt') as f:
    f.write(log.decode())
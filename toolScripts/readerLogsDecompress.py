"""
Decompress the logs file downloaded from the reader page.
"""
import zlib

file = r"C:\Users\hui\Downloads\logs.gz"

with open(file,'rb') as f:
    data  = zlib.decompress(f.read())

with open(file+'.decon.txt','wt') as f:
    f.write(data.decode('utf-8'))


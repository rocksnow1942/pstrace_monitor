"read the log and raw data downloaded from covid reader"
import zlib
import glob
# file = r"C:\Users\hui\Desktop\logs.gz"


# with open(file,'rb') as f:
#     data = f.read()
    
    
# log = zlib.decompress(data)

# out = r'C:\Users\hui\Desktop\logs.txt'

# with open(out,'wt') as f:
#     f.write(log.decode())


# files = [r"C:\Users\hui\Desktop\raw\DMV.gz",
# r"C:\Users\hui\Desktop\raw\IYX.gz",
# r"C:\Users\hui\Desktop\raw\JAR.gz",
# r"C:\Users\hui\Desktop\raw\KIN.gz",
# r"C:\Users\hui\Desktop\raw\PSA.gz",
# r"C:\Users\hui\Desktop\raw\QJA.gz",
# ]

files = glob.glob(r"C:\Users\hui\Desktop\data\*.gz")
print(files)


# file = r"C:\Users\hui\Desktop\logs.gz"

def decodeReaderData(file):
    with open(file,'rb') as f:
        data = f.read()
        
        
    log = zlib.decompress(data)

    out = file.split('.')[0]+'.gz'

    with open(out,'wb') as f:
        f.write(log)

for file in files:
    decodeReaderData(file)
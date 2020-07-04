import serial
import serial.tools.list_ports
import datetime
import numpy as np

#dictionary list for conversion of the SI prefixes
sip_factor = {
'a' : 1e-18 ,
'f' : 1e-15 ,
'p' : 1e-12 ,
'n' : 1e-09 ,
'u' : 1e-06 ,
'm' : 0.001 ,
' ' : 1.0 ,
'i' : 1.0 ,
'k' : 1000.0 ,
'M' : 1000000.0 ,
'G' : 1000000000.0 ,
'T' : 1000000000000.0 ,
'P' : 1000000000000000.0 ,
'E' : 1e+18 ,
}

for i in sip_factor:
    print(repr(i['si']),':',i['factor'],',')


#dictionary containing all used var types for MethodSCRIPT
ms_var_types = [  {"vt":"aa", "type": "unknown"             , "unit" : " " },
                  {"vt":"ab", "type": "WE vs RE potential"  , "unit" : "V" },
                  {"vt":"ac", "type": "CE potential"        , "unit" : "V" },
                  #{"vt":"ad", "type": "WE potential"        , "unit" : "V" },
                  {"vt":"ae", "type": "RE potential"        , "unit" : "V" },
                  {"vt":"ag", "type": "WE vs CE potential"  , "unit" : "V" },

                  {"vt":"as", "type": "AIN0 potential"      , "unit" : "V" },
                  {"vt":"at", "type": "AIN1 potential"      , "unit" : "V" },
                  {"vt":"au", "type": "AIN2 potential"      , "unit" : "V" },

                  {"vt":"ba", "type": "WE current"          , "unit" : "A"},

                  {"vt":"ca", "type": "Phase"               , "unit" : "Degrees"},
                  {"vt":"cb", "type": "Impedance"           , "unit" : "Ohm"},
                  {"vt":"cc", "type": "ZReal"               , "unit" : "Ohm"},
                  {"vt":"cd", "type": "ZImag"               , "unit" : "Ohm"},

                  {"vt":"da", "type": "Applied potential"   , "unit" : "V"},
                  {"vt":"db", "type": "Applied current"     , "unit" : "A"},
                  {"vt":"dc", "type": "Applied frequency"   , "unit" : "Hz"},
                  {"vt":"dd", "type": "Applied AC amplitude", "unit" : "Vrms"},

                  {"vt":"eb", "type": "Time"                , "unit" : "s"},
                  {"vt":"ec", "type": "Pin mask"            , "unit" : " "},

                  {"vt":"ja", "type": "Misc. generic 1"     , "unit" : " " },
                  {"vt":"jb", "type": "Misc. generic 2"     , "unit" : " " },
                  {"vt":"jc", "type": "Misc. generic 3"     , "unit" : " " },
                  {"vt":"jd", "type": "Misc. generic 4"     , "unit" : " " }]


def Flush(ser):
    prev_timeout = ser.timeout                          #Get the current timeout to restore it later
    ser.timeout = 4                                     #Set the timeout to 2 seconds
    ser.write(bytes("\n",  'ascii'))                   	#write a linefeed to flush
    _ =  ser.read_until(bytes("\n", 'ascii'))   	#read until \n to catch the response
    ser.timeout = prev_timeout                          #restore timeout


def GetResults(ser):
    "return results as a list of lines"
    results = []
    while 1:
        res = ser.readline()
        strline = res.decode('ascii')
        results.append(strline)
        if strline == '\n' or '!' in strline:
            break 
    return results 


def ValConverter(value,sip):
    return sip_factor.get(sip,np.nan) * value
    
def ParseVarString(varstr):
    SIP = varstr[7]                 #get SI Prefix
    varstr = varstr[:7]             #strip SI prefix from value
    val = int(varstr,16)            #convert the hexdecimal number to an integer
    val = val - 2**27               #substract the offset binary part to make it a signed value
    return ValConverter(val,SIP)    #return the converted floating point value


def ParseResultsFromLine(res_line):
    lval= list()                            #Create a list for values
    lvt= list()                             #Create a list for values
    if res_line.startswith('P'):            #data point start with P
        pck = res_line[1:len(res_line)]     #ignore last and first character
        for v in pck.split(';'):            #value fields are seperated by a semicolon
            str_vt = v[0:2]                 #get the value-type
            str_var = v[2:2+8]              #strip out value type
            val = ParseVarString(str_var)   #Parse the value
            lval.append(val)                #append value to the list
            lvt.append(str_vt)
    return lval,lvt   

def GetValueMatrix(content):
    val_array=[[]]
    j=0
    for resultLine in content:
        #check for possible end-of-curve characters
        if resultLine.startswith('*') or resultLine.startswith('+') or resultLine.startswith('-'):
            j = len(val_array) #step to next section of values
             
        else:
            #parse line into value array and value type array
            vals,_ = ParseResultsFromLine(resultLine)
            #Ignore lines that hold no actual data package
            if len(vals) > 0:
                #If we're here we've found data for this curve, so check that space in allocated for this curve
                #This way we don't allocate space for empty curves (for example when a loop has no data packages)
                if j >= len(val_array):
                    val_array.append([])
                #Add values to value array
                val_array[j].append(vals)
    return val_array


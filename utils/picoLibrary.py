import serial
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

def openSerialPort(comport):
    ser = serial.Serial() 
    ser.port = comport                                  #set the port
    ser.baudrate = 230400                               #Baudrate is 230400 for EmstatPico
    ser.bytesize = serial.EIGHTBITS                     #number of bits per bytes
    ser.parity = serial.PARITY_NONE                     #set parity check: no parity
    ser.stopbits = serial.STOPBITS_ONE                  #number of stop bits
    #ser.timeout = None                                 #block read
    ser.timeout = 1                                     #timeout block read
    ser.xonxoff = False                                 #disable software flow control
    ser.rtscts = False                                  #disable hardware (RTS/CTS) flow control
    ser.dsrdtr = False                                  #disable hardware (DSR/DTR) flow control
    ser.write_timeout = 2                                #timeout for write is 2 seconds
    ser.open()                                      #open the port
    return ser 

def channel_to_pin(channel):
    "convert channel to pin in the multiplexer. channel is C1-C16"
    pins = [128,64,32,16] # pin7 , 6, 5, 4
    pinNum = sum(int(i)*j for i,j in zip(f"{int(channel[1:])-1:04b}",pins))
    return f"set_gpio_cfg 240 1\nset_gpio {pinNum}i"
    

def constructScript(settings):
    """
    use channel info to set pins. 
    construct method script from settings
    covid-trace method format: {
        'script': method script to send. 
        'interval': interval 
        'repeats' : repeat how many times 
        'duration' : total last measurement time. # whichever happens first. 
    }
    """
    channel = settings['channel']
    dtype = settings['dtype']
    
    if dtype =='covid-trace':
        setPin = channel_to_pin(channel)
        E_begin = convert_voltage(settings['E Begin'])
        E_end = convert_voltage(settings['E End'])
        assert (settings['E Step']>=0.001 and settings['E Step']<=0.1) ,'E step out of range'
        E_step = convert_voltage(settings['E Step'])
        assert (settings['E Amp']>0.001 and settings['E Amp']<=0.25 ), 'E Amp out of range.'
        E_amp = convert_voltage(settings['E Amp']) 
        Freq = int(settings['Frequency'])
        assert (Freq<999 and Freq>5) , "Frequency out of range."
        crMin = convert_currange_range(settings['CurrentRange Min'])
        crMax = convert_currange_range(settings['CurrentRange Max'])
        repeats = settings['Total Scans']
        interval = settings['Interval'] 
        assert (interval > 4) , 'Interval too small for pico.'
        duration = settings['Duration(s)']
        script = eval('f'+repr(covid_trace_template))
        return {'interval':interval,'repeats':repeats,
            'script':script , 'duration':duration   }


    return "None"

def convert_voltage(v):
    assert (v>=-1.61 and v<=1.81) , 'Potential out of range'
    return f"{v*1000:.0f}m"

def convert_currange_range(r):
    "'100 nA','1 uA','10 uA','100 uA','1 mA','5 mA'"
    n,u = r.split(' ')
    return n+u[0]


covid_trace_template="""e
var c
var p
var f
var r
{setPin}
set_pgstat_chan 0
set_pgstat_mode 3
set_max_bandwidth {Freq*4}
set_pot_range {E_begin} {E_end}
set_autoranging {crMin} {crMax}
cell_on
set_e {E_begin}
meas_loop_swv p c f r {E_begin} {E_end} {E_step} {E_amp} {Freq}
	pck_start
	pck_add p
	pck_add c
	pck_end
endloop
on_finished:
cell_off

"""

template="""e
var c
var p
var f
var r
set_pgstat_chan 0
set_pgstat_mode 3
set_max_bandwidth 400
set_pot_range -300m 400m
set_cr 59n
set_autoranging 59n 590u
cell_on
set_e -600m
meas_loop_swv p c f r -600m 100m 2m 50m 100
	pck_start
	pck_add p
	pck_add c
	pck_end
endloop
on_finished:
cell_off

"""


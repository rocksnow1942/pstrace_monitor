import serial
import time

with serial.Serial('/dev/cu.SLAB_USBtoUART6', 115200, timeout=3) as slave:
    for i in range(10):
        time.sleep(2)
        slave.write('Hello\n'.encode())
        res = slave.read_all()
        print(res.decode())

    slave.write('\x03\r\n'.encode())

serial.PARITY_NONE

slave = serial.Serial('/dev/cu.SLAB_USBtoUART4', 115200, timeout=3,bytesize=8,parity='N',stopbits=1)




len('123456789012345678901234567890123456789012345678901234567890\n')

writestring = 'repl'*1 + '\n'

slave.write('help()\n'.encode())

slave.write(writestring.encode())

slave.write('\x00\r\n'.encode())

print((slave.read_all().decode()))

slave.write('import main\n'.encode())


slave.write('help()\n'.encode())



slave.close()







slave = serial.Serial('/dev/cu.SLAB_USBtoUART', 115200, timeout=3)





len(bytearray('wow i am your loss?\n'.encode()))

b = 'abc'.encode()

len(b)



slave.write('wow i am your loss?\n'.encode())
slave.write('\x00\r\n'.encode())

print(slave.read_all().decode())




slave.close()








# USB read for pico
import serial
import time


#Opens a serial COM port
def OpenComport(ser,comport,timeout):
    ser.port = comport                                  #set the port
    ser.baudrate = 230400                               #Baudrate is 230400 for EmstatPico
    ser.bytesize = serial.EIGHTBITS                     #number of bits per bytes
    ser.parity = serial.PARITY_NONE                     #set parity check: no parity
    ser.stopbits = serial.STOPBITS_ONE                  #number of stop bits
    #ser.timeout = None                                 #block read
    ser.timeout = timeout                               #timeout block read
    ser.xonxoff = False                                 #disable software flow control
    ser.rtscts = False                                  #disable hardware (RTS/CTS) flow control
    ser.dsrdtr = False                                  #disable hardware (DSR/DTR) flow control
    ser.writeTimeout = 2                                #timeout for write is 2 seconds
    try:
        ser.open()                                      #open the port
    except serial.SerialException as e:                 #catch exception
        print("error open serial port: " + str(e))      #print the exception
        return False
    return True


ser = serial.Serial()


# port on mbp 
port = "/dev/tty.usbserial-FT4JDMYV"

OpenComport(ser,port,1)


OpenComport(ser,'/dev/cu.usbserial-FT4JDMYV',1)

ser.write('e\nsend_string "hello world"\n\n'.encode())

ser.read_all().decode()

ser.read_until(bytes("*\n",  'ascii'))

ser.close()
"t\n"


def test(n):
    i=n
    while True:
        i+=1
        yield i
        if i>10:
            break


a = test(1)

for i in a:
    print(i)




script = """e
var c
var p
set_pgstat_mode 3
set_max_bandwidth 1k
set_cr 10625n
set_autoranging 85n 850u
set_e 0m
cell_on
wait 1
#Eres,Ires,Ebegin,Evtx1,Evtx2,Estep,Scanrate
meas_loop_cv p c 0m 500m -500m 5m 500m
	pck_start
	pck_add p
	pck_add c
	pck_end
endloop
on_finished:
cell_off


"""


ser.write(script.encode())
ser.read_all().decode()


scriptfile = '/Users/hui/Documents/Scripts/micropython/MethodSCRIPTExamples/MethodSCRIPTExample_Python/MethodSCRIPTExample_Python/MethodSCRIPT files/MSExampleCV.mscr'
swvscript = '/Users/hui/Documents/Scripts/micropython/MethodSCRIPTExamples/MethodSCRIPTExample_Python/MethodSCRIPTExample_Python/MethodSCRIPT files/MSExampleAdvancedSWV.mscr'

with open(swvscript) as f:
    content = f.readlines()
print( repr("".join(i for i in content)).strip('\'') )




import PSEsPicoLib as p
import serial
swvscript = '/Users/hui/Documents/Scripts/micropython/MethodSCRIPTExamples/MethodSCRIPTExample_Python/MethodSCRIPTExample_Python/MethodSCRIPT files/MSExampleAdvancedSWV.mscr'

ser = serial.Serial()
p.OpenComport(ser,'/dev/cu.usbserial-FT4JDMYV',1)

ser.write('e\nsend_string "hello world"\n\n'.encode())

ser.read_all().decode()





p.SendScriptFile(ser,swvscript)
#Get the results and store it in datafile
datafile=p.GetResults(ser)

'''
Example:  Use ARK bridge to stream data from Chipsea EVB
'''
import matplotlib.pyplot as plt
import time
import serial
import arduino_io as ark

#Scan for ARK bridge that act as virtual serial port
ser = serial.Serial()
a=serial.tools.list_ports.comports()
for w in a:
    ser.baudrate=115200
    ser.port=w.device
    ser.open()
    i = 10
    while ser.isOpen() == False:
        i -= 1
        if i == 0:
            print "Cannot open serial port in 10 tries."
            exit()

time.sleep(4)

ark.i2c_address(0x26)

data=[]
temp=[]
   
#Fill the first 100 samples
for i in range(100):
    status, num_read = ark.read(ser, 0x9d, 3, temp)
    #if num_read != 3:
        #print len(temp)
        #print i
    t = 0
    #Temporary solution for serial port read glitches
    for z in range(len(temp)):
        t += temp[z] << (8 * (2-z))
    data.append(t)

x = range(100)

while 1:
    try:
        plt.clf()
        plt.plot(x, data)
        plt.pause(0.01)
        
        for i in range(99):
            data[i] = data[i+1]
        status, num_read = ark.read(ser, 0x9d, 3, temp)
        t = 0
        for z in range(len(temp)):
            t += temp[z] << (8 * (2-z))
        data[99] = t             
        
    except KeyboardInterrupt:
        ser.close()
        break    
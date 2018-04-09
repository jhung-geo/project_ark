'''
Example:  Use ARK bridge to stream data
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


data=[]
temp=[]
   
if (ser.isOpen()):
       
    ark.i2c_address(ser, 0x40)
    
    '''Enable the AFE and display raw value '''
    status, num_read = ark.read(ser, 0x00, 1, temp)
    temp[0] |= 0x09
    time.sleep(0.1)
    status, num_read = ark.write(ser, 0x00, temp)
    
   
    '''Fill the first 100 samples'''
    for i in range(100):
        status, num_read = ark.read(ser, 0x03, 2, temp)
        t = ((temp[0] << 8) + (temp[1] & 0xf0))>>4
        data.append(t)
    
    x = range(100)
    
    while 1:
        try:
            plt.clf()
            plt.plot(x, data)
            plt.pause(0.001)
            
            for i in range(99):
                data[i] = data[i+1]
            status, num_read = ark.read(ser, 0x03, 2, temp)
            t = ((temp[0] << 8) + (temp[1] & 0xf0))>>4
            data[99] = t             
            
        except KeyboardInterrupt:
            ser.close()
            break    
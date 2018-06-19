import sys
import math
import matplotlib.pyplot as plt
import arduino_io as acom
import time
import serial
import progressbar

ser = acom.enum()[0]

#time.sleep(4)

temp =[]
data =[]    
ver = []
pos = 32
# setting up the communication
#acom.i2c_address(ser,0x26)
file_name = sys.argv[1]
fp = open(file_name, "rU")
fp.seek(0,2)
size = fp.tell()
reg = 0x00


if True:#(ser.isOpen()):
    device = ser
    
    temp = []
    
    status, num_read = acom.read(device, 0x00, 1, temp)
    
    count = 0
    while (count < 3):
        #ERASE FLASH
        data = [0x55,0xa5,0x55]
        status, num_written = acom.write(device, 0xa1, data)
        time.sleep(0.160)
        count = count + 1
        for x in range(0, 10):
            status, num_read = acom.read(device, 0x00, 1, temp)
            time.sleep(0.015)
            if temp[0] == 17 or temp[0] == 18:
                count = 10     
                break
        
    if count == 3:
        print('Error:Cannot reset EVB!')
        fp.close()    
        sys.exit(0)
    
    #WRITE FLASH
    time.sleep(0.1)
    data = [0x55,0xa5,0x5a]
    status, num_written = acom.write(device, 0xa1, data)    
    time.sleep(0.005)
    
    write_bar = progressbar.ProgressBar(max_value=size)
    
    print "Writing Flash" + "\n"
    
    while pos < size:
        del data[:]        
        for x in range(0, 32):
            fp.seek(pos)     
            byte = ord(fp.read(1))
            #print byte
            data.append(byte)
            ver.append(byte)
            pos += 1
            
        status, num_written = acom.write(device, reg, data)
        
        if status != 0:
            print ('Write error ')
            print status
            print pos
            sys.exit(0)
        reg += 1
        reg %= 256
        time.sleep(0.01)
        #print ("write block %d ", pos)
        write_bar.update(pos)
        
    fp.close()
    
    print "\n" + "\n" + "Readback and Verify" + "\n"
    
    #READBACK AND VERIFY
    pos = 0
    reg = 0    
    time.sleep(0.100)   
    data = [0x55,0xa5,0xa5]
    status, num_written = acom.write(device, 0xa1, data)
    
    read_bar = progressbar.ProgressBar(max_value=size)
    
    while pos+32 < size:    
        del data[:]        
        status, num_read = acom.read(device, reg, 32, data)
        if status != 0:
            print ('I2C error @ READBACK')
            print status
            print pos
            sys.exit(0)
        #print num_read
        #print pos
        #time.sleep(0.01)
        for x in range(0, 32):
            #print x
            #print pos
            #print len(data)
            #print len(ver)
            if data[x] != ver[pos]:
                print ('Verify error @ byte %d'% pos)
                sys.exit(0)
            pos += 1
        reg += 1
        reg %= 256
        #time.sleep(0.01)
        read_bar.update(pos)
    
    #SIGN AND CLOSE
    time.sleep(0.052)   
    data = [0x55,0xa5,0x51]
    status, num_written = acom.write(device, 0xa1, data)
    
    #time.sleep(0.054)   
    #data = [0x55,0xa5,0xaa]
    #status, num_written = acom.write(device, 0xa1, data)    
     
    
    print "\n" + "\n" + "ALL DONE"
else:
    print('Error:No device detected!')




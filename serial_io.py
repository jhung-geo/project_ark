import time
import serial
import serial.tools.list_ports
import string
import sys

#Default I2C slave address
address = '26'

STATUS_OK = 0
STATUS_ERROR = 1        

ARK_PID = 67
ARK_VID = 9025

#convert string to hex
toHex = lambda x:"".join([hex(ord(c))[2:].zfill(2) for c in x])

#convert hex repr to string
def toStr(s):
    return s and chr(int(s[:2], base=16)) + toStr(s[2:]) or ''


def convert_hex_to_ascii(h):
    chars_in_reverse = []
    while h != 0x0:
        chars_in_reverse.append(chr(h & 0xFF))
        h = h >> 8

    chars_in_reverse.reverse()
    return ''.join(chars_in_reverse)


def i2c_address(addr):
    address = '{:02X}'.format(addr)#str(addr)#int(str(addr))
    #print(address)

def enum():
    ser = serial.Serial()
    port_list = []
    a=serial.tools.list_ports.comports()
    for w in a:
        #print( w.device, w.pid, w.vid, w.name)
        if w.pid == ARK_PID and w.vid == ARK_VID:
            #print( w.device, w.pid, w.vid, w.name)
            ser.baudrate=115200
            ser.port=w.device
            ser.open()
            while ser.isOpen() == False:
                pass#print "not yet open"
            port_list += w.device
    return(ser)

def read(uid, reg, length, data):
    """
    Reads data from a target demo device.

    First performs a write to the device with the target register
    as the payload before reading back the device data.

    Args:
      uid:    Protocol-specific identification data for the target
              device.
      reg:    The register address to start reading from.
      length: The number of bytes to read.
      data:   The list to fill with read data.

    Returns:
      status: Operation status code.
      count:  The number of bytes read from the target.
    """
    #block cannot exceed 32 bytes
    if length > 32:
	return STATUS_ERROR
    uid.flushInput()
    uid.flushOutput()
    num_read = 0
    out = ''
    out += '41'
    out += address
    out += '4C'
    out += '01'
    out += '77'#'57'
    if reg < 0x10 and reg != 0:
        out += '0'
    out += '{:02X}'.format(reg)#str(reg)
    out += '4C'
    out += '{:02X}'.format(length)
    out += '52'
       
    input = toStr(out)
    uid.write(input)
    readback = ''
    #print(out)
    # let's wait one second before reading output (let's give device time to answer)
    #time.sleep(0.005)#float(length)*0.002)#15)
    while uid.in_waiting == 0:
	pass
    
    while uid.inWaiting() > 0:
        readback += uid.read(1)          
	
    if readback != '':
	del data[:]
	for i in range(len(readback)):
	    #print ">>" + toHex(readback[i:i+1])
	    data.append(int(toHex(readback[i:i+1]),16))
	    i=i+1

    num_read = len(data)
    status = STATUS_OK

    return status, num_read


def write(uid, reg, data):
    """
    Writes data to a target demo device.

    Args:
      uid:    Protocol-specific identification data for the target
              device.
      reg:    The register address to start writing to.
      data:   The list of bytes to write to the target.

    Returns:
      status: Operation status code.
      count:  The number of bytes written to the target.
    """
    
    #block cannot exceed 32 bytes
    if len(data) > 31:
	return STATUS_ERROR    
    num_written = 0
    
    #num_read = 0
    out = ''
    out += '41'
    out += address
    out += '4C'
    if len(data) < 10:
	out += '0'
    out += str(len(data)+1)#'{:02X}'.format(length)
    out += '57'
    if reg < 0x10:
	out += '0'
    out += '{:02X}'.format(reg)#str(reg)
    for i in range(len(data)):
	out += '{:02X}'.format(data[i])#str(data[i])
    input = toStr(out)
    #print(out)
    uid.write(input)
    # let's wait one second before reading output (let's give device time to answer)
    #time.sleep(float(len(data))*0.0015)    
    
    while uid.out_waiting > 0:
	pass    
    
    num_written = len(data)
    status = STATUS_OK

    return status, num_written


def close(handle):
    handle.close()
    return STATUS_OK
"""    
##Test code below
temp = []
seri = enum()
i2c_address(0x26)
time.sleep(4)
i = 100
print len(temp)
while i > 0:
    status, num_read = read(seri, 0x80, 1, temp)
    temp[0] ^= 0x08
    if len(temp) > 1:
	print "SUN TIN WONG"
	print i
	print len(temp)
	break
    status, num_write = write(seri, 0x80, temp)
    #time.sleep(0.2)
    status, num_read = read(seri, 0x80, 1, temp)
    print(temp[0])    
    i -= 1
close(seri)
exit()
"""
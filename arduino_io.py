import time
import serial
import serial.tools.list_ports
import string
import sys

# Known I2C slave address
addr_list = [0x26, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47]

STATUS_OK = 0
STATUS_ERROR = 1

# ARK_PID = 67
# ARK_VID = 9025
# convert string to hex
toHex = lambda x: "".join([hex(ord(c))[2:].zfill(2) for c in x])


# convert hex repr to string
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
    out = ''
    if addr <= 0x7f:
        out += '41'
        out += '{:02X}'.format(addr)
    return out
'''
I2C Pull-up control, still under development
'''
def pullup(serial_port,state):
    #out = ''
    #uid = (port, addr)
    if state:
        out = '50'
    else:
        out = '70'
    serial_port.flushInput()
    serial_port.flushOutput()    
    foo = toStr(out)
    serial_port.write(foo)
    while serial_port.out_waiting > 0:
        pass
    
    
def i2c_clock(uid, clock):
    if clock > 40 or clock < 0:
        print "I2C clock out of range"
        return
    num_written = 0
    uid.flushInput()
    uid.flushOutput()
    out = ''
    out += '43'
    out += str(clock)
    #print(out)
    input = toStr(out)
    uid.write(input)

    while uid.out_waiting > 0:
        pass

def address_check(port): # Scan all possible slave address to find the valid one
    devices = []
    for addr in addr_list:
        uid = (port, addr)
        status, num_write = write(uid, 0xdd, [0x00])
        if status == STATUS_OK:
            devices.append(uid)
    return devices


def enum():
    devices = []
    a = serial.tools.list_ports.comports()
    for w in a:
        print(w.device, w.pid, w.vid, w.name)
        if w.pid and w.vid:  # Looking for a COM port with PID and VID
            ser = serial.Serial()
            ser.baudrate = 921600#115200
            ser.port = w.device
            ser.open()
            while ser.isOpen() == False:
                pass # print "not yet open"
            time.sleep(4) # wait 4 second
            
            #pullup(ser,True)
            #time.sleep(1) # Delay for the line to be pulled up
            
            devices += address_check(ser)
            #print len(devices)
            #if len(devices) == 0:
                #print "pull it up"
                #pullup(ser,True)
                #devices += address_check(ser)
        else:
            print "Not Arduino"
    return(devices)


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
    # block cannot exceed 32 bytes
    if length > 32:
        return STATUS_ERROR
    uid[0].flushInput()
    uid[0].flushOutput()
    num_read = 0
    out = i2c_address(uid[1])
    if len(out) <= 0:
        return STATUS_ERROR
    out += '4C'
    out += '01'
    out += '77'
    out += '{:02X}'.format(reg)
    out += '4C'
    out += '{:02X}'.format(length)
    out += '52'

    input = toStr(out)
    uid[0].write(input)
    readback = ''
    # print(out)
    # let's wait one second before reading output (let's give device time to answer)
    #if length < 5:
        #wait_time = 0.006
    #else:
        #wait_time = float(length)*0.001
    #time.sleep(wait_time)#float(length)*0.001)#15)
    while uid[0].in_waiting == 0:
        pass

    while uid[0].inWaiting() > 0:
        readback += uid[0].read(1)

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

    #I2C buffer only 32 bytes, including address.  For write data over 31 bytes long send first
    #16 byte w/ address, then restart the write to send the rest

    #print len(data)
    #if len(data) > 31:
    ##print "size too big"
    #return STATUS_ERROR
    num_written = 0
    uid[0].flushInput()
    uid[0].flushOutput()

    out = i2c_address(uid[1])
    if len(out) <= 0:
        return STATUS_ERROR
    out += '4C'
    if len(data) > 16:
        t = 16
    else:
        t = len(data)
    out += '{:02X}'.format(t+1)

    if (len(data)) > 16:
        out += '77'
    else:
        out += '57'

    out += '{:02X}'.format(reg)
    for i in range(0,t):
        out += '{:02X}'.format(data[i])
    input = toStr(out)
    #print(out)
    uid[0].write(input)

    while uid[0].out_waiting > 0:
        pass

    if len(data) > 16:
        out = i2c_address(uid[1])
        if len(out) <= 0:
            return STATUS_ERROR
        out += '4C'
        t = len(data) - t
        out += '{:02X}'.format(t)
        out += '57'

        for i in range(t,len(data)):
            out += '{:02X}'.format(data[i])
        input = toStr(out)
        #print(out)
        uid[0].write(input)
        # let's wait one second before reading output (let's give device time to answer)
        #time.sleep(float(len(data))*0.0015)

        while uid[0].out_waiting > 0:
            pass

    readback = ''
    while uid[0].in_waiting == 0:
        pass

    status = STATUS_OK
    while uid[0].inWaiting() > 0:
        rc = uid[0].read(1)
        if ord(rc) != 5:
            status = STATUS_ERROR

    num_written = len(data)
    return status, num_written


def close(handle):
    handle.close()
    return STATUS_OK

'''test code'''
#aio = enum()[0]
#close(aio)
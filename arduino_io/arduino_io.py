from __future__ import absolute_import
from __future__ import print_function
import time
import serial
import serial.tools.list_ports
#import string
#import sys
from six.moves import range

STATUS_OK = 0
STATUS_ERROR = 1

# convert string to hex
#toHex = lambda x: "".join([hex(ord(c))[2:].zfill(2) for c in x])
def toHex(x):
    return "".join([hex(ord(c))[2:].zfill(2) for c in x])


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
    try:
        serial_port.write(foo.encode('iso-8859-1'))
    except UnicodeDecodeError:
        serial_port.write(foo)
    while serial_port.out_waiting > 0:
        pass

'''
GPIO control, still under development
'''
def dio_pin(serial_port, pin):
    if pin < 2 or pin > 13:
        print ("Digital IO pin {} out of range".format(pin))
        return STATUS_ERROR
    out = '44'
    out += str(pin)
    serial_port.flushInput()
    serial_port.flushOutput()
    out = toStr(out)
    try:
        serial_port.write(out.encode('iso-8859-1'))
    except UnicodeDecodeError:
        serial_port.write(out)

    while serial_port.out_waiting > 0:
        pass
    return STATUS_OK

def dio_mode(serial_port, pin, mode):
    if dio_pin(serial_port, pin) != STATUS_OK:
        return
    if mode < 0 or mode > 2:
        print ("Digital IO mode {} out of range".format(mode))
        return
    out = '4D'
    out += str(mode)
    serial_port.flushInput()
    serial_port.flushOutput()
    out = toStr(out)
    try:
        serial_port.write(out.encode('iso-8859-1'))
    except UnicodeDecodeError:
        serial_port.write(out)

    while serial_port.out_waiting > 0:
        pass


def dio_read(serial_port, pin):
    if dio_pin(serial_port, pin) != STATUS_OK:
        return
    out = '3C'
    serial_port.flushInput()
    serial_port.flushOutput()
    out = toStr(out)
    try:
        serial_port.write(out.encode('iso-8859-1'))
    except UnicodeDecodeError:
        serial_port.write(out)

    while serial_port.in_waiting == 0:
        pass
    readback = serial_port.read(1)
    try:
        return int.from_bytes(readback, byteorder='big')
    except AttributeError:
        return int(toHex(str(readback)[0:1]),16)


def dio_write(serial_port, pin, level):
    if dio_pin(serial_port, pin) != STATUS_OK:
        return
    if level < 0 or level > 1:
        print ("Digital IO level {} out of range".format(level))
        return
    out = '3E'
    out += str(level)
    serial_port.flushInput()
    serial_port.flushOutput()
    out = toStr(out)
    try:
        serial_port.write(out.encode('iso-8859-1'))
    except UnicodeDecodeError:
        serial_port.write(out)

    while serial_port.out_waiting > 0:
        pass
    return

def i2c_clock(uid, clock):
    if clock > 100 or clock < 0:
        print ("I2C clock out of range")
        return
    uid[0].flushInput()
    uid[0].flushOutput()
    out = '43'
    out += '{:02X}'.format(clock)
    out = toStr(out)
    try:
        uid[0].write(out.encode('iso-8859-1'))
    except UnicodeDecodeError:
        uid[0].write(out)

    while uid[0].out_waiting > 0:
        pass
    return

def address_check(port): # Scan all possible slave address to find the valid one
    devices = []
    t = int(round(time.time() * 1000))
    for addr in range(8,120): #Scan all possible I2C address
        if (int(round(time.time() * 1000)) - t) > 500: #if the address scan takes more than 500ms, escape
            break
        uid = (port, addr)
        status, num_write = write(uid, 0xdd, [0x00])
        if status == STATUS_OK:
            devices.append(uid)
            #print ("Device found @ I2C address 0x%x" %addr)
            print(("Device found @ I2C address 0x%x" %addr))
    return devices


def arduino_check(ser): # Send test string and see if target devices acknowledged
    #ser.flushInput()
    #ser.flushOutput()

    #send out "ZZ"
    out = ''
    out += '5A'
    out += '5A'

    input = toStr(out)

    start_delay = 0
    while start_delay < 10:
        ser.flushInput()
        ser.flushOutput()
        try:
            ser.write(input.encode('iso-8859-1'))
        except UnicodeDecodeError:
            ser.write(input)

        #Escape after 100 ms
        t = int(round(time.time() * 1000))
        while ser.in_waiting != 8:
            if (int(round(time.time() * 1000)) - t) > 100:
                start_delay += 1
                break
            else:
                pass
        else:
            start_delay = 10

    readback = []
    while ser.inWaiting() > 0:
        readback += ser.read(1).decode()

    if len(readback) != 0:
        if readback[0] == readback[1] == 'z':
            print(("Arduino found, FW v." + ''.join(readback[2:])))
            return True
        else:
            return False
    else:
        return False


def enum():
    devices = []
    a = serial.tools.list_ports.comports()
    for w in a:
        #print(w.device, w.pid, w.vid, w.name)
        print((w.device, w.pid, w.vid, w.name))
        if w.pid and w.vid:  # Looking for a COM port with PID and VID
            ser = serial.Serial()
            ser.baudrate = 115200
            ser.port = w.device
            ser.open()
            while ser.isOpen() is False:
                pass # print "not yet open"
            #time.sleep(4) # wait 4 second

            #pullup(ser,True)
            #time.sleep(1) # Delay for the line to be pulled up

            if arduino_check(ser) is False:
                print ("Not Arduino")
                continue

            devices += address_check(ser)
            #print len(devices)
            
        else:
            pass#print "Not Arduino"
    if devices == []:
        print ('\nDevice enumeration failed, please check connection and/or device(s)\n')
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
    try:
        uid[0].write(input.encode('iso-8859-1'))
    except UnicodeDecodeError:
        uid[0].write(input)
    readback = []
    #Escape after 100 ms
    t = int(round(time.time() * 1000))
    while uid[0].in_waiting != length:
        if (int(round(time.time() * 1000)) - t) > 100:
            return STATUS_ERROR, 0
        else:
            pass


    while uid[0].inWaiting() > 0:
        readback += uid[0].read(1)

    for i in range(len(readback)):
        try:
            readback[i] = chr(readback[i])
        except TypeError:
            break

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
    if len(data) > 32:
        t = 16
    else:
        t = len(data)
    out += '{:02X}'.format(t+1)

    if (len(data)) > 32:
        out += '77'
    else:
        out += '57'

    out += '{:02X}'.format(reg)
    for i in range(0,t):
        out += '{:02X}'.format(data[i])
    input = toStr(out)
    try:
        uid[0].write(input.encode('iso-8859-1'))
    except UnicodeDecodeError:
        uid[0].write(input)

    while uid[0].out_waiting > 0:
        pass

    if len(data) > 32:
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
        try:
            uid[0].write(input.encode('iso-8859-1'))
        except UnicodeDecodeError:
            id[0].write(input)

        # let's wait one second before reading output (let's give device time to answer)
        #time.sleep(float(len(data))*0.0015)

        while uid[0].out_waiting > 0:
            pass

    #readback = ''

    #Escape after 10 ms
    t = int(round(time.time() * 1000))
    while uid[0].in_waiting == 0:
        if (int(round(time.time() * 1000)) - t) > 10:
            return STATUS_ERROR, 0
        else:
            pass

    status = STATUS_OK
    while uid[0].inWaiting() > 0:
        rc = uid[0].read(1).decode()
        if ord(rc) != 5:
            status = STATUS_ERROR

    num_written = len(data)
    return status, num_written


def close(handle):
    handle.close()
    return STATUS_OK

'''test code'''
# import numpy as np

# def twos_comp(val, bits):
#     if (val & (1 << (bits - 1))) != 0:
#         val -= (1 << bits)
#     return val

# aio = enum()
# data = []

#i2c_clock(aio[-1],10)
#time.sleep(0.1)
# write(aio[-1], 8, [0xF0])
# time.sleep(0.01)
# read(aio[-1], 8, 1, data)
# print(data)
# write(aio[-1], 11, [0])
# time.sleep(0.01)
# read(aio[-1], 11, 1, data)
# print(data)
# write(aio[-1], 0, [0x8B, 0x35])
# time.sleep(0.01)
# print()
#i2c_clock(aio[-1],100)
#time.sleep(0.1)
# t = time.time()
# raw = []
# temp = []
# while time.time() - t < 5:
#     read(aio[-1], 3, 4, data)
#     raw.append(twos_comp((data[0] << 4) + (data[1] >> 4), 12))
#     temp.append(twos_comp((data[2] << 4) + (data[3] >> 4), 12))
#     print(raw[-1], temp[-1])
# print(np.round(np.mean(raw)), np.round(np.mean(temp)))
# close(aio[-1][0])
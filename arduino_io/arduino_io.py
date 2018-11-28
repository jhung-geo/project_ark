from __future__ import absolute_import
from __future__ import print_function
import serial
import serial.tools.list_ports
from six.moves import range
import time

STATUS_OK = 0
STATUS_ERROR = 1

# Convert bytes to string
def bytes_to_str(b):
    return b.decode('iso-8859-1')

# Convert bytes to ordinals
def bytes_to_ord(b):
    return [c for c in bytearray(b)]

# Convert string to hex
def str_to_hex(s):
    return ''.join([hex(ord(c))[2:].zfill(2) for c in s])

# Convert hex to bytes
def hex_to_bytes(x):
    return bytearray.fromhex(x)

def serial_write(ser, out, flush=True):
    if flush:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    ser.write(out)

def serial_read(ser, length=1):
    r = ser.read(length)
    return r


# Attempt to establish handshake with serial device
def arduino_check(ser):
    out = hex_to_bytes('5A5A')

    start_delay = 0
    while start_delay < 10:
        serial_write(ser, out)

        readback = bytes_to_str(serial_read(ser, 8))
        if len(readback) == 8:
            break
        else:
            start_delay += 1

    if len(readback) == 8:
        if readback[0] == readback[1] == 'z':
            version = int(readback[2:])
            print('Arduino found at {}, FW v.{}'.format(ser.port, version))
            if version < 181025:
                global neopixel_color
                def neopixel_color(ser, r, g, b):
                    return STATUS_ERROR
            return True
    return False


# Get the number of I2C buses
def num_i2c_bus(ser):
    out = hex_to_bytes('62')
    serial_write(ser, out)
    readback = bytes_to_ord(serial_read(ser, 1))
    num_bus = 1
    if len(readback) > 0:
        num_bus = readback[0]
    if num_bus == 1:
        global set_i2c_bus
        def set_i2c_bus(ser, bus):
            return STATUS_ERROR
    return num_bus

# Select the active I2C bus
def set_i2c_bus(ser, bus):
    out = hex_to_bytes('42{:02X}'.format(bus))
    serial_write(ser, out)
    return STATUS_OK

# Format I2C address
def i2c_address(addr):
    return '41{:02X}'.format(addr) if addr <= 0x7F else ''

# Set I2C pullups
# Still under development
def pullup(ser, state):
    out = hex_to_bytes('50' if state else '70')
    serial_write(ser, out)

# Target GPIO pin
def dio_pin(ser, pin):
    if pin < 2 or pin > 13:
        print('Digital IO pin {} out of range'.format(pin))
        return STATUS_ERROR
    out = hex_to_bytes('44{:02X}'.format(pin))
    serial_write(ser, out)
    return STATUS_OK

# Set GPIO pin mode
def dio_mode(ser, pin, mode):
    if dio_pin(ser, pin) != STATUS_OK:
        return STATUS_ERROR
    if mode < 0 or mode > 2:
        print('Digital IO mode {} out of range'.format(mode))
        return STATUS_ERROR
    out = hex_to_bytes('4D{:02X}'.format(mode))
    serial_write(ser, out)
    return STATUS_OK

# Read GPIO pin state
def dio_read(ser, pin):
    if dio_pin(ser, pin) != STATUS_OK:
        return STATUS_ERROR
    out = hex_to_bytes('3C')
    serial_write(ser, out)
    readback = bytes_to_ord(serial_read(ser, 1))
    return readback[0]

# Write GPIO pin state
def dio_write(ser, pin, level):
    if dio_pin(ser, pin) != STATUS_OK:
        return STATUS_ERROR
    if level < 0 or level > 1:
        print('Digital IO level {} out of range'.format(level))
        return STATUS_ERROR
    out = hex_to_bytes('3E{:02X}'.format(level))
    serial_write(ser, out)
    return STATUS_OK

def neopixel_color(ser, r, g, b):
    if r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
        return STATUS_ERROR
    out = hex_to_bytes('58{:02X}{:02X}{:02X}'.format(r, g, b))
    serial_write(ser, out)
    return STATUS_OK

# Set active I2C bus clock speed
def i2c_clock(ser, clock):
    if clock > 100 or clock <= 0:
        print('I2C clock {} out of range'.format(clock))
        return STATUS_ERROR
    out = hex_to_bytes('43{:02X}'.format(clock))
    serial_write(ser, out)
    return STATUS_OK

# Scan all I2C buses for all possible slave addresses
def address_check(ser, addrs):
    devices = []

    num_bus = num_i2c_bus(ser)
    print('Found {} I2C bus(es)'.format(num_bus))
    for b in range(num_bus):
        # Scan all possible I2C addresses
        for addr in addrs:
            uid = (ser, b, addr)
            status, num_write = write(uid, 0xdd, [0x00])
            if status == STATUS_OK:
                devices.append(uid)
                print('Device found on bus {} @ I2C address 0x{:02X}'.format(b, addr))

    return devices


def enum(ports=[], baudrate=115200, addrs=range(8, 120)):
    devices = []
    if len(ports) is 0:
        ports = [p.device for p in serial.tools.list_ports.comports()]

    for port in ports:
        try:
            ser = serial.Serial(port)
            ser.baudrate = baudrate
            ser.write_timeout = 0
            ser.timeout = 1
            while not ser.isOpen():
                pass

            if not arduino_check(ser):
                print('Not Arduino')
                continue

            devices += address_check(ser, addrs)
        except (OSError, serial.SerialException):
            pass

    if devices == []:
        print('\nDevice enumeration failed, please check connection and/or device(s)\n')

    return(devices)


def read(uid, reg, length, data):
    """
    Reads data from a target device.

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

    # Block cannot exceed 32 bytes
    if length > 32:
        return STATUS_ERROR, 0

    ser = uid[0]
    bus = uid[1]
    addr = uid[2]

    set_i2c_bus(ser, bus)

    out = hex_to_bytes('{}4C0177{:02X}4C{:02X}52'.format(i2c_address(addr), reg, length))
    if len(out) < 9:
        return STATUS_ERROR, 0
    serial_write(ser, out)

    readback = bytes_to_ord(serial_read(ser, length))
    if len(readback) != length:
        print('Received {}, expected {}'.format(len(readback), length))
        return STATUS_ERROR, len(readback)

    data[:] = readback

    return STATUS_OK, len(data)


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

    # I2C buffer only 32 bytes, including address.  For write data over 31 bytes long send first
    # 16 byte w/ address, then restart the write to send the rest

    ser = uid[0]
    bus = uid[1]
    addr = uid[2]

    set_i2c_bus(ser, bus)

    if len(data) > 32:
        n = 16
    else:
        n = len(data)
    hex = '{}4C{:02X}{}'.format(i2c_address(addr), n + 1, '77' if len(data) > 32 else '57')
    hex += '{:02X}'.format(reg)
    for i in range(n):
        hex += '{:02X}'.format(data[i])
    out = hex_to_bytes(hex)
    serial_write(ser, out)

    if len(data) > 32:
        hex = '{}4C{:02X}57'.format(i2c_address(addr), len(data) - n)
        for i in range(n, len(data)):
            hex += '{:02X}'.format(data[i])
        out = hex_to_bytes(hex)
        serial_write(ser, out, False)

    readback = bytes_to_ord(serial_read(ser, 1))
    if len(readback) == 1:
        if readback[0] == 5:
            return STATUS_OK, len(data)
    return STATUS_ERROR, len(data)


def close(ser):
    ser.close()
    return STATUS_OK

'''test code'''
if __name__ == "__main__":
    import numpy as np

    def twos_comp(val, bits):
        if (val & (1 << (bits - 1))) != 0:
            val -= (1 << bits)
        return val

    aio = enum(baudrate=9600, addrs=[0x44, 0x45, 0x46, 0x47])
    if len(aio) == 0:
        exit()

    data = []
    module = -1
    preload = 16
    gain = 3
    timeout = 10

    i2c_clock(aio[-1][0],10)
    write(aio[module], 8, [0xF0])
    time.sleep(0.01)
    i2c_clock(aio[-1][0],20)
    read(aio[module], 8, 1, data)
    print(data)
    i2c_clock(aio[-1][0],30)
    write(aio[module], 11, [preload << 3])
    time.sleep(0.01)
    i2c_clock(aio[-1][0],100)
    read(aio[module], 11, 1, data)
    print(data)
    write(aio[module], 0, [0x9B, (gain << 4) + 0x05])
    time.sleep(0.01)
    print()

    t = time.time()
    raw = []
    temp = []
    count = 0
    while time.time() - t < timeout:
    # while True:
        read(aio[module], 3, 4, data)
        raw.append(twos_comp((data[0] << 4) + (data[1] >> 4), 12))
        temp.append(twos_comp((data[2] << 4) + (data[3] >> 4), 12))
        # print(count, time.time() - t, raw[-1], temp[-1])
        count += 1
    print(np.round(np.mean(raw)), np.round(np.mean(temp)))
    close(aio[module][0])

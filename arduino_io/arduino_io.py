from __future__ import absolute_import
from __future__ import print_function
import serial
import serial.tools.list_ports
from six.moves import range
import time

STATUS_OK = 0
STATUS_ERROR = 1

# Convert string to hex
def str_to_hex(s):
    return ''.join([hex(ord(c))[2:].zfill(2) for c in s])

# Convert hex to string
def hex_to_str(x):
    return x and chr(int(x[:2], base=16)) + hex_to_str(x[2:]) or ''

# Convert hex to ascii
def hex_to_ascii(x):
    chars_in_reverse = []
    while x != 0:
        chars_in_reverse.append(chr(x & 0xFF))
        x = x >> 8

    chars_in_reverse.reverse()
    return ''.join(chars_in_reverse)

# Backwards-compatible serial write
def serial_write(ser, out, flush=True):
    if flush:
        ser.flushInput()
        ser.flushOutput()
    try:
        ser.write(out.encode('iso-8859-1'))
    except UnicodeDecodeError:
        ser.write(out)


def serial_read(ser, length=0, timeout=0.1):
    readback = []
    ser.timeout = timeout if timeout > 0 else None
    r = ser.read(length)
    try:
        readback += r.decode()
    except UnicodeDecodeError:
        readback += r
    return readback





# Attempt to establish handshake with serial device
def arduino_check(ser):
    out = hex_to_str('5A5A')

    start_delay = 0
    while start_delay < 10:
        serial_write(ser, out)

        # Escape after 100 ms
        readback = serial_read(ser, 8)
        if len(readback) == 8:
            break
        else:
            start_delay += 1

    if len(readback) == 8:
        if readback[0] == readback[1] == 'z':
            version = ''.join(readback[2:])
            print('Arduino found at {}, FW v.{}'.format(ser.port, version))
            if version < 181025:
                global neopixel_color
                def neopixel_color(ser, r, g, b):
                    return STATUS_ERROR
            return True
    return False


# Get the number of I2C buses
def num_i2c_bus(ser):
    out = hex_to_str('62')
    serial_write(ser, out)
    readback = serial_read(ser, 1)
    num_bus = 1
    if len(readback) > 0:
        try:
            num_bus = int.from_bytes(readback[0], byteorder='big')
        except AttributeError:
            num_bus = int(str_to_hex(str(readback[0])[0]),16)
    if num_bus == 1:
        global set_i2c_bus
        def set_i2c_bus(ser, bus):
            return STATUS_ERROR
    return num_bus

# Select the active I2C bus
def set_i2c_bus(ser, bus):
    out = hex_to_str('42{:02X}'.format(bus))
    serial_write(ser, out)
    return STATUS_OK

# Format I2C address
def i2c_address(addr):
    return '41{:02X}'.format(addr) if addr <= 0x7F else ''

# Set I2C pullups
# Still under development
def pullup(ser, state):
    out = hex_to_str('50' if state else '70')
    serial_write(ser, out)

# Target GPIO pin
def dio_pin(ser, pin):
    if pin < 2 or pin > 13:
        print('Digital IO pin {} out of range'.format(pin))
        return STATUS_ERROR
    out = hex_to_str('44{:02X}'.format(pin))
    serial_write(ser, out)
    return STATUS_OK

# Set GPIO pin mode
def dio_mode(ser, pin, mode):
    if dio_pin(ser, pin) != STATUS_OK:
        return STATUS_ERROR
    if mode < 0 or mode > 2:
        print('Digital IO mode {} out of range'.format(mode))
        return STATUS_ERROR
    out = hex_to_str('4D{:02X}'.format(mode))
    serial_write(ser, out)
    return STATUS_OK

# Read GPIO pin state
def dio_read(ser, pin):
    if dio_pin(ser, pin) != STATUS_OK:
        return STATUS_ERROR
    out = hex_to_str('3C')
    serial_write(ser, out)
    readback = serial_read(ser, 1)
    try:
        return int.from_bytes(readback[0], byteorder='big')
    except AttributeError:
        return int(str_to_hex(str(readback[0])[0]),16)

# Write GPIO pin state
def dio_write(ser, pin, level):
    if dio_pin(ser, pin) != STATUS_OK:
        return STATUS_ERROR
    if level < 0 or level > 1:
        print('Digital IO level {} out of range'.format(level))
        return STATUS_ERROR
    out = hex_to_str('3E{:02X}'.format(level))
    serial_write(ser, out)
    return STATUS_OK

def neopixel_color(ser, r, g, b):
    if r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
        return STATUS_ERROR
    out = hex_to_str('58{:02X}{:02X}{:02X}'.format(r, g, b))
    serial_write(ser, out)
    return STATUS_OK

# Set active I2C bus clock speed
def i2c_clock(ser, clock):
    if clock > 100 or clock <= 0:
        print('I2C clock {} out of range'.format(clock))
        return STATUS_ERROR
    out = hex_to_str('43{:02X}'.format(clock))
    serial_write(ser, out)
    return STATUS_OK

# Scan all I2C buses for all possible slave addresses
def address_check(ser):
    devices = []

    num_bus = num_i2c_bus(ser)
    print('Found {} I2C bus(es)'.format(num_bus))
    for b in range(num_bus):
        # Scan all possible I2C addresses
        for addr in range(8, 120):
            uid = (ser, b, addr)
            status, num_write = write(uid, 0xdd, [0x00])
            if status == STATUS_OK:
                devices.append(uid)
                print('Device found on bus {} @ I2C address 0x{:02X}'.format(b, addr))

    return devices


def enum():
    devices = []
    ports = serial.tools.list_ports.comports()

    for port in ports:
        try:
            ser = serial.Serial(port.device)
            ser.baudrate = 115200
            ser.write_timeout = 0
            while not ser.isOpen():
                pass

            if not arduino_check(ser):
                print('Not Arduino')
                continue

            devices += address_check(ser)
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

    out = hex_to_str('{}4C0177{:02X}4C{:02X}52'.format(i2c_address(addr), reg, length))
    if len(out) < 9:
        return STATUS_ERROR, 0
    serial_write(ser, out)

    readback = serial_read(ser, length)
    if len(readback) != length:
        print('Received {}, expected {}'.format(len(readback), length))
        return STATUS_ERROR, len(readback)


    # ASDFASDFASDFASDF
    for i in range(len(readback)):
        try:
            readback[i] = chr(readback[i])
        except TypeError:
            break

    if readback != '':
        del data[:]
        for i in range(len(readback)):
            data.append(int(str_to_hex(readback[i]),16))

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
    out = hex_to_str(hex)
    serial_write(ser, out)

    if len(data) > 32:
        hex = '{}4C{:02X}57'.format(i2c_address(addr), len(data) - n)
        for i in range(n, len(data)):
            hex += '{:02X}'.format(data[i])
        out = hex_to_str(hex)
        serial_write(ser, out, False)

    # Escape after 10 ms
    readback = serial_read(ser, 1, 0.01)
    if len(readback) == 1:
        if ord(readback[0]) == 5:
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

    aio = enum()
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
    while time.time() - t < timeout:
        read(aio[module], 3, 4, data)
        raw.append(twos_comp((data[0] << 4) + (data[1] >> 4), 12))
        temp.append(twos_comp((data[2] << 4) + (data[3] >> 4), 12))
        # print(raw[-1], temp[-1])
    print(np.round(np.mean(raw)), np.round(np.mean(temp)))
    close(aio[module][0])

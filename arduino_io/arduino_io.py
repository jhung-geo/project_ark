from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import serial
import serial.tools.list_ports
try:
    import termios
except ModuleNotFoundError:
    class termios():
        class error(BaseException):
            pass
import time

STATUS_OK = 0
STATUS_ERROR = 1

_ARDUINO_HANDSHAKE = '5A5A'
_ARDUINO_NUM_BUS = '62'

_DIO_PIN = '44'
_DIO_MODE = '4D'
_DIO_READ = '3C'
_DIO_WRITE = '3E'

_NEOPIXEL_COLOR = '58'

_I2C_BUS = '42'
_I2C_ADDR = '41'
_I2C_LENGTH = '4C'
_I2C_CLOCK = '43'
_I2C_PULLUP_ON = '50'
_I2C_PULLUP_OFF = '70'

_I2C_BLE_READ_MAX_PAYLOAD = 20
_I2C_SER_READ_MAX_PAYLOAD = 32
_I2C_READ = '52'
_I2C_READ_RESTART = '72'

_I2C_WRITE_MAX_PAYLOAD = 16
_I2C_WRITE = '57'
_I2C_WRITE_RESTART = '77'

_BLE_PACKET_HEADER_LENGTH = 4
_BLE_WRITE_MAX_PAYLOAD = 20
_BLE_RSP_SYSTEM_GET_INFO = (0, 0, 0, 8)
_BLE_EVT_GAP_SCAN_RESPONSE = (1, 0, 6, 0)
_BLE_EVT_CONNECTION_STATUS = (1, 0, 3, 0)
_BLE_EVT_ATTCLIENT_GROUP_FOUND = (1, 0, 4, 2)
_BLE_EVT_ATTCLIENT_FIND_INFORMATION_FOUND = (1, 0, 4, 4)
_BLE_PROCEDURE_COMPLETED = (1, 0, 4, 1)
_BLE_ATTRIBUTE_VALUE = (1, 0, 4, 5)

ble_uuid_uart_service = [0x6e, 0x40, 0x00, 0x01, 0xb5, 0xa3, 0xf3, 0x93, 0xe0, 0xa9, 0xe5, 0x0e, 0x24, 0xdc, 0xca, 0x9e]
ble_uuid_service = [0x28, 0x00]
ble_uuid_tx = [0x6e, 0x40, 0x00, 0x02, 0xb5, 0xa3, 0xf3, 0x93, 0xe0, 0xa9, 0xe5, 0x0e, 0x24, 0xdc, 0xca, 0x9e]
ble_uuid_rx = [0x6e, 0x40, 0x00, 0x03, 0xb5, 0xa3, 0xf3, 0x93, 0xe0, 0xa9, 0xe5, 0x0e, 0x24, 0xdc, 0xca, 0x9e]

_DEBUG = False

def debug(flag):
    global _DEBUG
    _DEBUG = True if flag else False

def _log(s):
    if _DEBUG:
        print(s)

# Convert bytes to string
def _bytes_to_str(b):
    return b.decode('iso-8859-1')

# Convert bytes to ordinals
def _bytes_to_ord(b):
    return [c for c in bytearray(b)]

# Convert string to hex
def _str_to_hex(s):
    return ''.join([hex(ord(c))[2:].zfill(2) for c in s])

# Convert hex to bytes
def _hex_to_bytes(x):
    return bytearray.fromhex(x)
















def _ble_payload_length(h):
    return ((h[0] & 0x7) << 8) + h[1]

def _ble_packet_ident(h):
    mt = h[0] >> 7
    tt = (h[0] & 0x78) >> 3
    cid = h[2]
    cmd = h[3]
    return (mt, tt, cid, cmd)

def _ble_cmd_attclient_attribute_write(conn, attr, data):
    hex = '{}{:02X}{}{}{:02X}{:02X}{:02X}{:02X}{}'.format(
        '00', 4 + len(data), '04', '05',
        conn, attr & 0xFF, (attr >> 8) & 0xFF, len(data),
        ''.join(['{:02X}'.format(d) for d in data]))
    return _hex_to_bytes(hex)

def _ble_cmd_attclient_read_long(conn, attr):
    hex = '{}{}{}{}{:02X}{:02X}{:02X}'.format(
        '00', '03', '04', '08',
        conn, attr & 0xFF, (attr >> 8) & 0xFF)
    return _hex_to_bytes(hex)

def _ble_cmd_system_reset(dfu):
    hex = '{}{}{}{}{:02X}'.format(
        '00', '01', '00', '00',
        dfu)
    return _hex_to_bytes(hex)

def _ble_cmd_system_get_info():
    hex = '{}{}{}{}'.format(
        '00', '00', '00', '08')
    return _hex_to_bytes(hex)

def _ble_cmd_connection_disconnect(conn):
    hex = '{}{}{}{}{:02X}'.format(
        '00', '01', '03', '00',
        conn)
    return _hex_to_bytes(hex)

def _ble_cmd_gap_set_mode(discover, connect):
    hex = '{}{}{}{}{:02X}{:02X}'.format(
        '00', '02', '06', '01',
        discover, connect)
    return _hex_to_bytes(hex)

def _ble_cmd_gap_end_procedure():
    hex = '{}{}{}{}'.format(
        '00', '00', '06', '04')
    return _hex_to_bytes(hex)

def _ble_cmd_gap_set_scan_parameters(interval, window, active):
    hex = '{}{}{}{}{:02X}{:02X}{:02X}{:02X}{:02X}'.format(
        '00', '05', '06', '07',
        interval & 0xFF, (interval >> 8) & 0xFF,
        window & 0xFF, (window >> 8) & 0xFF,
        active)
    return _hex_to_bytes(hex)

def _ble_cmd_gap_discover(mode):
    hex = '{}{}{}{}{:02X}'.format(
        '00', '01', '06', '02',
        mode)
    return _hex_to_bytes(hex)

def _ble_cmd_gap_connect_direct(addr, addr_type, interval_min, interval_max, timeout, latency):
    hex = '{}{}{}{}{}{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}'.format(
        '00', '0F', '06', '03',
        ''.join(['{:02X}'.format(a) for a in addr]), addr_type,
        interval_min & 0xFF, (interval_min >> 8) & 0xFF,
        interval_max & 0xFF, (interval_max >> 8) & 0xFF,
        timeout & 0xFF, (timeout >> 8) & 0xFF,
        latency & 0xFF, (latency >> 8) & 0xFF)
    return _hex_to_bytes(hex)

def _ble_cmd_attclient_read_by_group_type(conn, start, end, uuid):
    hex = '{}{:02X}{}{}{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}{}'.format(
        '00', 6 + len(uuid), '04', '01',
        conn,
        start & 0xFF, (start >> 8) & 0xFF,
        end & 0xFF, (end >> 8) & 0xFF,
        len(uuid), ''.join(['{:02X}'.format(u) for u in uuid]))
    return _hex_to_bytes(hex)

def _ble_cmd_attclient_find_information(conn, start, end):
    hex = '{}{}{}{}{:02X}{:02X}{:02X}{:02X}{:02X}'.format(
        '00', '05', '04', '03',
        conn,
        start & 0xFF, (start >> 8) & 0xFF,
        end & 0xFF, (end >> 8) & 0xFF)
    return _hex_to_bytes(hex)

def _ble_write_split_packets(conn, tx, p):
    # Split into BLE packets
    for n in range(len(p[0]) // _BLE_WRITE_MAX_PAYLOAD):
        p.append(_ble_cmd_attclient_attribute_write(conn, tx, _bytes_to_ord(p[0][n * _BLE_WRITE_MAX_PAYLOAD : (n + 1) * _BLE_WRITE_MAX_PAYLOAD])))
    # Last packet of leftover bytes
    p.append(_ble_cmd_attclient_attribute_write(conn, tx, _bytes_to_ord(p[0][-(len(p[0]) % _BLE_WRITE_MAX_PAYLOAD):])))
    # Remove original
    p.pop(0)
    return p

def _ble_write_confirm(ser):
    # Wait for acknowledge response
    while True:
        if ser.in_waiting >= _BLE_PACKET_HEADER_LENGTH:
            h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
            p = _bytes_to_ord(ser.read(_ble_payload_length(h)))
            if _ble_packet_ident(h) == _BLE_PROCEDURE_COMPLETED and p[1] == 0 and p[2] == 0:
                break

def _ble_read(ser, conn, rx):
    _log('Writing {}'.format(' '.join(['{:02X}'.format(b) for b in _ble_cmd_attclient_read_long(conn, rx)])))
    ser.write(_ble_cmd_attclient_read_long(conn, rx))
    r = []
    while True:
        if ser.in_waiting >= _BLE_PACKET_HEADER_LENGTH:
            h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
            p = _bytes_to_ord(ser.read(_ble_payload_length(h)))
            if _ble_packet_ident(h) == _BLE_ATTRIBUTE_VALUE:
                _log('BLE_ATTRIBUTE_VALUE {}'.format(str(p)))
                r += p
            elif _ble_packet_ident(h) == _BLE_PROCEDURE_COMPLETED:
                _log('BLE_PROCEDURE_COMPLETED {}'.format(str(p)))
                return r[5:]








# Get the number of I2C buses
def _num_i2c_bus(uid):
    ser = uid[0]
    ble = uid[1]

    hex = _ARDUINO_NUM_BUS
    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Write packets
    for o in out:
        ser.write(o)
        if ble:
            _ble_write_confirm(ser)

    if ble:
        r = _ble_read(ser, ble[0], ble[2])
    else:
        r = _bytes_to_ord(ser.read(1))

    num_bus = r[-1] if len(r) > 0 else 1
    return num_bus

# Format I2C bus
def _i2c_bus(bus):
    return '{}{:02X}'.format(_I2C_BUS, bus) if bus >= 0 else ''

# Format I2C address
def _i2c_address(addr):
    return '{}{:02X}'.format(_I2C_ADDR, addr) if addr <= 0x7F else ''

# Format I2C length
def _i2c_length(length):
    return '{}{:02X}'.format(_I2C_LENGTH, length) if length > 0 else ''

# Set active I2C bus clock speed
def i2c_clock(uid, clock):
    ser = uid[0][0]
    ble = uid[0][1]
    # v = uid[0][2]
    nb = uid[0][3]
    bus = uid[1]
    # addr = uid[2]

    if clock > 100 or clock <= 0:
        print('I2C clock {} out of range'.format(clock))
        return STATUS_ERROR

    hex = '{}{}{:02X}'.format(
        _i2c_bus(bus) if nb > 1 else '',
        _I2C_CLOCK,
        clock)

    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Write packets
    for o in out:
        ser.write(o)
        if ble:
            _ble_write_confirm(ser)

    return STATUS_OK

# Set I2C pullups
# Still under development
def i2c_pullup(uid, pullup):
    ser = uid[0][0]
    ble = uid[0][1]
    # v = uid[0][2]
    nb = uid[0][3]
    bus = uid[1]
    # addr = uid[2]

    hex = '{}{}'.format(
        _i2c_bus(bus) if nb > 1 else '',
        _I2C_PULLUP_ON if pullup else _I2C_PULLUP_OFF)

    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Write packets
    for o in out:
        ser.write(o)
        if ble:
            _ble_write_confirm(ser)

    return STATUS_OK










# Target GPIO pin
def _dio_pin(uid, pin):
    ser = uid[0][0]
    ble = uid[0][1]
    # v = uid[0][2]
    # nb = uid[0][3]
    # bus = uid[1]
    # addr = uid[2]

    hex = '{}{:02X}'.format(
        _DIO_PIN,
        pin)

    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Write packets
    for o in out:
        ser.write(o)
        if ble:
            _ble_write_confirm(ser)

    return STATUS_OK

# Set GPIO pin mode
def dio_mode(uid, pin, mode):
    ser = uid[0][0]
    ble = uid[0][1]
    # v = uid[0][2]
    # nb = uid[0][3]
    # bus = uid[1]
    # addr = uid[2]

    _dio_pin(uid, pin)

    if mode < 0 or mode > 2:
        print('Digital IO mode {} out of range'.format(mode))
        return STATUS_ERROR

    hex = '{}{:02X}'.format(
        _DIO_MODE,
        mode)

    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Write packets
    for o in out:
        ser.write(o)
        if ble:
            _ble_write_confirm(ser)

    return STATUS_OK

# Read GPIO pin state
def dio_read(uid, pin):
    ser = uid[0][0]
    ble = uid[0][1]
    # v = uid[0][2]
    # nb = uid[0][3]
    # bus = uid[1]
    # addr = uid[2]

    _dio_pin(uid, pin)

    hex = '{}'.format(_DIO_READ)

    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Write packets
    for o in out:
        ser.write(o)
        if ble:
            _ble_write_confirm(ser)

    if ble:
        r = _ble_read(ser, ble[0], ble[2])
    else:
        r = _bytes_to_ord(ser.read(1))

    return r[-1] if len(r) > 0 else STATUS_ERROR

# Write GPIO pin state
def dio_write(uid, pin, level):
    ser = uid[0][0]
    ble = uid[0][1]
    # v = uid[0][2]
    # nb = uid[0][3]
    # bus = uid[1]
    # addr = uid[2]

    _dio_pin(uid, pin)

    if level < 0 or level > 1:
        print('Digital IO level {} out of range'.format(level))
        return STATUS_ERROR

    hex = '{}{:02X}'.format(
        _DIO_WRITE,
        level)

    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Write packets
    for o in out:
        ser.write(o)
        if ble:
            _ble_write_confirm(ser)

    return STATUS_OK










def neopixel_color(uid, r, g, b):
    ser = uid[0][0]
    ble = uid[0][1]
    v = uid[0][2]
    # nb = uid[0][3]
    # bus = uid[1]
    # addr = uid[2]

    if ble or v < 181025:
        return STATUS_ERROR

    if r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
        return STATUS_ERROR

    hex = '{}{:02X}{:02X}{:02X}'.format(
        _NEOPIXEL_COLOR,
        r,
        g,
        b)

    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Write packets
    for o in out:
        ser.write(o)
        if ble:
            _ble_write_confirm(ser)

    return STATUS_OK










def _arduino_check(uid):
    ser = uid[0]
    ble = uid[1]

    hex = _ARDUINO_HANDSHAKE
    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Try 5 times
    for t in range(5):
        # Write packets
        for o in out:
            _log('Writing {}'.format(' '.join(['{:02X}'.format(b) for b in bytearray(o)])))
            ser.write(o)
            if ble:
                _ble_write_confirm(ser)

        if ble:
            r = _ble_read(ser, ble[0], ble[2])
        else:
            r = _bytes_to_ord(ser.read(8))

        _log('Read back {}'.format(' '.join(['{:02X}'.format(b) for b in r])))

        if len(r) >= 8:
            break

    if len(r) >= 8:
        if chr(r[-8]) == chr(r[-7]) == 'z':
            v = int(''.join([chr(n) for n in r[-6:]]))
            nb = _num_i2c_bus(uid)
            return [(ser, ble, v, nb)]

    return []










def _ble_check(uid):
    ser = uid[0]

    devices = []

    # _log('BLE Reset')
    # ser.write(_ble_cmd_system_reset(0))

    _log('BLE Get Info')
    ser.write(_ble_cmd_system_get_info())
    h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
    if not h:
        _log('BLE No Response')
        return devices
    p = _bytes_to_ord(ser.read(_ble_payload_length(h)))
    if _ble_packet_ident(h) != _BLE_RSP_SYSTEM_GET_INFO:
        _log('BLE Unknown Response')
        return devices

    _log('BLE Disconnect')
    ser.write(_ble_cmd_connection_disconnect(0))
    h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
    p = _bytes_to_ord(ser.read(_ble_payload_length(h)))

    _log('BLE Stop Advertising')
    ser.write(_ble_cmd_gap_set_mode(0, 0))
    h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
    p = _bytes_to_ord(ser.read(_ble_payload_length(h)))

    _log('BLE Stop Scanning')
    ser.write(_ble_cmd_gap_end_procedure())
    h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
    p = _bytes_to_ord(ser.read(_ble_payload_length(h)))

    _log('BLE Set Scan Parameters')
    ser.write(_ble_cmd_gap_set_scan_parameters(200, 200, 1))
    h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
    p = _bytes_to_ord(ser.read(_ble_payload_length(h)))

    _log('BLE Start Scan')
    ser.write(_ble_cmd_gap_discover(1))

    time.sleep(0.5)

    _log('BLE Stop Scan')
    ser.write(_ble_cmd_gap_end_procedure())

    _log('BLE Get Scan Responses')
    ble_peripherals = []
    while ser.in_waiting >= _BLE_PACKET_HEADER_LENGTH:
        h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
        p = _bytes_to_ord(ser.read(_ble_payload_length(h)))
        if _ble_packet_ident(h) == _BLE_EVT_GAP_SCAN_RESPONSE:
            # Parse ad services
            ad_services = []
            field = []
            bytes_left = 0
            for b in p[11:]:
                if bytes_left == 0:
                    bytes_left = b
                    field = []
                else:
                    field.append(b)
                    bytes_left -= 1
                    if bytes_left == 0:
                        if field[0] in [0x02, 0x03]: # 16-bit UUIDs
                            for i in range((len(field) - 1) // 2):
                                ad_services.append(field[-1 - i * 2 : -3 - i * 2 : -1])
                        if field[0] in [0x04, 0x05]: # 32-bit UUIDs
                            for i in range((len(field) - 1) // 4):
                                ad_services.append(field[-1 - i * 4 : -5 - i * 4 : -1])
                        if field[0] in [0x06, 0x07]: # 128-bit UUIDs
                            for i in range((len(field) - 1) // 16):
                                ad_services.append(field[-1 - i * 16 : -17 - i * 16 : -1])

            # Check for uart service
            if ble_uuid_uart_service in ad_services:
                sender = p[2:8]
                addr_type = p[8]
                if (sender, addr_type) not in ble_peripherals:
                    _log('BLE UART Service Found')
                    ble_peripherals.append((sender, addr_type))

    _log('BLE Connect')
    ble_conns = []
    for peripheral in ble_peripherals:
        ser.write(_ble_cmd_gap_connect_direct(peripheral[0], peripheral[1], 8, 76, 100, 0))
        while True:
            if ser.in_waiting >= _BLE_PACKET_HEADER_LENGTH:
                h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
                p = _bytes_to_ord(ser.read(_ble_payload_length(h)))
                if _ble_packet_ident(h) == _BLE_EVT_CONNECTION_STATUS:
                    if p[1] & 5 == 5:
                        ble_conns.append([p[0]])
                        break

    _log('BLE Get Handle Range')
    for c in range(len(ble_conns)):
        ser.write(_ble_cmd_attclient_read_by_group_type(ble_conns[c][0], 0x0001, 0xFFFF, list(reversed(ble_uuid_service))))
        while True:
            if ser.in_waiting >= _BLE_PACKET_HEADER_LENGTH:
                h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
                p = _bytes_to_ord(ser.read(_ble_payload_length(h)))
                if _ble_packet_ident(h) == _BLE_EVT_ATTCLIENT_GROUP_FOUND:
                    if p[6:] == list(reversed(ble_uuid_uart_service)):
                        ble_conns[c].append(p[1] + (p[2] << 8))
                        ble_conns[c].append(p[3] + (p[4] << 8))
                elif _ble_packet_ident(h) == _BLE_PROCEDURE_COMPLETED:
                    break

    _log('BLE Get Attribute Handles')
    for c in range(len(ble_conns)):
        ser.write(_ble_cmd_attclient_find_information(ble_conns[c][0], ble_conns[c][1], ble_conns[c][2]))
        while True:
            if ser.in_waiting >= _BLE_PACKET_HEADER_LENGTH:
                h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
                p = _bytes_to_ord(ser.read(_ble_payload_length(h)))
                if _ble_packet_ident(h) == _BLE_EVT_ATTCLIENT_FIND_INFORMATION_FOUND:
                    uuid = p[4:]
                    if uuid == list(reversed(ble_uuid_tx)):
                        ble_conns[c].insert(3, p[1] + (p[2] << 8))
                    elif uuid == list(reversed(ble_uuid_rx)):
                        ble_conns[c].insert(4, p[1] + (p[2] << 8))
                elif _ble_packet_ident(h) == _BLE_PROCEDURE_COMPLETED:
                    break

    _log('BLE Arduino Check')
    for c in range(len(ble_conns)):
        devices += _arduino_check((ser, (ble_conns[c][0], ble_conns[c][3], ble_conns[c][4])))

    return devices

def _addr_check(uid, addrs):
    devices = []

    # ser = uid[0]
    # ble = uid[1]
    # v = uid[2]
    nb = uid[3]

    for b in range(nb):
        for addr in addrs:
            status, num_write = write((uid, b, addr), 0xDD, [0x00])
            if status == STATUS_OK:
                devices.append((uid, b, addr))
                print('Device found on bus {} @ I2C address 0x{:02X}'.format(b, addr))

    return devices







def enum(ports=[], baud=115200, addrs=range(8, 120)):
    """
    Enumerates connected devices

    Initializes the communication bridge first, if necessary.
    Stores the identification data for each device into a
    protocol-dependent representation.

    Args:
    ports:    A list of serial ports to probe. If empty, this function
              will probe all available ports.
    baud:     The serial port baud rate.
    addrs:    A list of I2C slave addresses to probe.

    Returns:
    devices:  A list of connected device unique identifiers.
    """
    devices = []
    if len(ports) == 0:
        ports = [p.device for p in serial.tools.list_ports.comports()]

    devs = []
    for port in ports:
        try:
            ser = serial.Serial(port)
            ser.baudrate = baud
            ser.write_timeout = 0
            ser.timeout = 1

            while not ser.isOpen():
                pass

            ser.reset_input_buffer()
            ser.reset_output_buffer()

            _log('Checking port {}'.format(port))
            d = _ble_check((ser,))
            if len(d) == 0:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                d = _arduino_check((ser, None))
            devs += d

        except (OSError, serial.SerialException, termios.error):
            pass

    _log(devs)

    for dev in devs:
        _log('Searching device {}'.format(str(dev)))
        print('Arduino found at {}{}, FW v.{}'.format(dev[0].port, ' [BLE {}]'.format(dev[1][0]) if dev[1] else '', dev[2]))
        devices += _addr_check(dev, addrs)

    if devices == []:
        print('\nDevice enumeration failed, please check connection and/or device(s)\n')

    return devices


def read(uid, reg, length, data):
    """
    Reads data from a target device.

    First performs a write to the device with the target register
    as the payload before reading back the device data.

    Args:
    uid:    Protocol-specific identification data for the target
            device.
    reg:    The register address to start reading from, or None
            to continue from the device register address pointer.
    length: The number of bytes to read.
    data:   The list to fill with read data.

    Returns:
    status: Operation status code.
    count:  The number of bytes read from the target.
    """

    ser = uid[0][0]
    ble = uid[0][1]
    # v = uid[0][2]
    nb = uid[0][3]
    bus = uid[1]
    addr = uid[2]

    _I2C_READ_MAX_PAYLOAD = _I2C_BLE_READ_MAX_PAYLOAD if ble else _I2C_SER_READ_MAX_PAYLOAD

    # Bus, address, register address
    hex = '{}{}{}{}{:02X}'.format(
        _i2c_bus(bus) if nb > 1 else '',
        _i2c_address(addr),
        _i2c_length(1),
        _I2C_WRITE_RESTART,
        reg) if reg is not None else ''

    if length <= _I2C_READ_MAX_PAYLOAD:
        hex += '{}{}'.format(
            _i2c_length(length),
            _I2C_READ)

        out = [_hex_to_bytes(hex)]

        if ble:
            out = _ble_write_split_packets(ble[0], ble[1], out)

        # Write packets
        for o in out:
            _log('Writing {}'.format(' '.join(['{:02X}'.format(b) for b in bytearray(o)])))
            ser.write(o)
            if ble:
                _ble_write_confirm(ser)

        if ble:
            r = _ble_read(ser, ble[0], ble[2])
        else:
            r = _bytes_to_ord(ser.read(length))

        _log('Read back {}'.format(' '.join(['{:02X}'.format(b) for b in r])))

        if len(r) < length:
            _log('Received {}, expected {}'.format(len(r), length))
            return STATUS_ERROR, len(r)

        data[:] = r[-length:]
        return STATUS_OK, len(data)

    else:
        hex += '{}{}'.format(
            _i2c_length(_I2C_READ_MAX_PAYLOAD),
            _I2C_READ_RESTART)

        out = [_hex_to_bytes(hex)]

        if ble:
            out = _ble_write_split_packets(ble[0], ble[1], out)

        # Write packets
        for o in out:
            _log('Writing {}'.format(' '.join(['{:02X}'.format(b) for b in bytearray(o)])))
            ser.write(o)
            if ble:
                _ble_write_confirm(ser)

        if ble:
            r = _ble_read(ser, ble[0], ble[2])
        else:
            r = _bytes_to_ord(ser.read(_I2C_READ_MAX_PAYLOAD))

        _log('Read back {}'.format(' '.join(['{:02X}'.format(b) for b in r])))

        if len(r) < _I2C_READ_MAX_PAYLOAD:
            _log('Received {}, expected {}'.format(len(r), _I2C_READ_MAX_PAYLOAD))
            return STATUS_ERROR, len(r)

        rdata = []
        if read(uid, reg + _I2C_READ_MAX_PAYLOAD, length - _I2C_READ_MAX_PAYLOAD, rdata) == (STATUS_OK, length - _I2C_READ_MAX_PAYLOAD):
            data[:] = r[-length:] + rdata
            return STATUS_OK, len(data)

def write(uid, reg, data):
    """
    Writes data to a target device.

    Args:
    uid:    Protocol-specific identification data for the target
            device.
    reg:    The register address to start writing to
    data:   The list of bytes to write to the target.

    Returns:
    status: Operation status code.
    count:  The number of bytes written to the target.
    """

    ser = uid[0][0]
    ble = uid[0][1]
    # v = uid[0][2]
    nb = uid[0][3]
    bus = uid[1]
    addr = uid[2]

    # Bus and address
    hex = '{}{}'.format(
        _i2c_bus(bus) if nb > 1 else '',
        _i2c_address(addr))

    # Split into Arduino packets
    for n in range(len(data) // _I2C_WRITE_MAX_PAYLOAD):
        # Length 16, repeated write
        hex += '{}{}'.format(
            _i2c_length(_I2C_WRITE_MAX_PAYLOAD + 1),
            _I2C_WRITE_RESTART)
        # Register address
        hex += '{:02X}'.format(reg + n * _I2C_WRITE_MAX_PAYLOAD)
        # Data payload
        hex += ''.join(['{:02X}'.format(d) for d in data[n * _I2C_WRITE_MAX_PAYLOAD : (n + 1) * _I2C_WRITE_MAX_PAYLOAD]])

    # Last packet of leftover bytes
    n = len(data) % _I2C_WRITE_MAX_PAYLOAD
    hex += '{}{}'.format(
        _i2c_length(n + 1),
        _I2C_WRITE)
    hex += '{:02X}'.format(reg + len(data) - n)
    hex += ''.join(['{:02X}'.format(d) for d in data[-n:]])

    # Serial packets
    out = [_hex_to_bytes(hex)]

    if ble:
        out = _ble_write_split_packets(ble[0], ble[1], out)

    # Write packets
    for o in out:
        _log('Writing {}'.format(' '.join(['{:02X}'.format(b) for b in bytearray(o)])))
        ser.write(o)
        if ble:
            _ble_write_confirm(ser)

    if ble:
        r = _ble_read(ser, ble[0], ble[2])
    else:
        r = _bytes_to_ord(ser.read(1))

    _log('Read back {}'.format(' '.join(['{:02X}'.format(b) for b in r])))

    if len(r) > 0 and r[-1] == 5:
        return STATUS_OK, len(data)

    return STATUS_ERROR, len(data)


def close(uid):
    ser = uid[0][0]
    ble = uid[0][1]

    if ble:
        _log('BLE Disconnect')
        ser.write(_ble_cmd_connection_disconnect(0))
        h = _bytes_to_ord(ser.read(_BLE_PACKET_HEADER_LENGTH))
        p = _bytes_to_ord(ser.read(_ble_payload_length(h)))
        if _ble_packet_ident(h) != _BLE_PROCEDURE_COMPLETED or p[1] != 0 or p[2] != 0:
            return STATUS_ERROR

    ser.close()

    return STATUS_OK









if __name__ == '__main__':
    import numpy as np

    def twos_comp(val, bits):
        if (val & (1 << (bits - 1))) != 0:
            val -= (1 << bits)
        return val

    devs = enum(addrs=range(0x44, 0x48))
    if len(devs) == 0:
        exit()

    data = []
    module = -1
    preload = 26
    gain = 3
    timeout = 10

    i2c_clock(devs[-1], 10)
    write(devs[module], 8, [0xF0])
    time.sleep(0.01)
    i2c_clock(devs[-1], 20)
    read(devs[module], 8, 1, data)
    print(data)
    i2c_clock(devs[-1], 30)
    write(devs[module], 11, [preload << 3])
    time.sleep(0.01)
    i2c_clock(devs[-1], 100)
    read(devs[module], 11, 1, data)
    print(data)
    write(devs[module], 0, [0x9B, (gain << 4) + 0x05])
    time.sleep(0.01)
    print()

    t = time.time()
    raw = []
    temp = []
    while time.time() - t < timeout:
        read(devs[module], 3, 4, data)
        raw.append(twos_comp((data[0] << 4) + (data[1] >> 4), 12))
        temp.append(twos_comp((data[2] << 4) + (data[3] >> 4), 12))
        # print(raw[-1], temp[-1])
    print(np.round(np.mean(raw)), np.round(np.mean(temp)))
    [close(d) for d in devs]


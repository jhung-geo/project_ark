import time
import serial
#import string


#address = 0
#register = 0
#length = 0
write_read = 0 #0 is Write, R is Read

#convert string to hex
toHex = lambda x:"".join([hex(ord(c))[2:].zfill(2) for c in x])
#def toHex(s):
    #lst = []
    #for ch in s:
        #hv = hex(ord(ch)).replace('0x', '')
        #if len(hv) == 1:
            #hv = '0'+hv
        #lst.append(hv)
    
    #return reduce(lambda x,y:x+y, lst)

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

# configure the serial connections (the parameters differs on the device you are connecting to)
ser = serial.Serial(
    port='COM3',
    baudrate=115200
    #parity=serial.PARITY_ODD,
    #stopbits=serial.STOPBITS_TWO,
    #bytesize=serial.SEVENBITS
)

ser.isOpen()

print 'Enter your commands below.\r\nInsert "exit" to leave the application.'

input=1
while 1 :
    # get keyboard input
    input = raw_input(">> ")
        # Python 3 users
        # input = input(">> ")    
    if input == 'exit':
        ser.close()
        exit()
    else:
        x_list = input.split(' ')
        wbuffer = ''        
        for s in range(len(x_list)):
            #print x_list[s]
            if x_list[s] == 'A':
                s = s+1
                address = x_list[s]#int(x_list[s],16)
            elif x_list[s] == 'a':
                s += 1
                register = x_list[s]#int(x_list[s],16)
            elif x_list[s] == 'l':
                s += 1
                length = x_list[s]#int(x_list[s])
            elif x_list[s] == 'w':
                write_read = 0
                for x in range(0,int(length,16)):
                    s += 1
                    wbuffer += x_list[s]
            elif x_list[s] == 'r':
                write_read = 1        
        
        
        out = ''
        if write_read == 0:
            out += '41'
            out += address
            out += '4C'
            out += length
            out += '57'
            out += register
            out += wbuffer
        else:
            out += '41'
            out += address
            out += '4C'
            out += '01'
            out += '57'   
            out += register
            out += '4C'
            out += length
            out += '52'
        input = toStr(out)
        print(out)
        print(input)
        # send the character to the device
        # (note that I happend a \r\n carriage return and line feed to the characters - this is requested by my device)
        #input = convert_hex_to_ascii(0x41264C01579D4C0352)
        ser.write(input)# + '\r\n')
        readback = ''
        # let's wait one second before reading output (let's give device time to answer)
        #time.sleep(1)
        while ser.inWaiting() > 0:
            readback += ser.read(1)

        if readback != '':
            print ">>" + toHex(readback)


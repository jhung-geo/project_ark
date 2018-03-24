# Project_ARK
Project ARK's goal is to replace existing Aardvark I2C bridge with Arduino Uno
board (Arduino Replaces aardvarK).  The project contains:

	serial_io.py		Python interface that allow user to interact with the 
						bridge
	i2c_usb_bridge.ino	Arduino board FW
	
The Arduino board is programmed to act as a virtual serial port to host machine.
User can send and receive data by issuing serial command:

	'A' set the I2C device address
	'a' set the target register address
	'l' set the length of read or write buffer
	'w' indicates it's a write operation
	'r' indicates it's a read operation
	
For example, to read 3 bytes from device 0x26, register 0x9d:

	"A 26 a 9d l 03 r"

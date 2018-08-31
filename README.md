# Project_ARK
Project ARK's goal is to replace existing Aardvark I2C bridge with Arduino Uno
board (Arduino Replaces aardvarK).  The project contains:

	arduino_io.py		Python interface that allow user to interact with the bridge

	i2c_usb_bridge.ino	Arduino board FW



To use the scripts and firmware code, you need to have:

	Python 2.7 with required modules installed (run "pip install -r requirements.txt")
	Arduino IDE (download here https://www.arduino.cc/en/Main/Software)

To build and install the module as a python package, run:

	pip install git+https://bitbucket.org/nextinput_sw/project_ark.git
	
or, if there's no Internet connection, run:
	
	python setup.py sdist
	pip install dist/arduino_io-[latest_version].tar.gz


The Arduino board is programmed to act as a virtual serial port to host machine.
User can send and receive data by issuing serial command:

	'A' set the I2C device address
	'a' set the target register address
	'l' set the length of read or write buffer
	'w' indicates it's a write operation
	'r' indicates it's a read operation

For example, to read 3 bytes from device 0x26, register 0x9d:

	"A 26 a 9d l 03 r"

You can also control the Arduino digital GPIOs with the following commands:

	'D' sets the pin number (2 through 13)
	'M' sets the pin mode (0 = input, 1 = output, 2 = input pullup)
	'<' reads from the digital pin (0 or 1)
	'>' writes to the digital pin (0 or 1)

Pin config and IO capabilities are accessible through the APIs dio_mode, dio_read, and dio_write in arduino_io.py

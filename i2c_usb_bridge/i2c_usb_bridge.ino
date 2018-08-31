// I2C to USB Adapter using Arduino

#include <Wire.h>

/**
 * These function signatures are necessary so the file can get compiled
 * with the commandline arduino-mk package (apt-get install arduino-mk)
 */
void handleReceivedData(byte data);
void initAdapter();
void handleCommand(byte command);
void handleData(byte data);
void handleWireRead();
void handleDioRead();
void handleIdent();
void toggle_LED();

/**
 * Can't access error register of TWI/Wire library. Thus no errors
 * can get recognized for Wire.requestFrom()
 */


#define CMD_I2C_ADDRESS			'A'
#define CMD_I2C_LENGTH        	'L'
#define CMD_I2C_WRITE_RESTART   'w'
#define CMD_I2C_WRITE       	'W'
#define CMD_I2C_READ_RESTART    'r'
#define CMD_I2C_READ          	'R'
#define CMD_GET_STATE       	'S'
#define CMD_GET_ERROR       	'E'
#define CMD_GET_IDENT       	'I'
#define CMD_GET_ADDRESS       	'a'
#define CMD_GET_LENGTH        	'l'
#define CMD_SET_CLOCK			'C'
#define CMD_PULLUP_ON        	'P'
#define CMD_PULLUP_OFF			'p'
#define CMD_HANDSHAKE       'Z'

#define CMD_DIO_PIN         'D'
#define CMD_DIO_MODE        'M'
#define CMD_DIO_READ        '<'
#define CMD_DIO_WRITE       '>'

#define STATE_INIT		0x00
#define STATE_ERROR		0x01
#define STATE_ADDRESS	0x02
#define STATE_LENGTH    0x03
#define STATE_WRITE   	0x05
#define STATE_CLOCK		0x06

#define STATE_DIO_PIN     0x08
#define STATE_DIO_MODE    0x09
#define STATE_DIO_WRITE   0x0A

#define STATE_HANDSHAKE   0x10

#define CHAR_RESET		0x1B    // It is somehow misleading that <ESC> is used for RESET
#define CHAR_ESCAPE		0x5C    // And "\" is the escape character.

#define CHAR_ESCAPED_RESET		0xB1
#define CHAR_ESCAPED_ESCAPE		0xC5

#define ERROR_NONE        	'N'
#define ERROR_UNESCAPE      'U'
#define ERROR_LENGTH        'L'
#define ERROR_READ        	'R'
#define ERROR_WRITEDATA     'W'
#define ERROR_SENDDATA      'S'


byte state = STATE_INIT;
byte address = 0;
byte length = 0;
byte error = 0;
boolean restart = false;
char data = 0;
boolean escape = false;
boolean led_state = false;

byte dio_pin = 0;
byte dio_mode = 3;

byte length_echo = 0;

byte read_buf[32];

byte time_stamp[6] = { //180831
	0x31,
	0x38,
	0x30,
	0x38,
	0x33,
	0x31
};

String ident = "Arduino I2C-to-USB 1.0"; 

void setup() {
	// initialize the serial communication:
	Serial.begin(115200);
	pinMode(LED_BUILTIN, OUTPUT);
	Wire.begin();
 
	// Disable internal pullups
	//pinMode(SDA, INPUT);
	//pinMode(SCL, INPUT);
  
	initAdapter();
	Wire.setClock(400000);
}

void initAdapter() {
	// End an eventually ongoing transmission
	//Wire.endTransmission();
  
	state = STATE_INIT;
	address = 0;
	length = 0;
	error = ERROR_NONE;
	restart = false;
	data = 0;
	escape = false;
}

void loop() {
	if (Serial.available()) {
	
		if (state == STATE_ERROR) {
			// Signal the PC an error
			Serial.write(error);
			
			initAdapter(); //Go back to init state after error is reported, JH
			Wire.endTransmission();
		}

		// Read data from serial port
		data = Serial.read();

		handleData(data);
		
		if (state == STATE_ERROR) {
			// Signal the PC an error
			Serial.write(error);
			
			initAdapter(); //Go back to init state after error is reported, JH
			Wire.endTransmission();
		}
	} else {
		if (state == STATE_ERROR) {
		  // Signal the PC an error
		  Serial.write(error);
		  
		  initAdapter(); //Go back to init state after error is reported, JH
		  Wire.endTransmission();
		}
	}
}

void toggle_LED() {
  /*
	if (led_state){
		digitalWrite(LED_BUILTIN, LOW);
    	led_state = false;
	} else {
		digitalWrite(LED_BUILTIN, HIGH);
    	led_state = true;
	}
  */
}

/**
 * This function handles a passed data byte according to the current state
 *
 * @param byte data: The received data byte
 * @return void;
 */
void handleData(byte data) {
	byte rv = 0;
  byte i2c_clock = 0;
	
	if (state == STATE_INIT) {
		//Serial.flush();
		// The first received byte designates the command
		handleCommand(data);
	} else if (state == STATE_ADDRESS) {
		// In state ADDRESS the passed byte denotes the address upon
		// which further commands will act.
		address = data;
		state = STATE_INIT;
	} else if (state == STATE_LENGTH) {
		// The LENGTH command defines the number of bytes which
		// should get read/written
		if (data > 32/*BUFFER_LENGTH*/) {
			state = STATE_ERROR;
			error = ERROR_LENGTH;
		} else {
			length = data;
			state = STATE_INIT;
		}
	} else if (state == STATE_WRITE) {
		// When in WRITE state the passed value is a data byte which should
		// get sent. Pass on as many bytes as specified by a previous LENGTH
		// command. Then send it out on the I2C port.
		if (length) {
			if (Wire.write(data) == 0) {
				state = STATE_ERROR;
				error = ERROR_WRITEDATA;
				return;
			}
			length--;
		}
		if (length == 0) {
			rv = Wire.endTransmission(restart ? false : true);
			if (rv != 0) {
				//state = STATE_ERROR;
				error = ERROR_SENDDATA + 10 + rv;
				Serial.write(error);     
				initAdapter(); //Go back to init state after error is reported, JH
				return;
			}
				
			//toggle_LED();
			
			if (!restart){
				//escapeSendData(state);
				Serial.write(state);
				Serial.flush();
			}
			restart = false;
			state = STATE_INIT;
		}
	} else if (state == STATE_CLOCK) {
		i2c_clock = data;
		if (i2c_clock <= 40) {
			Wire.setClock(int(i2c_clock*10000));
		}
		state = STATE_INIT;
	} else if (state == STATE_DIO_PIN) {
		dio_pin = data;
		state = STATE_INIT;
	} else if (state == STATE_DIO_MODE) {
		dio_mode = data;
		if (dio_pin > 1 && dio_pin < 14) {
			switch (dio_mode) {
				case 0:
				  pinMode(dio_pin, INPUT);
				  break;
				case 1:
				  pinMode(dio_pin, OUTPUT);
				  break;
				case 2:
				  pinMode(dio_pin, INPUT_PULLUP);
				  break;
				default:
				  break;
			}
		}
		state = STATE_INIT;
	} else if (state == STATE_DIO_WRITE) {
		if (dio_pin > 1 && dio_pin < 14) {
			digitalWrite(dio_pin, data == 0 ? LOW : HIGH);
		}
		state = STATE_INIT;
	} else if (state == STATE_HANDSHAKE) {
    //if (data == CMD_HANDSHAKE) {
		read_buf[0] = 0x7A; read_buf[1] = 0x7A;
		for (byte i = 0; i < 6; i++) {
			read_buf[i+2] = time_stamp[i];
		}
		Serial.write(read_buf, 8);
		Serial.flush();      
    //}
		state = STATE_INIT;
	}
}

/**
 * This function handles a passed command
 *
 * @param byte command: The command which should get handled
 * @return void
 */
void handleCommand(byte command) {
	switch (command) {

		case CMD_I2C_ADDRESS:
			state = STATE_ADDRESS;
			break;

		case CMD_I2C_LENGTH:
			state = STATE_LENGTH;
			break;

		case CMD_I2C_WRITE_RESTART:
			restart = true;
		case CMD_I2C_WRITE:
			Wire.beginTransmission(address);
			state = STATE_WRITE;
			break;

		case CMD_I2C_READ_RESTART:
			restart = true;
		case CMD_I2C_READ:
			handleWireRead();
			break;

		case CMD_GET_ADDRESS:
			Serial.write(address);
			break;

		case CMD_GET_LENGTH:
			Serial.write(length);
			break;

		case CMD_GET_STATE:
			Serial.write(state);
			break;

		case CMD_GET_ERROR:
			Serial.write(error);
			break;

		case CMD_GET_IDENT:
			handleIdent();
			break;
			
		case CMD_SET_CLOCK:
			state = STATE_CLOCK;
			break;
			
		case CMD_PULLUP_OFF:
			// Disable internal pullups
			pinMode(SDA, INPUT);
			pinMode(SCL, INPUT);
			break;			
			
		case CMD_PULLUP_ON:
			// Enable internal pullups
			pinMode(SDA, INPUT_PULLUP);
			pinMode(SCL, INPUT_PULLUP);
			break;			
			
		case CMD_DIO_PIN:
			state = STATE_DIO_PIN;
			break;

		case CMD_DIO_MODE:
			state = STATE_DIO_MODE;
			break;

		case CMD_DIO_READ:
			handleDioRead();
			break;

		case CMD_DIO_WRITE:
			state = STATE_DIO_WRITE;
			break;

		case CMD_HANDSHAKE:
			state = STATE_HANDSHAKE;
			break;
	}
}

void handleIdent() {
  	int len = ident.length();
  	char buf[len+1];
  	ident.toCharArray(buf, len+1);
  	Serial.write(len);
  	// We can use "Serial.write" here because we know the IDENT string
  	// doesn't contain any characters which would have to get escaped.
  	Serial.write((uint8_t*)buf, len);
}

void handleWireRead() {
	byte retry = 0;
	byte a;
	
	while (1) { //Retry 3 times if the I2C read length doesn't match with actual read size
		Wire.requestFrom((uint8_t)address, (uint8_t)length, (uint8_t)1);
    	restart = false;
    
		a = Wire.available();
		if (a == length) {
			break;
		} else if (retry++ > 3) {
			state = STATE_ERROR;
			return;
		}
	}
      

  	if (a != 0) {
    	for (byte i = 0; i < a; i++) {
      		read_buf[i] = Wire.read();
    	}
		//toggle_LED();
  	}
    
    Serial.write(read_buf, a);
  	Serial.flush();  	
	
  	if (Wire.available() != 0) {
    	state = STATE_ERROR;
  	} else {
    	state = STATE_INIT;
  	}
}

void handleDioRead() {
    if (dio_pin > 1 && dio_pin < 14) {
		byte level = digitalRead(dio_pin);
		Serial.write(level == LOW ? 0 : 1);
		Serial.flush();
    }
    state = STATE_INIT;
}

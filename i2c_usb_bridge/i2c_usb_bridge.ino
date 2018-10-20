// I2C to USB Adapter using Arduino

#include <Wire.h>
#include <SoftwareWire.h>

/**
 * These function signatures are necessary so the file can get compiled
 * with the commandline arduino-mk package (apt-get install arduino-mk)
 */
void resetAdapter();
void handleData(uint8_t data);
void handleCommand(uint8_t cmd);
void handleError();
void handleIdent();
void handleWireRead();
void handleDioRead();

/**
 * Can't access error register of TWI/Wire library. Thus no errors
 * can get recognized for Wire.requestFrom()
 */

#define TGL_LED()               digitalWrite(LED_BUILTIN, digitalRead(LED_BUILTIN) == LOW ? 1 : 0)
#define SET_LED()               digitalWrite(LED_BUILTIN, HIGH)
#define CLR_LED()               digitalWrite(LED_BUILTIN, LOW)

// General
#define CMD_HANDSHAKE           'Z'
#define CMD_GET_ERROR           'E'
#define CMD_GET_IDENT           'I'
#define CMD_GET_STATE           'S'

// I2C bus configuration
#define CMD_GET_NUM_I2C_BUS     'b'
#define CMD_I2C_BUS             'B'
#define CMD_SET_CLOCK           'C'
#define CMD_PULLUP_ON           'P'
#define CMD_PULLUP_OFF          'p'

// I2C bus operation
#define CMD_I2C_ADDRESS         'A'
#define CMD_I2C_LENGTH          'L'
#define CMD_I2C_WRITE_RESTART   'w'
#define CMD_I2C_WRITE           'W'
#define CMD_I2C_READ_RESTART    'r'
#define CMD_I2C_READ            'R'

#define CMD_GET_ADDRESS         'a'
#define CMD_GET_LENGTH          'l'

// DIO operation
#define CMD_DIO_PIN             'D'
#define CMD_DIO_MODE            'M'
#define CMD_DIO_READ            '<'
#define CMD_DIO_WRITE           '>'



#define STATE_HANDSHAKE         0x10

#define STATE_INIT              0x00
#define STATE_ERROR             0x01
#define STATE_ADDRESS           0x02
#define STATE_LENGTH            0x03
#define STATE_WRITE             0x05
#define STATE_CLOCK             0x06
#define STATE_BUS               0x07

#define STATE_DIO_PIN           0x08
#define STATE_DIO_MODE          0x09
#define STATE_DIO_WRITE         0x0A


#define CHAR_RESET              0x1B    // It is somehow misleading that <ESC> is used for RESET
#define CHAR_ESCAPE             0x5C    // And "\" is the escape character.

#define CHAR_ESCAPED_RESET      0xB1
#define CHAR_ESCAPED_ESCAPE     0xC5

#define ERROR_NONE              'N'
#define ERROR_UNESCAPE          'U'
#define ERROR_LENGTH            'L'
#define ERROR_READ              'R'
#define ERROR_WRITEDATA         'W'
#define ERROR_SENDDATA          'S'

#ifdef ARDUINO_METRO_M4
#define I2C_CLK_LIMIT 1000000
#else
#define I2C_CLK_LIMIT 400000
#endif

#define NUM_I2C_BUS             2
#define SW_WIRE_1_SCL           7
#define SW_WIRE_1_SDA           6
#define SW_WIRE_2_SCL           5
#define SW_WIRE_2_SDA           4
#define SW_WIRE_3_SCL           3
#define SW_WIRE_3_SDA           2

uint8_t time_stamp[6] = { // 180831
  0x31,
  0x38,
  0x31,
  0x30,
  0x30,
  0x31
};


String ident = "Arduino I2C-to-USB 1.0";


SoftwareWire swWire1(SW_WIRE_1_SDA, SW_WIRE_1_SCL);
SoftwareWire swWire2(SW_WIRE_2_SDA, SW_WIRE_2_SCL);
SoftwareWire swWire3(SW_WIRE_3_SDA, SW_WIRE_3_SCL);

TwoWire **wires;

uint8_t activeWire = 0;

uint8_t wiresSCL[NUM_I2C_BUS] = {
  SCL,
#if NUM_I2C_BUS > 1
  SW_WIRE_1_SCL,
#endif
#if NUM_I2C_BUS > 2
  SW_WIRE_2_SCL,
#endif
#if NUM_I2C_BUS > 3
  SW_WIRE_3_SCL,
#endif
};

uint8_t wiresSDA[NUM_I2C_BUS] = {
  SDA,
#if NUM_I2C_BUS > 1
  SW_WIRE_1_SDA,
#endif
#if NUM_I2C_BUS > 2
  SW_WIRE_2_SDA,
#endif
#if NUM_I2C_BUS > 3
  SW_WIRE_3_SDA,
#endif
};


uint8_t state = STATE_INIT;
uint8_t address = 0;
uint8_t length = 0;
uint8_t error = 0;
bool restart = false;
uint8_t read_buf[32];


uint8_t dio_pin = 0;
uint8_t dio_mode = 3;


void setup() {
  // Initialize LED
  pinMode(LED_BUILTIN, OUTPUT);
  
  // Initialize the serial communication
  Serial.begin(115200);

  // Initialize I2C buses
  wires = new TwoWire*[NUM_I2C_BUS];
  wires[0] = &Wire;
#if NUM_I2C_BUS > 1
  wires[1] = &swWire1;
#endif
#if NUM_I2C_BUS > 2
  wires[2] = &swWire2;
#endif
#if NUM_I2C_BUS > 3
  wires[3] = &swWire3;
#endif

  // Configure I2C buses
  for (uint8_t b = 0; b < NUM_I2C_BUS; b++) {
    pinMode(wiresSCL[b], INPUT_PULLUP);
    pinMode(wiresSDA[b], INPUT_PULLUP);
    wires[b]->begin();
    wires[b]->setClock(I2C_CLK_LIMIT);
  }
  
#ifdef ARDUINO_AVR_UNO
	// Disable internal pullups
	pinMode(SDA, INPUT);
	pinMode(SCL, INPUT);
#endif

  // Initialize state machine
  resetAdapter();
}

void resetAdapter() {
  state = STATE_INIT;
  address = 0;
  length = 0;
  error = ERROR_NONE;
  restart = false;
}

void loop() {
  if (Serial.available()) {
    if (state == STATE_ERROR) {
      handleError();
    }

    // Read and handle data from serial port
    char data = Serial.read();
    if (data >= 0) {
      handleData(data);
    }

    if (state == STATE_ERROR) {
      handleError();
    }
  } else {
    if (state == STATE_ERROR) {
      handleError();
    }
  }
}

/**
 * This function handles a passed data byte according to the current state
 *
 * @param uint8_t data: The received data byte
 * @return void;
 */
void handleData(uint8_t data) {
  switch (state) {

    case STATE_INIT:
      // The first received byte designates the command
      handleCommand(data);
      break;

    case STATE_HANDSHAKE:
      // In state HANDSHAKE, the host must repeat the HANDSHAKE command
      // for the handshake to occur
      if (data == CMD_HANDSHAKE) {
        read_buf[0] = 0x7A;
        read_buf[1] = 0x7A;
        for (uint8_t i = 0; i < 6; i++) {
          read_buf[i + 2] = time_stamp[i];
        }
        Serial.write(read_buf, 8);
        Serial.flush();
      }
      state = STATE_INIT;
      break;

    case STATE_BUS:
      // In state BUS, the passed byte denotes the I2C bus to activate
      data = data > (NUM_I2C_BUS - 1) ? (NUM_I2C_BUS - 1) : data;
      if (activeWire != data) {
        activeWire = data;
        resetAdapter();
      }
      state = STATE_INIT;
      break;

    case STATE_CLOCK:
      // In the CLOCK state, the passed byte indicates the desired I2C
      // clock speed (in 10kHz)
      wires[activeWire]->endTransmission();
      wires[activeWire]->setClock((data * 10000) > I2C_CLK_LIMIT ? I2C_CLK_LIMIT : (data * 10000));
      resetAdapter();
      break;

    case STATE_ADDRESS:
      // In state ADDRESS, the passed byte denotes the address upon
      // which further commands will act
      address = data;
      state = STATE_INIT;
      break;

    case STATE_LENGTH:
      // In state LENGTH, the passed byte defines the number of bytes
      // to read or write
      if (data > 32) {
        state = STATE_ERROR;
        error = ERROR_LENGTH;
      } else {
        length = data;
        state = STATE_INIT;
      }
      break;

    case STATE_WRITE:
      // In the WRITE state, accept as many data bytes as specified by a
      // previous LENGTH command, writing them to the target slave address
      if (length) {
        if (wires[activeWire]->write(data) == 0) {
          error = ERROR_WRITEDATA;
          handleError();
          return;
        }
        length--;
      }

      if (length == 0) {
        uint8_t status = wires[activeWire]->endTransmission(!restart);
        if (status != 0) {
          error = ERROR_SENDDATA + 10 + status;
          handleError();
          return;
        }

        if (!restart) {
          Serial.write(state);
          Serial.flush();
        }

        restart = false;
        state = STATE_INIT;
      }
      break;

    case STATE_DIO_PIN:
      // In the DIO_PIN state, the passed byte indicates the pin to operate on
      dio_pin = data;
      state = STATE_INIT;
      break;

    case STATE_DIO_MODE:
      // In the DIO_MODE state, the passed byte sets the active pin mode
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
        }
      }
      state = STATE_INIT;
      break;

    case STATE_DIO_WRITE:
      // In the DIO_WRITE state, the passed byte represents the pin logic level
      if (dio_pin > 1 && dio_pin < 14) {
        digitalWrite(dio_pin, data == 0 ? LOW : HIGH);
      }
      state = STATE_INIT;
      break;
      
  }
}

/**
 * This function handles a passed command
 *
 * @param uint8_t command: The command which should get handled
 * @return void
 */
void handleCommand(uint8_t cmd) {
	switch (cmd) {

    case CMD_HANDSHAKE:
      state = STATE_HANDSHAKE;
      break;

    case CMD_GET_ERROR:
      Serial.write(error);
      break;

    case CMD_GET_IDENT:
      handleIdent();
      break;

    case CMD_GET_STATE:
      Serial.write(state);
      break;

    case CMD_GET_NUM_I2C_BUS:
      Serial.write(NUM_I2C_BUS);
      break;

    case CMD_I2C_BUS:
      state = STATE_BUS;
      break;

    case CMD_SET_CLOCK:
      state = STATE_CLOCK;
      break;

    case CMD_PULLUP_ON:
      // Enable internal pullups
      pinMode(SDA, INPUT_PULLUP);
      pinMode(SCL, INPUT_PULLUP);
      break;

    case CMD_PULLUP_OFF:
      // Disable internal pullups
      pinMode(SDA, INPUT);
      pinMode(SCL, INPUT);
      break;

    case CMD_I2C_ADDRESS:
      state = STATE_ADDRESS;
      break;

    case CMD_I2C_LENGTH:
      state = STATE_LENGTH;
      break;

    case CMD_I2C_WRITE_RESTART:
      restart = true;
    case CMD_I2C_WRITE:
      if (digitalRead(wiresSCL[activeWire]) == LOW && digitalRead(wiresSDA[activeWire]) == LOW) {
        error = ERROR_SENDDATA;
        handleError();
      } else {
        wires[activeWire]->beginTransmission(address);
        state = STATE_WRITE;
        Serial.write(state);
      }
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

  }
}

void handleError() {
  // Signal error to host
  Serial.write(error);
  // Return to initial state
  resetAdapter();
}

void handleIdent() {
  int len = ident.length();
  char buf[len + 1];
  ident.toCharArray(buf, len + 1);
  Serial.write(len);
  // We can use "Serial.write" here because we know the IDENT string
  // doesn't contain any characters which would have to get escaped.
  Serial.write((uint8_t*)buf, len);
}

void handleWireRead() {
  uint8_t retry = 0;
  uint8_t a;

  // Retry a maximum of 3 times until the number of received bytes matches the requested length
  while (1) {
    wires[activeWire]->requestFrom(address, length, !restart);

    a = wires[activeWire]->available();
    if (a == length) {
      restart = false;
      break;
    } else if (retry++ > 3) {
      state = STATE_ERROR;
      restart = false;
      return;
    }
  }

  for (uint8_t i = 0; i < a; i++) {
    read_buf[i] = wires[activeWire]->read();
  }

  Serial.write(read_buf, a);
  Serial.flush();
	
  if (wires[activeWire]->available() != 0) {
    state = STATE_ERROR;
  }
}

void handleDioRead() {
  if (dio_pin > 1 && dio_pin < 14) {
    byte level = digitalRead(dio_pin);
    Serial.write(level == LOW ? 0 : 1);
    Serial.flush();
  }
}

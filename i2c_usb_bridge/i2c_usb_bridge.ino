// I2C to USB Adapter using Arduino

#include <Arduino.h>
#include <Wire.h>

/**
 * These function signatures are necessary so the file can get compiled
 * with the commandline arduino-mk package (apt-get install arduino-mk)
 */
void resetAdapter();
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


#define SERIAL_BEGIN(com, baud) do { \
                                  com.begin(baud); \
                                } while (false)
#define BLE_BEGIN(com)          do { \
                                  com.begin(); \
                                  if (BLE_RESET_ENABLE) { \
                                    com.factoryReset(); \
                                  } \
                                  com.verbose(false); \
                                  com.echo(false); \
                                  while (!com.isConnected()) { \
                                    delay(500); \
                                  } \
                                  if (com.isVersionAtLeast(BLE_MIN_FW_VERSION)) { \
                                    com.sendCommandCheckOK("AT+HWModeLED=" BLE_MODE_LED_BEHAVIOR); \
                                  } \
                                  com.setMode(BLUEFRUIT_MODE_DATA); \
                                } while (false)


#if defined ADAFRUIT_METRO_M4_EXPRESS

#include <SoftwareWire.h>
#include <Adafruit_NeoPixel.h>

#define DIO_PIN_MIN             1
#define DIO_PIN_MAX             14

#define I2C_CLK_LIMIT           1000000
#define NUM_HW_I2C_BUS          WIRE_INTERFACES_COUNT
#define NUM_SW_I2C_BUS          0
#define PIN_SWWIRE_SCL          7
#define PIN_SWWIRE_SDA          6
#define PIN_SWWIRE1_SCL         5
#define PIN_SWWIRE1_SDA         4
#define PIN_SWWIRE2_SCL         3
#define PIN_SWWIRE2_SDA         2
#define NUM_I2C_BUS             (NUM_HW_I2C_BUS + NUM_SW_I2C_BUS)

#define NUM_NEOPIXEL            1
#define PIN_NEOPIXEL            40
Adafruit_NeoPixel np = Adafruit_NeoPixel(NUM_NEOPIXEL, PIN_NEOPIXEL);

#define COM_MAIN                Serial
#define COM_MAIN_BEGIN()        SERIAL_BEGIN(COM_MAIN, 115200)

uint8_t time_stamp[6] = {
  0x30 | /* Y: */ 1,
  0x30 | /* Y: */ 8,
  0x30 | /* M: */ 1,
  0x30 | /* M: */ 2,
  0x30 | /* D: */ 0,
  0x30 | /* D: */ 5
};

#elif defined ADAFRUIT_FEATHER_M0

#include <SoftwareWire.h>
#include <SPI.h>
#include <Adafruit_BLE.h>
#include <Adafruit_BluefruitLE_SPI.h>

#define DIO_PIN_MIN             9
#define DIO_PIN_MAX             14

#define I2C_CLK_LIMIT           1000000
#define NUM_HW_I2C_BUS          WIRE_INTERFACES_COUNT
#define NUM_SW_I2C_BUS          0
#define NUM_I2C_BUS             (NUM_HW_I2C_BUS + NUM_SW_I2C_BUS)

#define BLE_RESET_ENABLE        1
#define BLE_MIN_FW_VERSION      "0.6.6"
#define BLE_MODE_LED_BEHAVIOR   "MODE"
#define BLE_SPI_CS              8
#define BLE_SPI_IRQ             7
#define BLE_SPI_RST             4
Adafruit_BluefruitLE_SPI ble(BLE_SPI_CS, BLE_SPI_IRQ, BLE_SPI_RST);

#define COM_MAIN                ble
#define COM_MAIN_BEGIN()        BLE_BEGIN(COM_MAIN)
                                
#define COM_DEBUG               Serial
#define COM_DEBUG_BEGIN()       SERIAL_BEGIN(COM_DEBUG, 115200)

uint8_t time_stamp[6] = {
  0x30 | /* Y: */ 1,
  0x30 | /* Y: */ 8,
  0x30 | /* M: */ 1,
  0x30 | /* M: */ 2,
  0x30 | /* D: */ 0,
  0x30 | /* D: */ 5
};

#elif defined ARDUINO_AVR_UNO

#define DIO_PIN_MIN             1
#define DIO_PIN_MAX             14

#define I2C_CLK_LIMIT           400000
#define NUM_HW_I2C_BUS          1
#define NUM_SW_I2C_BUS          0
#define NUM_I2C_BUS             (NUM_HW_I2C_BUS + NUM_SW_I2C_BUS)

#define COM_MAIN                Serial
#define COM_MAIN_BEGIN()        SERIAL_BEGIN(COM_MAIN, 115200)

uint8_t time_stamp[6] = {
  0x30 | /* Y: */ 1,
  0x30 | /* Y: */ 8,
  0x30 | /* M: */ 1,
  0x30 | /* M: */ 0,
  0x30 | /* D: */ 2,
  0x30 | /* D: */ 4
};

#else

#error "Board not supported"

#endif

#define DEBUG

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

// NeoPixel operation
#define CMD_NP_COLOR            'X'


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
#define ERROR_CMD               'C'
#define ERROR_DATA              'D'
#define ERROR_BUS               'B'
#define ERROR_LENGTH            'L'
#define ERROR_READ              'R'
#define ERROR_WRITEDATA         'W'
#define ERROR_SENDDATA          'S'
#define ERROR_DIO               'G'
#define ERROR_UNESCAPE          'U'


String ident = "Arduino I2C-to-USB 1.0";

TwoWire **wires;

#if NUM_SW_I2C_BUS > 0
SoftwareWire swWire(PIN_SWWIRE_SDA, PIN_SWWIRE_SCL, true, false);
#endif

#if NUM_SW_I2C_BUS > 1
SoftwareWire swWire1(PIN_SWWIRE1_SDA, PIN_SWWIRE1_SCL, true, false);
#endif

#if NUM_SW_I2C_BUS > 2
SoftwareWire swWire2(PIN_SWWIRE2_SDA, PIN_SWWIRE2_SCL, true, false);
#endif

uint8_t activeWire = 0;

uint8_t wiresSCL[NUM_I2C_BUS] = {
#if NUM_HW_I2C_BUS > 0
  PIN_WIRE_SCL,
#endif

#if NUM_HW_I2C_BUS > 1
  PIN_WIRE1_SCL,
#endif

#if NUM_HW_I2C_BUS > 2
  PIN_WIRE2_SCL,
#endif

#if NUM_SW_I2C_BUS > 0
  PIN_SWWIRE_SCL,
#endif

#if NUM_SW_I2C_BUS > 1
  PIN_SWWIRE1_SCL,
#endif

#if NUM_SW_I2C_BUS > 2
  PIN_SWWIRE2_SCL,
#endif
};

uint8_t wiresSDA[NUM_I2C_BUS] = {
#if NUM_HW_I2C_BUS > 0
  PIN_WIRE_SDA,
#endif

#if NUM_HW_I2C_BUS > 1
  PIN_WIRE1_SDA,
#endif

#if NUM_HW_I2C_BUS > 2
  PIN_WIRE2_SDA,
#endif

#if NUM_SW_I2C_BUS > 0
  PIN_SWWIRE_SDA,
#endif

#if NUM_SW_I2C_BUS > 1
  PIN_SWWIRE1_SDA,
#endif

#if NUM_SW_I2C_BUS > 2
  PIN_SWWIRE2_SDA,
#endif
};


uint8_t state = STATE_INIT;
uint8_t address = 0;
uint8_t length = 0;
uint8_t error = ERROR_NONE;
uint8_t stop = 1;
uint8_t read_buf[32];


uint8_t dio_pin = 0;
uint8_t dio_mode = 3;

void setup() {
  // Initialize LED
  pinMode(LED_BUILTIN, OUTPUT);

#ifdef ADAFRUIT_NEOPIXEL_H
  // Initialize NeoPixel
  np.begin();
  np.show();
#endif

  // Initialize I2C buses
  wires = new TwoWire*[NUM_I2C_BUS];  
  uint8_t b = 0;
#if NUM_HW_I2C_BUS > 0
  wires[b++] = &Wire;
#endif

#if NUM_HW_I2C_BUS > 1
  wires[b++] = &Wire1;
#endif

#if NUM_HW_I2C_BUS > 2
  wires[b++] = &Wire2;
#endif

#if NUM_SW_I2C_BUS > 0
  wires[b++] = &swWire;
#endif

#if NUM_SW_I2C_BUS > 1
  wires[b++] = &swWire1;
#endif

#if NUM_SW_I2C_BUS > 2
  wires[b++] = &swWire2;
#endif

  // Configure I2C buses
  for (b = 0; b < NUM_I2C_BUS; b++) {
#if defined ARDUINO_AVR_UNO
    // Disable internal 5V pullups
    pinMode(wiresSCL[b], INPUT);
    pinMode(wiresSDA[b], INPUT);
#else
    // Ensures software I2C lines [2, 7] are high when disconnected (floating), and 
    // hardware I2C lines (SCL, SDA) are low when disconnected (floating) (don't ask how)
    pinMode(wiresSCL[b], INPUT_PULLUP);
    pinMode(wiresSDA[b], INPUT_PULLUP);
#endif
    
    wires[b]->begin();
    wires[b]->setClock(I2C_CLK_LIMIT);
  }

  // Reset state machine
  resetAdapter();

#if defined DEBUG && defined COM_DEBUG
  // Initialize debug communication
  COM_DEBUG_BEGIN();
#endif
  
  // Initialize the main communication
  COM_MAIN_BEGIN();
}

void resetAdapter() {
  state = STATE_INIT;
  address = 0;
  length = 0;
  error = ERROR_NONE;
  stop = 1;
}

void loop() {
  if (COM_MAIN.available()) {
    if (state == STATE_ERROR) {
      handleError();
    }

    // Read and handle data from serial port
    char cmd = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
    COM_DEBUG.println();
    COM_DEBUG.print(cmd);
    COM_DEBUG.print(" [0x");
    if (cmd <= 0xF) COM_DEBUG.print(F("0"));
    COM_DEBUG.print(cmd, HEX);
    COM_DEBUG.print("] ");
#endif
    
    if (cmd >= 0) {
      handleCommand(cmd);
    }

    if (state == STATE_ERROR) {
      handleError();
    }
  }
}

/**
 * This function handles a passed command
 *
 * @param uint8_t command: The command which should get handled
 * @return void
 */
void handleCommand(uint8_t cmd) {
  unsigned long t0 = millis();
	switch (cmd) {

    case CMD_HANDSHAKE:
      // In state HANDSHAKE, the host must repeat the HANDSHAKE command
      // for the handshake to occur
      while (!COM_MAIN.available()) {
        delay(1);
        if (millis() - t0 > 100) {
          state = STATE_INIT;
          return;
        }
      }
      read_buf[0] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
      COM_DEBUG.print((char)read_buf[0]);
      COM_DEBUG.print(" [0x");
      if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
      COM_DEBUG.print((char)read_buf[0], HEX);
      COM_DEBUG.print("] ");
#endif
      
      if (read_buf[0] == CMD_HANDSHAKE) {
        read_buf[0] = 0x7A;
        read_buf[1] = 0x7A;
        for (uint8_t i = 0; i < 6; i++) {
          read_buf[i + 2] = time_stamp[i];
        }
        COM_MAIN.write(read_buf, 8);
        COM_MAIN.flush();
      } else {
        state = STATE_ERROR;
        error = ERROR_CMD;
      }
      break;

    case CMD_GET_ERROR:
      COM_MAIN.write(error);
      break;

    case CMD_GET_IDENT:
      handleIdent();
      break;

    case CMD_GET_STATE:
      COM_MAIN.write(state);
      break;

    case CMD_GET_NUM_I2C_BUS:
      COM_MAIN.write(NUM_I2C_BUS);
      break;

    case CMD_I2C_BUS:
      // In state BUS, the passed byte denotes the I2C bus to activate
      while (!COM_MAIN.available()) {
        delay(1);
        if (millis() - t0 > 100) {
          state = STATE_INIT;
          return;
        }
      }
      read_buf[0] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
      COM_DEBUG.print((char)read_buf[0]);
      COM_DEBUG.print(" [0x");
      if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
      COM_DEBUG.print((char)read_buf[0], HEX);
      COM_DEBUG.print("] ");
#endif
      
      if (read_buf[0] < NUM_I2C_BUS) {
        if (activeWire != read_buf[0]) {
          activeWire = read_buf[0];
          resetAdapter();
        }
      } else {
        state = STATE_ERROR;
        error = ERROR_BUS;
      }
      break;

    case CMD_SET_CLOCK:
      // In the CLOCK state, the passed byte indicates the desired I2C
      // clock speed (in 10kHz)
      while (!COM_MAIN.available()) {
        delay(1);
        if (millis() - t0 > 100) {
          state = STATE_INIT;
          return;
        }
      }
      read_buf[0] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
      COM_DEBUG.print((char)read_buf[0]);
      COM_DEBUG.print(" [0x");
      if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
      COM_DEBUG.print((char)read_buf[0], HEX);
      COM_DEBUG.print("] ");
#endif
      
      wires[activeWire]->endTransmission();
      wires[activeWire]->setClock(min(read_buf[0] * 10000, I2C_CLK_LIMIT));
      resetAdapter();
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
      // In state ADDRESS, the passed byte denotes the address upon
      // which further commands will act
      while (!COM_MAIN.available()) {
        delay(1);
        if (millis() - t0 > 100) {
          state = STATE_INIT;
          return;
        }
      }
      read_buf[0] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
      COM_DEBUG.print((char)read_buf[0]);
      COM_DEBUG.print(" [0x");
      if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
      COM_DEBUG.print((char)read_buf[0], HEX);
      COM_DEBUG.print("] ");
#endif
      
      address = read_buf[0];
      break;

    case CMD_I2C_LENGTH:
      // In state LENGTH, the passed byte defines the number of bytes
      // to read or write
      while (!COM_MAIN.available()) {
        delay(1);
        if (millis() - t0 > 100) {
          state = STATE_INIT;
          return;
        }
      }
      read_buf[0] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
      COM_DEBUG.print((char)read_buf[0]);
      COM_DEBUG.print(" [0x");
      if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
      COM_DEBUG.print((char)read_buf[0], HEX);
      COM_DEBUG.print("] ");
#endif
      
      if (read_buf[0] > 32) {
        state = STATE_ERROR;
        error = ERROR_LENGTH;
      } else {
        length = read_buf[0];
      }
      break;

    case CMD_I2C_WRITE_RESTART:
      stop = 0;
    case CMD_I2C_WRITE:
      // Flag a disconnected (floating) hardware I2C bus (SCL, SDA) 
      // by checking if both lines are LOW; if so, don't even bother trying
      // to begin a transmission
      // Disconnected (floating) software I2C buses will not trip this check, 
      // but that's okay, we'll catch them later
      if (digitalRead(wiresSCL[activeWire]) == LOW && digitalRead(wiresSDA[activeWire]) == LOW) {
        error = ERROR_SENDDATA;
      } else {
        wires[activeWire]->beginTransmission(address);
      }
  
      // In the WRITE state, accept as many data bytes as specified by a
      // previous LENGTH command, writing them to the target slave address
      for (uint8_t i = 0; i < length; i++) {
        while (!COM_MAIN.available()) {
          delay(1);
          if (millis() - t0 > 100) {
            state = STATE_INIT;
            return;
          }
        }
        read_buf[0] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
        COM_DEBUG.print((char)read_buf[0]);
        COM_DEBUG.print(" [0x");
        if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
        COM_DEBUG.print((char)read_buf[0], HEX);
        COM_DEBUG.print("] ");
#endif
        
        if (wires[activeWire]->write(read_buf[0]) == 0) {
          state = STATE_ERROR;
          error = ERROR_WRITEDATA;
          return;
        }
      }

      // If the hardware I2C bus (SCL, SDA) has been flagged as disconnected 
      // (floating), skip the endTransmission (for some reason it takes F O R E V E R) 
      // and just throw an error
      // Calling endTransmission on a disconnected (floating) software I2C bus is fine
      read_buf[0] = 4;
      if (error != ERROR_SENDDATA) {
        read_buf[0] = wires[activeWire]->endTransmission(stop);
      }
      if (read_buf[0] != 0) {
        state = STATE_ERROR;
        error = ERROR_SENDDATA + 10 + read_buf[0];
        return;
      }

      if (stop) {
        COM_MAIN.write(STATE_WRITE);
        COM_MAIN.flush();
      }

      stop = 1;
      break;

    case CMD_I2C_READ_RESTART:
      stop = 0;
    case CMD_I2C_READ:
      handleWireRead();
      break;

    case CMD_GET_ADDRESS:
      COM_MAIN.write(address);
      break;

    case CMD_GET_LENGTH:
      COM_MAIN.write(length);
      break;
      
    case CMD_DIO_PIN:
      // In the DIO_PIN state, the passed byte indicates the pin to operate on
      while (!COM_MAIN.available()) {
        delay(1);
        if (millis() - t0 > 100) {
          state = STATE_INIT;
          return;
        }
      }
      read_buf[0] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
      COM_DEBUG.print((char)read_buf[0]);
      COM_DEBUG.print(" [0x");
      if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
      COM_DEBUG.print((char)read_buf[0], HEX);
      COM_DEBUG.print("] ");
#endif
      
      if (read_buf[0] > DIO_PIN_MIN && read_buf[0] < DIO_PIN_MAX) {
        dio_pin = read_buf[0];
      } else {
        state = STATE_ERROR;
        error = ERROR_DIO;
      }
      break;

    case CMD_DIO_MODE:
      // In the DIO_MODE state, the passed byte sets the active pin mode
      while (!COM_MAIN.available()) {
        delay(1);
        if (millis() - t0 > 100) {
          state = STATE_INIT;
          return;
        }
      }
      read_buf[0] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
      COM_DEBUG.print((char)read_buf[0]);
      COM_DEBUG.print(" [0x");
      if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
      COM_DEBUG.print((char)read_buf[0], HEX);
      COM_DEBUG.print("] ");
#endif
      
      if (dio_pin > DIO_PIN_MIN && dio_pin < DIO_PIN_MAX) {
        dio_mode = read_buf[0];
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
            state = STATE_ERROR;
            error = ERROR_DIO;
            break;
        }
      }
      break;

    case CMD_DIO_READ:
      handleDioRead();
      break;

    case CMD_DIO_WRITE:
      // In the DIO_WRITE state, the passed byte represents the pin logic level
      while (!COM_MAIN.available()) {
        delay(1);
        if (millis() - t0 > 100) {
          state = STATE_INIT;
          return;
        }
      }
      read_buf[0] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
      COM_DEBUG.print((char)read_buf[0]);
      COM_DEBUG.print(" [0x");
      if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
      COM_DEBUG.print((char)read_buf[0], HEX);
      COM_DEBUG.print("] ");
#endif
      
      if (dio_pin > DIO_PIN_MIN && dio_pin < DIO_PIN_MAX) {
        digitalWrite(dio_pin, read_buf[0] == 0 ? LOW : HIGH);
      }
      break;

    case CMD_NP_COLOR:
      // In the NP_COLOR state, accept 3 bytes representing R, G, and B values
      for (uint8_t i = 0; i < 3; i++) {
        while (!COM_MAIN.available()) {
          delay(1);
          if (millis() - t0 > 100) {
            state = STATE_INIT;
            return;
          }
        }
        read_buf[i] = COM_MAIN.read();

#if defined DEBUG && defined COM_DEBUG
        COM_DEBUG.print((char)read_buf[0]);
        COM_DEBUG.print(" [0x");
        if (read_buf[0] <= 0xF) COM_DEBUG.print(F("0"));
        COM_DEBUG.print((char)read_buf[0], HEX);
        COM_DEBUG.print("] ");
#endif
        
      }
#ifdef ADAFRUIT_NEOPIXEL_H
      np.setPixelColor(0, read_buf[0], read_buf[1], read_buf[2]);
      np.show();
#endif
      break;

    default:
      // Command not recognized
      // state = STATE_ERROR;
      // error = ERROR_CMD;
      break;
  }
}

void handleError() {
  // Signal error to host
  COM_MAIN.write(error);
  // Return to initial state
  resetAdapter();
}

void handleIdent() {
  int len = ident.length();
  char buf[len + 1];
  ident.toCharArray(buf, len + 1);
  COM_MAIN.write(len);
  // We can use "Serial.write" here because we know the IDENT string
  // doesn't contain any characters which would have to get escaped.
  COM_MAIN.write((uint8_t*)buf, len);
}

void handleWireRead() {
  uint8_t retry = 0;
  uint8_t a;

  // Retry a maximum of 3 times until the number of received bytes matches the requested length
  while (1) {
    wires[activeWire]->requestFrom(address, length, stop);

    a = wires[activeWire]->available();
    if (a == length) {
      stop = 1;
      break;
    } else if (retry++ > 3) {
      state = STATE_ERROR;
      stop = 1;
      return;
    }
  }

  for (uint8_t i = 0; i < a; i++) {
    read_buf[i] = wires[activeWire]->read();
  }

  COM_MAIN.write(read_buf, a);
  COM_MAIN.flush();
  
  if (wires[activeWire]->available() != 0) {
    state = STATE_ERROR;
  }
}

void handleDioRead() {
  if (dio_pin > DIO_PIN_MIN && dio_pin < DIO_PIN_MAX) {
    byte level = digitalRead(dio_pin);
    COM_MAIN.write(level == LOW ? 0 : 1);
    COM_MAIN.flush();
  }
}

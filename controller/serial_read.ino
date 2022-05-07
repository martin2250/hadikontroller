#include "Arduino.h"

#define SERIAL_READ_BUFFER 10

char serial_read_buffer[SERIAL_READ_BUFFER];
uint8_t serial_read_pos = 0;
bool serial_read_valid = true;

void serial_read(uint32_t now) {
    while (true) {
        int rx = Serial.read();

        if (rx < 0)
            return;
        
        digitalWrite(LED_BUILTIN, 1-digitalRead(LED_BUILTIN));

        if (rx == 0x7f) {
            if (serial_read_pos > 0) {
                serial_read_pos--;
            }
        } else if (rx == '\n' || rx == '\r') {
            // ignore if not valid
            if (serial_read_valid) {
                serial_read_process();
            }
            serial_read_pos = 0;
            serial_read_valid = true;
        } else {
            if (serial_read_pos >= SERIAL_READ_BUFFER) {
                serial_read_pos = 0;
                serial_read_valid = false;
            } else {
                serial_read_buffer[serial_read_pos++] = rx;
            }
        }
    }
}

uint8_t config_led = 0;
bool config_led_changed = false;
uint8_t config_ledstrip = 0;

void serial_read_process() {
    char *buffer = serial_read_buffer;
    uint8_t len = serial_read_pos;
    if (len == 0) {
        return;
    }
    switch (buffer[0]) {
        case 'L': case 'S': {
            if (len != 3) {
                serial_read_error();
                return;
            }
            bool error = false;
            uint8_t value = 0;
            value = hex_to_int(buffer[1], &error) << 4;
            value |= hex_to_int(buffer[2], &error);
            if (error) {
                serial_read_hex_error();
            } else {
                switch (buffer[0]) {
                    case 'L': {
                        config_led_changed = config_led != value;
                        config_led = value;
                    } break;
                    case 'S': {
                        config_ledstrip = value;
                    }break;
                }
            }
        } break;
        default: {
            Serial.print("E: unknown command ");
            Serial.write(buffer[0]);
            Serial.println();
        } break;
    }
}

void serial_read_hex_error() {
    Serial.println("E: invalid hex value");
}

void serial_read_error() {
    Serial.print("E: wrong length for CMD ");
    Serial.write(serial_read_buffer[0]);
    Serial.print(" (");
    Serial.print(serial_read_pos);
    Serial.println(")");
}
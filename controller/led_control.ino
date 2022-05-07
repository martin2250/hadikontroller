#include "led_gamma.h"

extern uint8_t config_led;
extern uint8_t config_ledstrip;
extern bool config_led_changed;
extern uint8_t u_12v;
extern int8_t temperature[];

const uint8_t led_fan_min = 0x40;
const uint8_t led_fan_max_auto = 0xA0;
const uint8_t led_fan_max = 0xff;

// LED temperature actions
// Temp A: start ramping up fan
// Temp B: fan full, start dimming led
// Temp C: led at 0%
const uint8_t led_temp_a = 40;
const uint8_t led_temp_b = 50;
const uint8_t led_temp_c = 60;

uint16_t setpoint_led = 0;
uint8_t setpoint_fan = 0;

void led_control(uint32_t now) {
    static uint32_t next = 0;
    const uint16_t interval = 100;
    if (config_led_changed) {
        next = now + interval;
        config_led_changed = false;
    } else {
        if (now < next) {
            return;
        }
        next += interval;
    }

    // set LED current from gamma correction
    setpoint_led = pgm_read_word_near(led_gamma + config_led);

    // read temperatures
    int8_t t_led = temperature[0];

    if (u_12v < 8) {
        setpoint_led = 0;
        goto set_fan;
    }

    // LED too hot, turn off
    if (t_led > led_temp_c) {
        setpoint_led = 0;
        goto set_fan;
    }

    // LED getting warm, limit setpoint
    if (t_led > led_temp_b) {
        uint16_t set_max = map(t_led,
            led_temp_b,
            led_temp_c,
            led_gamma_max,
            led_gamma_min
        );
        if (setpoint_led > set_max) {
            setpoint_led = set_max;
        }
    }

set_fan:
    setpoint_fan = 0;

    // LED on? turn on fan as well
    if (setpoint_led > 0) {
        setpoint_fan = map(
            setpoint_led,
            led_gamma_min,
            led_gamma_max,
            led_fan_min,
            led_fan_max_auto
        );
    }

    // LED hot? speed up fan
    if (t_led > led_temp_a) {
        uint16_t set_min = map(
            t_led,
            led_temp_a,
            led_temp_b,
            setpoint_fan,
            led_fan_max
        );
        if (set_min > 0xff) {
            set_min = 0xff;
        }
        if (setpoint_fan < set_min) {
            setpoint_fan = set_min;
        }
    }

    pwm_output(0, 0xffff - setpoint_led);
    analogWrite(3, setpoint_fan);

    pwm_output(1, pgm_read_word_near(ledstrip_gamma + config_ledstrip));

    static uint32_t next_report = 0;
    if (now < next_report) {
        return;
    }
    next_report += 500;

    Serial.print("LED:");
    Serial.write(hex_from_int(t_led >> 4));
    Serial.write(hex_from_int(t_led >> 0));
    Serial.write(':');
    Serial.write(hex_from_int(u_12v));
    Serial.write(':');
    Serial.write(hex_from_int(setpoint_led >> 12));
    Serial.write(hex_from_int(setpoint_led >> 8));
    Serial.write(hex_from_int(setpoint_led >> 4));
    Serial.write(hex_from_int(setpoint_led >> 0));
    Serial.write(':');
    Serial.write(hex_from_int(setpoint_fan >> 4));
    Serial.write(hex_from_int(setpoint_fan >> 0));
    Serial.println();
}
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <string.h>

// Pin map
// 2: doorbell sensor
// 4: door sensor
// 7: window sensor
// 9: pwm16, LED (high power)
// 10: pwm16, LED strip
// 3: pwm8, fan
// A0: temp LED
// A1: temp (reserved)
// A1: temp (reserved)
// A3: 12V input, divided by 10k/39k

const unsigned long interval_report = 100;


void setup()
{
	// PWM outputs
	pinMode(3, OUTPUT);
	pinMode(9, OUTPUT);
	pinMode(10, OUTPUT);

	// door/window/doorbell inputs
	pinMode(2, INPUT_PULLUP);
	pinMode(4, INPUT_PULLUP);
	pinMode(7, INPUT_PULLUP);
	
	// LED
	pinMode(LED_BUILTIN, OUTPUT);

	// temperature inputs failsafe
	pinMode(A0, INPUT_PULLUP);
	pinMode(A1, INPUT_PULLUP);
	pinMode(A2, INPUT_PULLUP);

	pwm_output_init();
	temperature_init();

	Serial.begin(115200);
	Serial.println("start");
}

void loop()
{
	uint32_t now = millis();
	temperature_read(now);
	serial_read(now);
	led_control(now);
	read_inputs(now);
}
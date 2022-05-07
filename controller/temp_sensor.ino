#define TEMPERATURE_CHANNELS 1
#define TEMPERATURE_OVERSAMPLING 4
uint16_t temperature_buffer[TEMPERATURE_CHANNELS];
int8_t temperature[TEMPERATURE_CHANNELS];
uint8_t u_12v;

void temperature_init() {
    analogReference(INTERNAL4V3);
}

void temperature_read(uint32_t now) {
    static uint32_t next = 0;
    if (now < next) {
        return;
    }
    next += 100;

    u_12v = analogRead(3) / (uint16_t)(1024. * 10. / (4.3 * (10. + 39.)));

    for (uint8_t i = 0; i < TEMPERATURE_CHANNELS; i++) {
        temperature_buffer[i] -= temperature_buffer[i] / TEMPERATURE_OVERSAMPLING;

        temperature_buffer[i] += analogRead(i);

        // T = (V_in - 400mV) / (19.5mV/K)
        // V_in = temperature_buffer[i] * 4.3V/(2^10 - 1)/TEMPERATURE_OVERSAMPLING
        // -> T = -20.51 + 0.2156 temperature_buffer[i] / TEMPERATURE_OVERSAMPLING

        float t = temperature_buffer[i];
        t *= 0.2156 / TEMPERATURE_OVERSAMPLING;
        t -= 20.51;

        if (t > 127) {
            temperature[i] = 127;
        } else {
            temperature[i] = t;
        }
    }
}
uint8_t input_bell = 0;
uint8_t input_door = 0;
uint8_t input_window = 0;

void read_inputs(uint32_t now) {
    static uint32_t next = 0;
    if (now < next) {
        return;
    }
    next += 25;

    if (!digitalRead(2)) {
        input_bell += 1;
    }
    if (digitalRead(4)) {
        input_door += 1;
    }
    if (digitalRead(7)) {
        input_window += 1;
    }

    static uint32_t next_report = 0;
    if (now < next_report) {
        return;
    }
    next_report += 250;

    Serial.print("INP:");
    Serial.write((input_bell > 2) ? '1' : '0');
    Serial.write((input_door > 2) ? '1' : '0');
    Serial.write((input_window > 2) ? '1' : '0');
    Serial.println();

    input_bell = 0;
    input_door = 0;
    input_window = 0;
}
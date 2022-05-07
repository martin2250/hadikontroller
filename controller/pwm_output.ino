void pwm_output_init() {
    // PORTMUX setting for TCA -> all outputs [0:2] point to PORTB pins [0:2]
	PORTMUX.TCAROUTEA  = PORTMUX_TCA0_PORTB_gc;

	// Setup timers for single slope PWM
	TCA0.SINGLE.CTRLB = TCA_SINGLE_WGMODE_SINGLESLOPE_gc | TCA_SINGLE_CMP0EN_bm | TCA_SINGLE_CMP1EN_bm | TCA_SINGLE_CMP2EN_bm;

	// Period setting
	TCA0.SINGLE.PER = 0xFFFF;

	// Default duty cycle
	TCA0.SINGLE.CMP0BUF = 128;
	TCA0.SINGLE.CMP1BUF = 128;
	TCA0.SINGLE.CMP2BUF = 128;

	// Use DIV1, enable
	TCA0.SINGLE.CTRLA = TCA_SINGLE_CLKSEL_DIV1_gc | TCA_SINGLE_ENABLE_bm;

	// 64 * 256 - 1
	TCB3.CCMP = 0x3FFF;
	TCB3.CTRLB = TCB_CNTMODE_INT_gc;
}

void pwm_output(uint8_t channel, uint16_t value) {
	switch (channel) {
		case 0: {
			TCA0.SINGLE.CMP0BUF = value;
		} break;
		case 1: {
			TCA0.SINGLE.CMP1BUF = value;
		} break;
		case 2: {
			TCA0.SINGLE.CMP2BUF = value;
		} break;
	}
}
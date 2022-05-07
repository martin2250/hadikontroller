#!/usr/bin/python
import math

setpoint_min = 3500
setpoint_max = 45400
gamma = 2.2

i_min = math.pow(setpoint_min / setpoint_max, 1/gamma)
i_max = 1.0

values = [0]
for i in range(1, 256):
    val = math.pow(i / 255 * (i_max - i_min) + i_min, gamma)
    val = val * setpoint_max
    values.append(int(val))

f = open('led_gamma.h', 'w')
print(f'const uint16_t led_gamma_min = {setpoint_min};', file=f)
print(f'const uint16_t led_gamma_max = {setpoint_max};', file=f)
print('const uint16_t led_gamma[256] PROGMEM = {', file=f)
print(',\n'.join([f'\t{v}' for v in values]), file=f)
print('};', file=f)


values = [0]
for i in range(1, 256):
    val = math.pow(i / 255, gamma)
    val = val * 0xffff
    values.append(int(val))

print('const uint16_t ledstrip_gamma[256] PROGMEM = {', file=f)
print(',\n'.join([f'\t{v}' for v in values]), file=f)
print('};', file=f)

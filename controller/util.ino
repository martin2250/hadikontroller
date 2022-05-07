#include <stdint.h>

uint8_t hex_to_int(char c, bool *error) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'A' && c <= 'F') {
        return 10 + c - 'A';
    }
    if (c >= 'a' && c <= 'f') {
        return 10 + c - 'a';
    }
    *error = true;
    return 0;
}

char hex_from_int(uint8_t i) {
    i &= 0xF;
    if (i < 10) {
        return '0' + i;
    }
    return 'A' + i - 10;
}
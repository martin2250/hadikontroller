build: build/hadikontroller.ino.hex

led_gamma.h: gammatable.py
	./$<

build/hadikontroller.ino.hex: led_gamma.h
	arduino-cli compile --fqbn arduino:megaavr:nona4809:mode=off

PORT=$(shell readlink -f /dev/serial/by-id/usb-Arduino_LLC_Arduino_Nano_Every*)
.PHONY: upload
upload: build
	@echo "uploading to $(PORT)"
	arduino-cli upload --fqbn arduino:megaavr:nona4809:mode=off -p $(PORT)

# arduino-cli core install arduino:megaavr
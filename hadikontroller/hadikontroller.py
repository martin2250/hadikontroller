#!/usr/bin/python -u

import asyncio
import asyncio.subprocess
import datetime
import os
import shlex
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import astral
import astral.sun
import serial
from aiogram import Bot, Dispatcher, executor, types

token = Path('/run/secrets/hadikontroller_telegram_token').read_text()
portname = '/dev/ttyhadikontroller'
chat_id = Path('/run/secrets/hadikontroller_telegram_chatid').read_text()
ping_command = shlex.split(Path('/run/secrets/hadikontroller_ping_command').read_text())

conf_city = astral.LocationInfo("Karlsruhe", "Germany", "Europe/Berlin", 49.0069, 8.4037)

conf_strip_auto_elevation_min = 3
conf_strip_auto_elevation_max = 8
conf_strip_auto_brightness = 180

@dataclass
class ControllerInput:
    doorbell: bool
    door: bool
    window: bool


@dataclass
class ControllerLEDStatus:
    tled: int
    u12v: int
    sled: int
    sfan: int


def th_read_port(
    port: serial.Serial,
    loop: asyncio.BaseEventLoop,
    input_update: Callable[[ControllerInput], None],
    led_update: Callable[[ControllerLEDStatus], None],
    ):
    while True:
        line = port.readline().decode().strip()
        try:
            if line.startswith('LED:'):
                _, T, U, L, F = line.split(':')
                loop.call_soon_threadsafe(
                    led_update,
                    ControllerLEDStatus(
                        int(T, 16),
                        int(U, 16),
                        int(L, 16),
                        int(F, 16),
                    ),
                )
            if line.startswith('INP:'):
                loop.call_soon_threadsafe(
                    input_update,
                    ControllerInput(
                        bool(int(line[4])),
                        bool(int(line[5])),
                        bool(int(line[6])),
                    ),
                )
        except Exception as e:
            print('error in serial thread', e)

class LedFader:
    def __init__(self, set_led):
        self.set_led = set_led
        self.value = 0
        self._target = -1
        self._interval = 0.1
        self._fading = asyncio.Event()

    async def led_handler(self):
        while True:
            await asyncio.sleep(self._interval)
            await self._fading.wait()
            if self.value < self._target:
                self.value += 1
            elif self.value > self._target:
                self.value -= 1
            self.set_led(self.value)
            if self.value == self._target:
                self._fading.clear()

    def led_set(self, value: int):
        if value not in range(256):
            return
        self._fading.clear()
        self.value = value
        self.set_led(self.value)

    def led_fade(self, value: int, interval: float):
        if value not in range(256):
            return
        if interval < 0:
            return
        self._target = value
        self._interval = interval
        self._fading.set()


class Pinger:
    def __init__(self):
        self.last = 0

    async def handler(self):
        while True:
            p = await asyncio.subprocess.create_subprocess_exec(
                *ping_command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            if await p.wait() == 0:
                self.last = time.time()
                await asyncio.sleep(45)
            else:    
                await asyncio.sleep(10)


class Alarm:
    def __init__(self):
        self.active = asyncio.Event()
        self.time = datetime.time(0, 0)
        self.match = False
        self.on_alarm = lambda: None

    async def handler(self):
        while True:
            await asyncio.sleep(10)
            await self.active.wait()
            now = datetime.datetime.now().time()
            match = now.hour == self.time.hour and now.minute == self.time.minute
            if match and not self.match:
                self.on_alarm()
            self.match = match

    def time_set(self, alarm_time: datetime.time):
        self.time = alarm_time
        self.active.set()

    def stop(self):
        self.active.clear()

import enum


class LedStripStatus(enum.Enum):
    # turn on between X and Y o'clock when home
    AUTO = 0
    # off, go back to auto in the morning
    AUTO_OFF = 1
    MANUAL = 2

class LedStripController:
    def __init__(self, pinger: Pinger, set_ledstrip_ext):
        self.pinger = pinger
        self.set_ledstrip_ext = set_ledstrip_ext        
        self.status = LedStripStatus.AUTO
        self.manual_setpoint = 0
        self.current_value = -1
        # when was the last time the door was opened?
        self.door_last = 0
    
    def set_ledstrip(self, value: int):
        if self.current_value == value:
            return
        self.set_ledstrip_ext(value)
        self.current_value = value

    def manual(self, value: int):
        if value not in range(256):
            return
        self.status = LedStripStatus.MANUAL
        self.manual_setpoint = value
    
    def auto(self):
        self.status = LedStripStatus.AUTO
    
    def auto_off(self):
        self.status = LedStripStatus.AUTO_OFF
    
    async def handler(self):
        while True:
            await asyncio.sleep(1)
            # manual mode, just set led to value
            if self.status == LedStripStatus.MANUAL:
                self.set_ledstrip(self.manual_setpoint)
            # switch back to auto at 8 in the morning
            elif self.status == LedStripStatus.AUTO_OFF:
                self.set_ledstrip(0)
                # cleared by alarm
                continue
            elif self.status == LedStripStatus.AUTO:
                sun_elevation = astral.sun.elevation(conf_city)
                # conditions
                now = datetime.datetime.now()
                at_home = (time.time() - self.pinger.last) < 300
                door_opened = (time.time() - self.door_last) < 300
                strip_on = at_home or door_opened
                # map elevation range to (0, 1)
                value = (sun_elevation - conf_strip_auto_elevation_min) / (conf_strip_auto_elevation_max - conf_strip_auto_elevation_min)
                value = min(max(value, 0), 1)
                brightness = int(conf_strip_auto_brightness * (1 - value))
                if not strip_on:
                    brightness = 0
                # turn strip on or not?
                self.set_ledstrip(brightness)


async def main():
    port = serial.Serial(portname, baudrate=115200)

    def set_led(value: int):
        if value not in range(0, 0x100):
            value = 0
        port.write(f'L{value:02X}\n'.encode())
        port.flush()

    def set_led_strip(value: int):
        if value not in range(0, 0x100):
            value = 0
        port.write(f'S{value:02X}\n'.encode())
        port.flush()

    led_fader = LedFader(set_led)

    pinger = Pinger()
    alarm = Alarm()

    led_strip_controller = LedStripController(pinger, set_led_strip)
    led_status = ControllerLEDStatus(127, 0, 0, 0)
    input_status = ControllerInput(False, False, False)

    bot = Bot(token=token)
    disp = Dispatcher(bot=bot)
    Bot.set_current(bot)

    chat = await bot.get_chat(chat_id)

    ############################################################################
    # Controller event handlers

    def controller_led_update(status_new: ControllerLEDStatus):
        nonlocal led_status
        led_status = status_new

    async def doorbell_notify():
        for _ in range(5):
            await bot.send_message(chat_id, 'doorbell')
            await asyncio.sleep(1)

    async def doorbell_led():
        orig = led_fader.value
        for _ in range(3):
            led_fader.set_led(0xff)
            await asyncio.sleep(0.25)
            led_fader.set_led(0)
            await asyncio.sleep(0.25)
        led_fader.set_led(orig)

    def controller_input_update(status_new: ControllerInput):
        nonlocal input_status
        if status_new.doorbell and not input_status.doorbell:
            asyncio.create_task(doorbell_notify())
            asyncio.create_task(doorbell_led())
        if status_new.door and not input_status.door:
            led_strip_controller.door_last = time.time()
            if (time.time() - pinger.last) > 300:
                asyncio.create_task(bot.send_message(chat_id, 'door opened'))
        input_status = status_new

    # start serial port reader
    loop = asyncio.get_event_loop()
    threading.Thread(
        target=th_read_port,
        args=[
            port,
            loop,
            controller_input_update,
            controller_led_update,
        ],
    ).start()

    ############################################################################
    # Alarm event handlers

    def alarm_handler():
        asyncio.create_task(bot.send_message(chat_id, 'alarm triggered'))
        # led_fader.led_fade(0xff, 0.75)
        led_fader.set_led(0xff)
        led_strip_controller.auto()

    alarm.on_alarm = alarm_handler

    ############################################################################
    # Telegram event handlers

    async def telegram_poll():
        try:
            await disp.start_polling()
        finally:
            await bot.close()

    async def telegram_start(event: types.Message):
        await event.answer(
            f'Hello, {event.from_user.get_mention(as_html=True)} 👋!',
            parse_mode=types.ParseMode.HTML,
        )

    async def telegram_status(event: types.Message):
        openclosed = {
            True: 'open',
            False: 'closed',
        }
        since_ping = datetime.datetime.now() - datetime.datetime.fromtimestamp(pinger.last)
        await event.reply(
            f'''HaDiKontroller Status:
door: {openclosed[input_status.door]}
window: {openclosed[input_status.window]}
led: 0x{led_fader.value:02X}, {led_status.tled} °C
alarm: {alarm.time if alarm.active.is_set() else 'off'}
ping: {since_ping.total_seconds():0.1f}s ago'''
        )

    async def telegram_led(event: types.Message):
        cmd = event.text.split(' ')
        if len(cmd) not in (2, 3):
            await event.reply('invalid arguments')
            return
        try:
            val = int(cmd[1], 0)
            if not val in range(256):
                raise ValueError()
        except:
            await event.reply('invalid value')
            return
        if len(cmd) == 2:
            led_fader.led_set(val)
            await event.reply(f'set LED to {val}')
            return
        try:
            time = float(cmd[2])
            if time < 0:
                time = 0
            interval = time / abs(led_fader.value - val)
            led_fader.led_fade(val, interval)
            await event.reply(f'fade LED to {val}')
        except:
            await event.reply('invalid value')

    async def telegram_alarm(event: types.Message, do_pin: bool = True):
        _, val = event.text.split(' ')
        if val == 'off':
            alarm.stop()
            await event.reply('turned off alarm')
            if do_pin:
                await chat.unpin_all_messages()
            return
        try:
            alarm.time_set(datetime.datetime.strptime(val, '%H:%M').time())
            if do_pin:
                await chat.unpin_all_messages()
                await chat.pin_message(event.message_id)
            await event.reply(f'set alarm to {alarm.time}')
        except:
            await event.reply('invalid value')

    async def telegram_strip(event: types.Message):
        cmd = event.text.split(' ')
        if len(cmd) != 2:
            await event.reply('invalid arguments')
            return

        if cmd[1] == 'auto':
            led_strip_controller.auto()
            await event.reply(f'set LED to auto')
            return
        elif cmd[1] == 'off':
            led_strip_controller.auto_off()
            await event.reply(f'set LED to auto off')
            return
        try:
            val = int(cmd[1], 0)
            if not val in range(256):
                raise ValueError()
        except:
            await event.reply('invalid value')
            return
        
        led_strip_controller.manual(val)
        await event.reply(f'set LED to {val}')

    disp.register_message_handler(telegram_start, commands={'start'})
    disp.register_message_handler(telegram_status, commands={'status'})
    disp.register_message_handler(telegram_alarm, commands={'alarm'})
    disp.register_message_handler(telegram_led, commands={'led'})
    disp.register_message_handler(telegram_strip, commands={'strip'})

    # ############################################################################
    # get alarm from pinned message

    if chat.pinned_message and chat.pinned_message.text.startswith('/alarm'):
        await telegram_alarm(chat.pinned_message, False)

    # ############################################################################
    # background tasks

    asyncio.create_task(led_strip_controller.handler())
    asyncio.create_task(pinger.handler())
    asyncio.create_task(alarm.handler())
    asyncio.create_task(led_fader.led_handler())
    await telegram_poll()

asyncio.run(main())

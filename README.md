# mqtt2pins-wiznet5k

#### CircuitPython based project for Adafruit wiznet5k to use MQTT to control GPIOs

Using:
- [Adafruit Ethernet FeatherWing](https://www.adafruit.com/product/3201)
- [Adafruit Feather RP2040](https://www.adafruit.com/product/4884) -- or any feather capable of running Circuit Python!
- **Optional** [Adafruit Non-Latching Mini Relay](https://www.adafruit.com/product/2895)

This project aims to provide a simple and generic codebase to connect to an MQTT broker
via wired Ethernet for controlling the GPIO pins of the microcontroller.
See the example below on how to make the GPIO pins on/off, as well as get the operational state.

![mqtt2pins-wiznet5k](https://live.staticflickr.com/65535/52530845394_81c7b21497_k.jpg)

**Note:** This code is used in a setup where I needed to control 4 [relays](https://www.mouser.com/ProductDetail/Panasonic-Industrial-Devices/HY1-4.5V?qs=YINDDaGsG3FSnYZykcV2vQ%3D%3D) wired to an alarm system.
You can see more [pictures of that project here :art:](https://flic.kr/s/aHBqjAhSD3).

Also, the enclosure printed for that project is available at [OnShape via this link](https://cad.onshape.com/documents/dfc64f3f819c48ce95943d31/w/ad13758cd223c2b401c080f3/e/51e3f25110950b06329750fe).

#### Adafruit Show and Tell

Adafruit offers guides along with products that make it easy to build this project.
Liz hosted [Show and Tell](https://www.youtube.com/c/adafruit/videos) on Dec 7th, 2022 and
I had the honor of [talking about what I did](https://youtu.be/dXhzo44lXQ0?t=598) to them.

[![mqtt2pins-wiznet5k talk](https://img.youtube.com/vi/dXhzo44lXQ0/2.jpg)](https://youtu.be/dXhzo44lXQ0?t=598)

# Usage

### Removing _all_ files from CIRCUITPY drive

```
# NOTE: Do not do this before backing up all files!!!
>>> import storage ; storage.erase_filesystem()
```

### Copying files from cloned repo to CIRCUITPY drive
```
# First, get to the REPL prompt so the board will not auto-restart as
# you copy files into it

# Assuming that [Feather](https://www.adafruit.com/category/943) is mounted under /Volumes/CIRCUITPY
$  cd ${THIS_REPO_DIR}
$  [ -e ./code.py ] && \
   [ -d /Volumes/CIRCUITPY/ ] && \
   rm -rf /Volumes/CIRCUITPY/*.py && \
   (tar czf - *) | ( cd /Volumes/CIRCUITPY ; tar xzvf - ) && \
   echo ok || echo not_okay
```

### Libraries

Use [circup](https://learn.adafruit.com/keep-your-circuitpython-libraries-on-devices-up-to-date-with-circup)
to install these libraries:

```text
$ python3 -m venv .env && source ./.env/bin/activate && \
  pip install --upgrade pip

$ pip3 install circup

$ for LIB in \
    adafruit_led_animation \
    adafruit_logging \
    adafruit_minimqtt \
    adafruit_wiznet5k \
    asyncio \
    neopixel \
    ; do circup install $LIB ; done
```

This is what it should look like:
```text
$ ls /Volumes/CIRCUITPY/
LICENSE    boot_out.txt   lib                    queue.py  secrets.py.sample
README.md  code.py        mqtt2pins_wiznet5k.py

$ ls /Volumes/CIRCUITPY/lib
adafruit_bus_device	adafruit_logging.mpy	adafruit_pixelbuf.mpy	adafruit_wiznet5k	neopixel.mpy
adafruit_led_animation	adafruit_minimqtt	adafruit_ticks.mpy	asyncio

$ cat /Volumes/CIRCUITPY/boot_out.txt
Adafruit CircuitPython 7.3.3 on 2022-08-29; Adafruit Feather RP2040 with rp2040
Board ID:adafruit_feather_rp2040

$ circup freeze | sort
Found device at /Volumes/CIRCUITPY, running CircuitPython 7.3.3.
adafruit_bus_device==5.2.3
adafruit_led_animation==2.6.1
adafruit_logging==5.0.1
adafruit_minimqtt==6.0.1
adafruit_pixelbuf==1.1.8
adafruit_ticks==1.0.8
adafruit_wiznet5k==1.12.15
asyncio==0.5.18
neopixel==6.3.7
```

### secrets.py

Make sure to create a file called secrets.py to include info on the MQTT
broker you will connect to. Use [**secrets.py.sample**](https://github.com/flavio-fernandes/mqtt2pins-wiznet5k/blob/main/secrets.py.sample)
as reference.

At this point, all needed files should be in place and all that is needed is to let
code.py run. From the Circuit Python serial console:

```text
>>  <CTRL-D>
soft reboot
...
```

Example MQTT commands

```bash
PREFIX='/onoffpins'
MQTT='broker.hivemq.com'

# Subscribing to status messages
mosquitto_sub -F '@Y-@m-@dT@H:@M:@S@z : %q : %t : %p' -h $MQTT  -t "${PREFIX}/#"

# On another shell session...

# Request general info. This will include the state of its ports and other interesting info
mosquitto_pub -h $MQTT -t "${PREFIX}/ping" -r -n

# Example output
2022-11-28T21:33:10-0500 : 0 : /onoffpins/status : {
  "ip": "192.168.10.11", "ports": "10000000", "uptime_mins": 50, "mem_free": 121776}

# Based on PINS (aka GPIOs) variable listed in the secrets.py file,
# you can publish on topics that control each port or all ports at once.

PORT0="${PREFIX}/0"

# Note: you can use 'on', 'yes', '1', 'up' to set port on.
# See: https://github.com/flavio-fernandes/mqtt2pins-wiznet5k/blob/main/mqtt2pins_wiznet5k.py#L83-L91
mosquitto_pub -h $MQTT -t $PORT0 -m 1      ; # turn port 0 on
mosquitto_pub -h $MQTT -t $PORT0 -m flip   ; # turn port 0 off
mosquitto_pub -h $MQTT -t $PORT0 -m flip   ; # turn port 0 on
mosquitto_pub -h $MQTT -t $PORT0 -r -m off ; # turn port 0 off again and retain value on broker

PORT1="${PREFIX}/1"

mosquitto_pub -h $MQTT -t $PORT1 -m 0  ; # turn port 1 off

# Set 8 ports to 'off'
mosquitto_pub -h $MQTT -t "${PREFIX}/ports" -m '00000000'

# Set port 0 to 'on', leave port 1 'as is' and set port 2 to 'off'
mosquitto_pub -h $MQTT -t "${PREFIX}/ports" -m '1.0'

# Flip ports 0 and 7 and leave others unchanged
mosquitto_pub -h $MQTT -t "${PREFIX}/ports" -m '!......!'

# Flip 8 ports
mosquitto_pub -h $MQTT -t "${PREFIX}/ports" -m '!!!!!!!!'
```

# on-off-pins-via-net

#### CircuitPython based project for Adafruit wiznet5k to use MQTT to control GPIOs

WIP...
    
### Removing _all_ files from CIRCUITPY drive

```
# NOTE: Do not do this before backing up all files!!!
>>> import storage ; storage.erase_filesystem()
```

### Copying files from cloned repo to CIRCUITPY drive
```
# First, get to the REPL prompt so the board will not auto-restart as
# you copy files into it

# Assuming that PyPortal is mounted under /Volumes/CIRCUITPY
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
    adafruit_adt7410 \
    adafruit_bitmap_font \
    adafruit_esp32spi \
    adafruit_logging \
    adafruit_minimqtt \
    adafruit_pyportal \
    neopixel \
    ; do circup install $LIB ; done
```

This is what it should look like:
```text
$ ls /Volumes/CIRCUITPY/
LICENSE         boot_out.txt  ...

$ ls /Volumes/CIRCUITPY/lib
...

$ circup freeze | sort
Found device at /Volumes/CIRCUITPY, running CircuitPython 7.3.3.
adafruit_ticks==1.0.8
adafruit_pixelbuf==1.1.8
neopixel==6.3.7
adafruit_logging==5.0.1
adafruit_bus_device==5.2.3
adafruit_wiznet5k==1.12.15
adafruit_minimqtt==6.0.1
asyncio==0.5.18
adafruit_led_animation==2.6.1
```

### secrets.py

Make sure to create a file called secrets.py to include info on the wifi as well as the MQTT
broker you will connect to. Use [**secrets.py.sample**](https://github.com/flavio-fernandes//blob/main/secrets.py.sample)
as reference.

At this point, all needed files should be in place, and all that
is needed is to let code.py run. From the Circuit Python serial console:

```text
>>  <CTRL-D>
soft reboot
...
```

Example MQTT commands

```bash
PREFIX='/onoffpins'
MQTT=192.168.10.10

# Subscribing to status messages

mosquitto_sub -F '@Y-@m-@dT@H:@M:@S@z : %q : %t : %p' -h $MQTT  -t "${PREFIX}/#"

# Request general info
mosquitto_pub -h $MQTT -t "${PREFIX}/ping" -r -n

# WIP...

mosquitto_pub -h $MQTT -t "${PREFIX}/0" -r -m 1
mosquitto_pub -h $MQTT -t "${PREFIX}/0" -m flip

mosquitto_pub -h $MQTT -t "${PREFIX}/1" -m 0

# Set all ports to 'off'   
mosquitto_pub -h $MQTT -t "${PREFIX}/ports" -m '00000000'

# Set port 0 to 'on', leave port 1 'as is' and port 2 to 'off'   
mosquitto_pub -h $MQTT -t "${PREFIX}/ports" -m '1.0'

# Flip ports 0 and 7 and leave others unchanged
mosquitto_pub -h $MQTT -t "${PREFIX}/ports" -m '!......!'

# Flip all ports
mosquitto_pub -h $MQTT -t "${PREFIX}/ports" -m '!!!!!!!!'
    
mosquitto_pub -h $MQTT -t "${PREFIX}/boom" -r -n
```

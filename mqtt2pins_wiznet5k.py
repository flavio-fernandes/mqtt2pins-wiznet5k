import gc
import json
import asyncio
import board
import busio
import digitalio
import supervisor
import microcontroller
import neopixel
import random
import time
from adafruit_wiznet5k.adafruit_wiznet5k import WIZNET5K
import adafruit_wiznet5k.adafruit_wiznet5k_socket as socket
import adafruit_logging as logging
from adafruit_led_animation import color

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from queue import Queue, QueueFull

try:
    from secrets import secrets
except ImportError:
    print("Required info is kept in secrets.py, please add them there!")
    raise

try:
    from secrets import PINS
except ImportError:
    print("Required PINS to manage is kept in secrets.py, please add them there!")
    raise


class Controls:
    def __init__(self):
        self.debug = False
        self.pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, auto_write=True)
        self.pins = [digitalio.DigitalInOut(x) for x in PINS]
        for pin in self.pins:
            pin.switch_to_output()
        self.mqtt_connected = False
        self.mqtt_client = None
        self.eth = None
        self.uptime_mins = 0
        self.soft_dog = 0
        self.counters = {}
        self.mqtt_subs = {}
        self.status_queue = Queue(maxsize=1)

    def inc_counter(self, name):
        curr_value = self.counters.get(name, 0)
        self.counters[name] = curr_value + 1

    def handle_message_boom(self, _topic, message):
        print("Handling boom")
        boom(message)

    def handle_message_ping(self, _topic, _message):
        print("Handling ping")
        send_status_now(self)

    def handle_message_ports(self, _topic, message):
        print(f"Handling ports: {message}")
        for pin_index, value_str in enumerate(message):
            if pin_index >= len(PINS):
                break
            new_value_dict = {
                "0": False,
                "1": True,
                "!": not self.pins[pin_index].value,
            }
            self.pins[pin_index].value = new_value_dict.get(
                value_str, self.pins[pin_index].value
            )

    def handle_message_port(self, topic, message):
        if not message:
            return
        try:
            pin_index = int(topic.split("/")[-1])
        except Exception as e:
            print(f"Failed to get pin_index from message: {e}")
            return

        assert pin_index >= 0 and pin_index < len(
            PINS
        ), f"Unexpected pin_index {topic} from message: {message}"
        value = message.lower() in {
            "1",
            "yes",
            "yeah",
            "yay",
            "yup",
            "y",
            "on",
            "up",
            "go",
        }
        if not value and message.lower() in {
            "!",
            "not",
            "flip",
            "other",
            "reverse",
            "change",
        }:
            value = not self.pins[pin_index].value
        print(f"Setting pin {pin_index} ({PINS[pin_index]}) to {value}")
        self.pins[pin_index].value = value


def boom(message):
    print(f"Handling boom: {message}")
    time.sleep(5)
    # bye bye cruel world
    microcontroller.reset()


# Define MQTT callback methods which are called when events occur
def connected(client, controls, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print(f"Connected to MQTT BROKER")

    # Subscribe to all feeds
    topic = secrets["topic_prefix"] + "/boom"
    client.subscribe(topic)
    controls.mqtt_subs[topic] = controls.handle_message_boom

    topic = secrets["topic_prefix"] + "/ping"
    client.subscribe(topic)
    controls.mqtt_subs[topic] = controls.handle_message_ping

    topic = secrets["topic_prefix"] + "/ports"
    client.subscribe(topic)
    controls.mqtt_subs[topic] = controls.handle_message_ports

    for index in range(len(PINS)):
        topic = secrets["topic_prefix"] + f"/{index}"
        client.subscribe(topic)
        controls.mqtt_subs[topic] = controls.handle_message_port

    controls.inc_counter("connect")
    controls.mqtt_connected = True


def disconnected(_client, controls, rc):
    # This method is called when the client is disconnected
    print(f"Disconnected from MQTT BROKER rc: {rc}")
    controls.mqtt_connected = False
    controls.inc_counter("disconnected")


def subscribe(_client, controls, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print(f"Subscribed to {topic} with QOS level {granted_qos}")
    controls.inc_counter("subscribe")


def publish(_client, controls, topic, pid):
    # This method is called when the client publishes data to a feed.
    print(f"Published to {topic} with PID {pid}")
    controls.inc_counter("publish")


def message(client, topic, message):
    # This method is called when a topic the client is subscribed to
    # has a new message.
    print("New message on topic {0}: {1}".format(topic, message))
    controls = client._user_data
    if topic in controls.mqtt_subs:
        controls.mqtt_subs[topic](topic, message)
        controls.inc_counter("message")


async def neo_status(controls):
    def cycle(items):
        while True:
            for item in items:
                yield item

    pixels_disc = cycle([color.RED, color.BLACK])
    pixels_conn = cycle(
        [
            color.ORANGE,
            color.YELLOW,
            color.GREEN,
            color.BLUE,
            color.PURPLE,
            color.MAGENTA,
            color.TEAL,
            color.CYAN,
            color.WHITE,
            color.GOLD,
            color.PINK,
            color.AQUA,
            color.JADE,
            color.AMBER,
            color.OLD_LACE,
        ]
    )
    while True:
        pixel_color = (
            next(pixels_conn) if controls.mqtt_connected else next(pixels_disc)
        )
        controls.pixels.fill(pixel_color)
        await asyncio.sleep(1)


async def bump_uptime(controls):
    while True:
        await asyncio.sleep(60)
        controls.uptime_mins += 1


async def trigger_send_status(controls):
    while True:
        # every 10 minutes and 10 seconds
        await asyncio.sleep(60 * 10 + 10)
        await controls.status_queue.put(True)


def send_status_now(controls):
    try:
        controls.status_queue.put_nowait(True)
    except QueueFull:
        pass


async def send_status(controls):
    mqtt_pub_status = secrets["topic_prefix"] + "/status"
    while True:
        while not controls.mqtt_connected:
            await asyncio.sleep(1)

        # Block until status is needed, which can be periodic or responding to ping msg
        _ = await controls.status_queue.get()

        ports = ""
        for pin_index in range(len(PINS)):
            ports += "1" if controls.pins[pin_index].value else "0"

        value = {
            "uptime_mins": controls.uptime_mins,
            "ip": controls.eth.pretty_ip(controls.eth.ip_address),
            "ports": ports,
            "counters": str(controls.counters),
            "mem_free": gc.mem_free(),
        }
        try:
            controls.mqtt_client.publish(mqtt_pub_status, json.dumps(value))
            controls.inc_counter("status")
            if controls.debug:
                print(f"send_status: {mqtt_pub_status}: {value}")
        except Exception as e:
            print(f"Failed to send status: {e}")


async def soft_dogwatch(controls):
    # Note: this is mostly used to handle cases when there is an exception in
    # net_monitor that could not be handled. When this happens, controls.soft_dog will
    # stop increasing and we will know it is time to panic.
    soft_dogwatch_interval = 60
    while True:
        before_soft_dog = controls.soft_dog
        await asyncio.sleep(soft_dogwatch_interval)
        if before_soft_dog == controls.soft_dog:
            boom(
                f"controls.soft_dog stuck at {before_soft_dog} after {soft_dogwatch_interval} seconds"
            )
        controls.soft_dog = 0


async def net_monitor(controls):
    cs = digitalio.DigitalInOut(board.D10)
    spi_bus = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    try:
        print("Connecting ethernet")
        controls.eth = WIZNET5K(spi_bus, cs, mac=secrets["mac"])
    except Exception as e:
        boom(f"Failed setup WIZNET5K: {e}")

    print("Chip Version:", controls.eth.chip)
    print("MAC Address:", [hex(i) for i in controls.eth.mac_address])
    print("My IP address is:", controls.eth.pretty_ip(controls.eth.ip_address))

    # Set up a MiniMQTT
    MQTT.set_socket(socket, controls.eth)
    # https://github.com/adafruit/Adafruit_CircuitPython_MiniMQTT/issues/129
    broker_user = secrets["broker_user"] if secrets["broker_user"] else None
    broker_pass = secrets["broker_pass"] if secrets["broker_pass"] else None
    controls.mqtt_client = MQTT.MQTT(
        broker=secrets["broker"],
        port=1883,
        username=broker_user,
        password=broker_pass,
        is_ssl=False,
    )

    if controls.debug:
        controls.mqtt_client.enable_logger(logging, logging.DEBUG)

    controls.mqtt_client._user_data = controls
    controls.mqtt_client.on_connect = connected
    controls.mqtt_client.on_disconnect = disconnected
    controls.mqtt_client.on_subscribe = subscribe
    controls.mqtt_client.on_publish = publish
    controls.mqtt_client.on_message = message

    connect_backoff = 0
    while True:
        controls.soft_dog += 1
        await asyncio.sleep(0)
        controls.eth.maintain_dhcp_lease()

        if not controls.mqtt_connected:
            try:
                print("Connecting to MQTT broker...")
                controls.mqtt_client.connect()
                assert (
                    controls.mqtt_connected
                ), "connected callback should have happened"
                connect_backoff = 0
                # send status when MQTT gets connected
                send_status_now(controls)
            except Exception as e:
                print(f"Failed mqtt connect: {e}")
                await asyncio.sleep(connect_backoff)
                if connect_backoff < 18:
                    connect_backoff += 1
            continue

        try:
            if not controls.mqtt_client.loop(timeout=0.2):
                # Take a little break if nothing really happened
                await asyncio.sleep(0.123)
        except Exception as e:
            if controls.debug:
                print(f"Failed MQTT client loop: {e}")
            await _try_disconnect(controls)
        await asyncio.sleep(0)


async def _try_disconnect(controls):
    print("MQTT is disconnecting")
    controls.inc_counter("fail_loop")
    await asyncio.sleep(3)
    if not controls.mqtt_connected:
        if controls.debug:
            print("MQTT disconnect not needed, because broker is not connected")
        return

    # Force state to be disconnected
    controls.mqtt_connected = False
    disc_ok = False
    try:
        controls.mqtt_client.disconnect()
        disc_ok = True
        print("MQTT disconnect completed")
    except Exception as e:
        print(f"Failed mqtt disconnect: {e}")

    try:
        if not disc_ok:
            controls.inc_counter("eth_reset")
            assert controls.eth.sw_reset() == 0, f"Reset WIZNET5K did not go well"
            print("Reset WIZNET5K completed")
    except Exception as e:
        boom(f"FATAL! Failed eth reset: {e}")


async def main():
    controls = Controls()

    neo_status_task = asyncio.create_task(neo_status(controls))
    bump_uptime_task = asyncio.create_task(bump_uptime(controls))
    trigger_send_status_task = asyncio.create_task(trigger_send_status(controls))
    send_status_task = asyncio.create_task(send_status(controls))
    soft_dogwatch_task = asyncio.create_task(soft_dogwatch(controls))
    net_monitor_task = asyncio.create_task(net_monitor(controls))
    await asyncio.gather(
        neo_status_task,
        bump_uptime_task,
        trigger_send_status_task,
        send_status_task,
        soft_dogwatch_task,
        net_monitor_task,
    )


supervisor.disable_autoreload()
asyncio.run(main())

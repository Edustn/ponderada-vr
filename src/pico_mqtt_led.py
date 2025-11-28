"""
MicroPython script for Raspberry Pi Pico W that listens to the same MQTT topic
used by face_realtime.py and toggles the onboard LED whenever a message is
received. Upload this file to the Pico W (e.g., via Thonny), fill in the Wi-Fi
credentials, and run it under MicroPython firmware 1.20+.
"""

import time
import machine 
import network
import ubinascii    
from umqtt.simple import MQTTClient

# --- Wi-Fi settings ---------------------------------------------------------
WIFI_SSID = "Inteli.Iot"
WIFI_PASSWORD = "%(Yk(sxGMtvFEs.3"

# --- MQTT broker settings (matches src/face_realtime.py) --------------------
BROKER = "2c1d3753ae2245788f10b12911914b34.s1.eu.hivemq.cloud"
PORT = 8883  # HiveMQ Cloud enforces TLS
TOPIC = b"cecilia_vr"
USERNAME = "cecilia_vr"
PASSWORD = "Inteli@123"

# Keep client id unique; reuse if you want predictable session handling.
CLIENT_ID = b"pico-" + ubinascii.hexlify(machine.unique_id())

# On-board LED pin (works on Pico W)
led = machine.Pin("LED", machine.Pin.OUT, value=0)


def connect_wifi() -> network.WLAN:
    """Connects to Wi-Fi and waits until an IP is assigned."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.3)
    print("Wi-Fi connected:", wlan.ifconfig())
    return wlan


def mqtt_callback(topic: bytes, msg: bytes) -> None:
    """Handle incoming MQTT payloads and control the LED."""
    payload = msg.decode().strip().lower()
    print("Received:", payload)
    if "1" in payload or payload in ("liga", "on"):
        led.value(1)
    elif payload == "toggle":
        led.toggle()
    else:
        # Any payload without the digit "1" forces the LED off.
        led.value(0)


def make_client() -> MQTTClient:
    """Creates an MQTT client configured for TLS."""
    # umqtt.simple only verifies TLS minimally; SNI avoids some broker rejections.
    return MQTTClient(
        client_id=CLIENT_ID,
        server=BROKER,
        port=PORT,
        user=USERNAME,
        password=PASSWORD,
        keepalive=60,
        ssl=True,
        ssl_params={"server_hostname": BROKER},
    )


def main() -> None:
    connect_wifi()
    client = make_client()
    client.set_callback(mqtt_callback)

    while True:
        try:
            print("Connecting to MQTT broker...")
            client.connect()
            client.subscribe(TOPIC)
            print("Subscribed to", TOPIC)

            # Blocks until a message arrives; wrap in try so we can reconnect.
            while True:
                client.wait_msg()
        except OSError as exc:
            print("MQTT error:", exc)
        finally:
            try:
                client.disconnect()
            except OSError:
                pass
            print("Reconnecting in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    main()

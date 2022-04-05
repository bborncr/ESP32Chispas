# Example main file for Chispa
import chispa
import time
from machine import Pin,SoftI2C
import esp32
import network

print("Connecting to WLAN...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("ssid", "password")
while not wlan.isconnected():
    pass
print(wlan.ifconfig())

chispa = chispa.Chispa('settings.json')
clientid = chispa.get_clientid()
print(clientid)

led = Pin(25, Pin.OUT)

# Timer for temperature publishing (never block the main loop)
start_time = time.ticks_ms()

def checkwifi():
    while not wlan.isconnected():
        time.sleep_ms(500)
        print(".")
        wlan.connect()

# Returns True if interval has passed
def ready_to_publish():
    global start_time
    if time.ticks_ms() - start_time > chispa.settings['Interval']:
        start_time = time.ticks_ms()
        return True
    else:
        return False

while True:
    checkwifi()
    chispa.update() # required in main loop
    
    led.value(chispa.settings['led'])
    
    if ready_to_publish(): # If the interval has not passed then don't publish
        temperature = esp32.raw_temperature()
        payload = {'Temp': temperature, 'Humidity': 77}
        chispa.send(payload)
    
    
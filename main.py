# Example main file for Chispa
from time import ticks_ms
from machine import Pin
import network
from chispa import Chispa

print("Connecting to WLAN...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("ssid", "password")
while not wlan.isconnected():
    pass
print(wlan.ifconfig())

settings_file = 'settings.json'

chispa = Chispa(settings_file)

clientid = chispa.get_clientid()
print(clientid)

start_time = ticks_ms()

def checkwifi():
    while not wlan.isconnected():
        sleep_ms(500)
        print(".")
        wlan.connect()

# Returns True if interval has passed
def ready_to_publish():
    global start_time
    if ticks_ms() - start_time > chispa.settings['Interval']:
        start_time = ticks_ms()
        return True
    else:
        return False

while True:
    checkwifi()
    chispa.update() # required in main loop
    
    if ready_to_publish(): # If the interval has not passed then don't publish
        payload = {'Temp': 25, 'Humidity': 77}
        chispa.send(payload)
    
    
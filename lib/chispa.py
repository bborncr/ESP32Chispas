# Chispa (lite version of Sparkplug B)
#
# Topic format: 
#   <NameSpace>/<GroupID>/<MessageType>/DeviceID
#   Message Types (outgoing) - DBIRTH, DDEATH, DDATA
#   Message Types (incoming) - DCMD
#   Payload - any single object with key/values (no nested objects or lists)
#
#   Note: DeviceID is generated from the internal ESP32 Unique ID
#   
#   Settings JSON file:
#       {
#         "Topic": "Organization/Lab/", # Root topic 
#         "SSL": true, # Secure connection to broker (requieres ca.crt setup)
#         "Interval": 10000, # publishing interval
#         "led": false, # led status
#         "User": "username", # broker username
#         "Pass": "thisisapassword", # broker password
#         "Port": 8883, # MQTT broker port 1883 (non-SSL) 8883 (SSL) 
#         "Broker": "mon.crcibernetica.com" # broker URL
#        }
#
# Copyright 2022 CRCibernetica SA

from umqtt.robust import MQTTClient
import ussl
import utime as time
from machine import unique_id
import ujson

class Chispa:
    def __init__(self, file):
        self.file = file
        self.mqtt_ping_time = time.ticks_ms()
        self.clientid = self.get_clientid()
        self.settings = self.get_settings(self.file)
        self.message = {}
        self.broker = self.settings['Broker']
        self.port = self.settings['Port']
        self.user = self.settings['User']
        self.password = self.settings['Pass']
        self.ssl = self.settings['SSL']
        self.topic = self.settings['Topic']
        self.connect_to_broker()
        self.client_setup()
    
    def update(self):
        self.client.check_msg()
        if self.ready_to_ping():
            self.client.ping()
    
    # Returns True if 5 seconds has passed
    def ready_to_ping(self):
        if time.ticks_ms() - self.mqtt_ping_time > 5000:
            self.mqtt_ping_time = time.ticks_ms()
            return True
        else:
            return False
    
    # get a unique clientid from the chipid
    def get_clientid(self):
        chipid = unique_id()
        clientid = ''
        for i in chipid:
            clientid += hex(i)
        clientid = "esp32-" + clientid.replace('0x', '')
        return clientid
    
    # The settings object is the central repository
    # for the config and environmental variables
    def get_settings(self, file):
        with open(file, 'r') as f:
            settings = f.read()
            settings = ujson.loads(settings)
            return settings
    
    # Broker with user/pass and TLS
    def connect_to_broker(self):
        if self.ssl:
            with open('ca.crt', 'r') as f:
                cert = f.read()
        else:
            cert = ""

        try:
            self.client = MQTTClient(self.clientid, self.broker, self.port, user=self.user, password=self.password, ssl=self.ssl, ssl_params={'cert':cert})
            self.client.keepalive=15 # Required for Last Will and Testament
            self.set_ddeath_message()
        except Exception as e:
            print(e)
            
    def set_ddeath_message(self):
        lwt = {"status": "offline"}
        payload = ujson.dumps(lwt)
        try:
            self.client.set_last_will(self.topic + 'DDEATH/' + self.clientid, payload, retain=True)
        except Exception as e:
            print(e)
        
    def updatesettings(self, settings):
        with open(self.file, 'w') as f:
            settings = ujson.dumps(settings)
            f.write(settings)
    
    # Callback function for incoming messages
    #
    # Any key:value that exists in the settings object can be
    # updated by sending json to the DCMD topic.
    # A response with the command is sent to the DDATA topic.
    # The handling of the updated settings should be
    # performed in the main loop.
    def on_message_received(self, msg_topic, msg):
        message = ujson.loads(msg)
        for key in message.keys():
            if key in self.settings:
                self.message[key] = message[key]
                self.settings[key] = message[key]
                payload = ujson.dumps({key: message[key]})
                print(f'DCMD:{payload}')  
            else:
                print('DCMD:Unknown command{}'.format(message))
        self.updatesettings(self.settings)
        payload = ujson.dumps(self.message)
        print(f'DDATA:{payload}')
        self.client.publish(self.topic + 'DDATA/' + self.clientid, payload)
        
        
    def client_setup(self):
        self.client.reconnect() # ensures the MQTT client is connected
        self.client.set_callback(self.on_message_received)     # First set the callback function for incoming messages
        self.client.subscribe(self.topic + 'DCMD/' + self.clientid)   # then set the subscription topic DCMD
        birth = {"status": "online"}
        payload = ujson.dumps(birth)
        print("[Sending DBIRTH message]")
        self.client.publish(self.topic + 'DBIRTH/' + self.clientid, payload)
        self.client.ping()
        
    def send(self, data):
        payload = ujson.dumps(data)
        print(f'DDATA:{data}')
        self.client.publish(self.topic + 'DDATA/' + self.clientid, payload)
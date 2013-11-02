import hashlib
import logging
import threading
from serial import SerialException

from . import wrapper
from .. import keydb

__author__ = 'Matthias Uschok <dev@uschok.de>'

class SerialThread (threading.Thread):

    def __init__(self, dbfile, port, baudrate=9600):
        super(SerialThread, self).__init__()
        self.log = logging.getLogger('serial')

        # Set up serial connection
        self.log.debug('Setting up serial connnection')
        self.ser = wrapper.Serial(port, baudrate)
        try:
            self.ser.connect()
        except SerialException as e:
            self.log.error("Error setting up serial: %s", e)
            self.ser = None
            raise

        self.db = keydb.KeyDB(dbfile)

    def run(self):

        while(True):
            self.log.debug('Server started, waiting for data...')
            command = self.ser.readCommand()
            self.log.debug('Data received')
            if (command == 0x01): # Key auth
                self.log.debug('Key auth cmd received')
                self.ser.timeout_en()

                cipher = hashlib.sha256()
                keyid = self.ser.readID()
                self.log.debug('Received id %d', keyid)

                challenge = random.read(32)
                self.ser.write(challenge)
                self.log.debug('Challenge sent')
                response = self.ser.read(32)
                self.log.debug('Received response')

                keySecret, keyLastUsed, keyActive = self.db.getKeyTuple(keyid)

                if (keySecret != None):
                    key_and_challenge = bytearray()
                    for i in range(0,32):
                        a = struct.unpack('B', keySecret[i])[0]
                        b = struct.unpack('B', challenge[i])[0]
                        key_and_challenge.append( struct.pack('B', (a & b)) )

                    cipher.update(key_and_challenge)
                    key_hash = cipher.digest()

                    if (response == key_hash):
                        self.log.info('Key for id ' + keyid + ' accepted')
                        self.ser.openDoor()
                    else:
                        self.log.info('Key for id ' + keyid + ' rejected')

            elif (command == 0x02): # Door bell
                self.ser.relayDoorBell()

            cipher = None
            self.ser.timeout_dis()

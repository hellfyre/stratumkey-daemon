import os
import sys
import daemon
import lockfile
import hashlib
import struct
import threading
import argparse
import serial
import signal
import socket

import keydb
import serialwrapper

def sig_int(signal, frame):
    #TODO: maybe stop the SerialThread here?
    sys.exit(0)

signal.signal(signal.SIGINT, sig_int)

random = None
outputfile = None

class SerialThread (threading.Thread):

    def __init__(self, port, dbfile):
        # Set up serial connection
        try:
            self.ser = serialwrapper.Serial(port)
        except serial.SerialException as e:
            print "Error setting up serial:"
            print e
            sys.exit(1)

        # Set up database
        if not os.path.exists(dbfile):
            print "Database file " + dbfile + " not found."
            sys.exit(1)
        self.dbfile = dbfile

        threading.Thread.__init__(self)

    def run(self):
        self.db = keydb.KeyDB(self.dbfile)

        while(True):
            command = self.ser.readCommand()
            if (command == 0x01): # Key auth
                cipher = hashlib.sha256()
                keyid = self.ser.readID()

                challenge = random.read(32)
                self.ser.writeBytes(challenge)
                response = self.ser.readBytes(32)

                key = self.db.getKey(keyid)

                if (key != None):
                    key_and_challenge = bytearray()
                    for i in range(0,32):
                        a = struct.unpack('B', key[i])[0]
                        b = struct.unpack('B', challenge[i])[0]
                        key_and_challenge.append( struct.pack('B', (a & b)) )

                    cipher.update(key_and_challenge)
                    key_hash = cipher.digest()

                    if (response == key_hash):
                        self.ser.openDoor(outputfile)
                        self.ser.flushInput()

            elif (command == 0x02): # Door bell
                self.ser.relayDoorBell()

            cipher = None


class ControlThread (threading.Thread):

    def __init__(self, socket):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(socket)
        self.sock.listen(1)
        self.conn,self.addr = self.sock.accept()

    def run(self):
        while(True):
            data = self.conn.recv(1024)
            if not data:
                continue
            
            

def init():

    global random
    if os.path.exists('/dev/hwrng'):
        random = open('/dev/hwrng', 'rb')
    else:
        random = open('/dev/random', 'rb')

    global outputfile
    outputfile = open("/var/lib/stratumkey/foobar", 'w')
    outputfile.write("One\n")

def main_loop():
    SerialThread(args.port, args.db_file).start()
    ControlThread(args.socket).start()

def main():
    optparser = argparse.ArgumentParser(description="StratumKey daemon is responsible for auth'ing keys used to open the Space Gate")
    optparser.add_argument('--no-daemon', '-n', action='store_const', const='1', help="Don't go into daemon mode")
    optparser.add_argument('--db-file', '-d', help="The file containing the key database. Format is sqlite3", default='/var/lib/stratumkey/keydb')
    optparser.add_argument('--port', '-p', help="Serial interface to the StratumKey master", default='/dev/ttyUSB0')
    optparser.add_argument('--socket', '-s', help="The socket for stratumkey_ctl", default='/var/lib/stratumkey/sock_ctl')

    global args
    args = optparser.parse_args()

    if not args.no_daemon:
        d = daemon.DaemonContext()
        d.pidfile=lockfile.FileLock('/var/run/stratumkey.pid')
        d.working_directory='/var/lib/stratumkey'
        if not os.path.exists(d.working_directory):
            os.makedirs(d.working_directory, 0644)
        if os.path.exists(args.socket):
            os.remove(args.socket)

        d.files_preserve=[outputfile]

        with d:
            init()
            main_loop()
    else:
        init()
        main_loop()

if __name__ == "__main__":
    main()

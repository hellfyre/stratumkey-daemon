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
import pickle
from types import *

import stratumkeyd
import protocol
import keydb
import serialwrapper


def sig_int(signal, frame):
    serialThread.join()
    controlThread.join()
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
        self.dbfile = dbfile

    def run(self):
        self.db = keydb.KeyDB(self.dbfile)

        while(True):
            command = self.ser.readCommand()
            if (command == 0x01): # Key auth
                self.ser.timeout_en()
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
            self.ser.timeout_dis()


class ControlThread (threading.Thread):

    def __init__(self, socketFile, dbfile):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # Set up database
        self.dbfile = dbfile

        try:
            self.sock.bind(socketFile)
            self.sock.listen(1)
            self.conn,self.addr = self.sock.accept()
        except:
            self.sock.close()
            if os.path.exists(socketFile):
                os.remove(socketFile)
            print "ERROR socket "+ socketFile +" in use"
            sys.exit(1)

    def run(self):
        self.db = keydb.KeyDB(self.dbfile)
        print "server linstening" 
        while(True):
            d=self.conn.recv(1024)
            if not d:
                continue
            print len(d)
            data= pickle.loads(d)
            if isinstance(data, protocol.modify_command) or isinstance(data,stratumkeyd.protocol.modify_command):
                if data.command=="add":
                    self.db.addKey(data.id, str(data.key))
                    response = protocol.response(data.command,"FAILED")
                    test=self.db.getKey(data.id)
                    if test:
                        print test
                        response.result="OK"
                    self.conn.send(pickle.dumps(response))
                elif data.command == "del":
                    response = protocol.response(data.command,"NOT IMPLEMENTED")
                    self.conn.send(pickle.dumps(response))
                
            else:
                response = protocol.response(data.command,"NOT IMPLEMENTED")
                self.conn.send(pickle.dumps(response))
                print data.__class__
            self.conn,self.addr = self.sock.accept()
        print "Oops"    

    def stop(self):
        self.sock.close()

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
    global controlThread
    controlThread=ControlThread(args.socket,args.db_file)
    controlThread.start()

    global serialThread
    serialThread = SerialThread(args.port, args.db_file)
    serialThread.start()

def main():
    optparser = argparse.ArgumentParser(description="StratumKey daemon is responsible for auth'ing keys used to open the Space Gate")
    optparser.add_argument('--no-daemon', '-n', action='store_const', const='1', help="Don't go into daemon mode")
    optparser.add_argument('--db-file', '-d', help="The file containing the key database. Format is sqlite3", default='/var/lib/stratumkey/keydb')
    optparser.add_argument('--port', '-p', help="Serial interface to the StratumKey master", default='/dev/ttyUSB0')
    optparser.add_argument('--socket', '-s', help="The socket for stratumkey_ctl", default='/var/lib/stratumkey/sock_ctl')

    global args
    args = optparser.parse_args()

    if not os.path.exists(args.db_file):
        print "Database file " + args.db_file + " not found."
        sys.exit(1)

    if args.no_daemon:
        if os.path.exists(args.socket):
            os.remove(args.socket)
        try:
            print "init"
            init()
            print "loop"
            main_loop()
        except:
            os.remove(args.socket)
    else:
        d = daemon.DaemonContext()
        d.pidfile=lockfile.FileLock('/var/run/stratumkey.pid')
        d.working_directory='/var/lib/stratumkey'
        if not os.path.exists(d.working_directory):
            os.makedirs(d.working_directory, 0644)
        if os.path.exists(args.socket):
            os.remove(args.socket)
            
        
        
        d.files_preserve=[outputfile]
        with d:
            try:
                init()
                main_loop()
            except:
                os.remove(args.socket)  
        
if __name__ == "__main__":
    main()

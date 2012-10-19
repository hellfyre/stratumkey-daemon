import argparse
import daemon
import hashlib
import lockfile
import logging
import os
import pickle
import serial
import signal
import socket
import struct
import sys
import threading
from types import *

import stratumkeyd
import protocol
import keydb
import serialwrapper


def sig_int(signal, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, sig_int)

random = None
outputfile = None

class SerialThread (threading.Thread):

    def __init__(self, port, dbfile):
        super(SerialThread, self).__init__()
        self.log = logging.getLogger('main')

        # Set up serial connection
        try:
            self.log.debug('Setting up serial connnection')
            self.ser = serialwrapper.Serial(port)
        except serial.SerialException as e:
            self.log.error("Error setting up serial:")
            self.log.exception(e)
            sys.exit(1)

        self.dbfile = dbfile

    def run(self):
        self.db = keydb.KeyDB(self.dbfile)

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
                self.ser.writeBytes(challenge)
                self.log.debug('Challenge sent')
                response = self.ser.readBytes(32)
                self.log.debug('Received response')

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
                        self.log.info('Key for id ' + keyid + ' accepted')
                        self.ser.openDoor(outputfile)
                        self.ser.flushInput()
                    else:
                        self.log.info('Key for id ' + keyid + ' rejected')

            elif (command == 0x02): # Door bell
                self.ser.relayDoorBell()

            cipher = None
            self.ser.timeout_dis()


class ControlThread (threading.Thread):

    def __init__(self, socketFile, dbfile):
        super(ControlThread, self).__init__()
        self.log = logging.getLogger('main')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.db = keydb.KeyDB(dbfile)

        try:
            self.sock.bind(socketFile)
            self.sock.listen(1)
        except:
            self.sock.close()
            self.log.error("Socket "+ socketFile +" in use")
            sys.exit(1)

    def run(self):
        self.log.debug("Server listening on socket" + self.sock.getsockname())
        self.conn,self.addr = self.sock.accept()
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
        print 'Stop called..'
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

def init():

    log = logging.getLogger('main')
    global random
    if os.path.exists('/dev/hwrng'):
        log.debug('Using hardware random number generator')
        random = open('/dev/hwrng', 'rb')
    else:
        log.debug('Using software random number generator')
        random = open('/dev/random', 'rb')

    global outputfile
    outputfile = open("/var/lib/stratumkey/foobar", 'w')
    outputfile.write("One\n")
 
def main_loop():
    log = logging.getLogger('main')

    controlThread = ControlThread(args.socket,args.db_file)
    controlThread.daemon = True
    log.debug('Starting control thread...')
    controlThread.start()

    serialThread = SerialThread(args.port, args.db_file)
    serialThread.daemon = True
    log.debug('Starting serial thread...')
    serialThread.start()

    while True:
        None

def main():
    optparser = argparse.ArgumentParser(description="StratumKey daemon is responsible for auth'ing keys used to open the Space Gate")
    optparser.add_argument('--no-daemon', '-n', action='store_const', const='1', help="Don't go into daemon mode")
    optparser.add_argument('--db-file', '-d', help="The file containing the key database. Format is sqlite3", default='/var/lib/stratumkey/keydb')
    optparser.add_argument('--port', '-p', help="Serial interface to the StratumKey master", default='/dev/ttyUSB0')
    optparser.add_argument('--socket', '-s', help="The socket for stratumkey_ctl", default='/var/lib/stratumkey/sock_ctl')
    optparser.add_argument('--logfile', '-f', help="Provide a file for logging", default='/var/log/stratumkey.log')
    optparser.add_argument('--loglevel', '-l', help="Set log level to INFO, WARN or DEBUG", default='WARN')

    global args
    args = optparser.parse_args()
    
    log = logging.getLogger('main')
    
    if args.no_daemon:
        loghandler = logging.StreamHandler(sys.stdout)
        #TODO: Remove this
        args.loglevel = 'DEBUG'
    else:
        loghandler = logging.FileHandler(args.logfile)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    loghandler.setFormatter(formatter)
    log.addHandler(loghandler)
    if args.loglevel=='INFO':
        log.setLevel(logging.INFO)
    if args.loglevel=='WARN':
        log.setLevel(logging.WARN)
    if args.loglevel=='DEBUG':
        log.setLevel(logging.DEBUG)

    if not os.path.exists(args.db_file):
        print "Database file " + args.db_file + " not found."
        sys.exit(1)

    if os.path.exists(args.socket):
        os.remove(args.socket)

    if args.no_daemon:
        init()
        main_loop()
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

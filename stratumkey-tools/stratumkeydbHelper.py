'''
Created on 21.08.2012

@author: oni
'''
import stratumkeyd.keydb as keydb
import argparse
import os
import sys
import socket
import pickle
from types import *

import  stratumkeyd
from stratumkeyd import protocol 


def main():
    optparser = argparse.ArgumentParser(description="StratumKeyDB Helper")
    optparser.add_argument('--dbfile', '-f', default='/var/lib/stratumkey/keydb',help="database file")
    optparser.add_argument('--create-new', '-c', action='store_const', const='1', help="create a new database file")
    optparser.add_argument('--add', '-a',action='store_const', const='1',help="add new key")
    optparser.add_argument('--delete', '-d', action='store_const', const='1',help="delete key")
    optparser.add_argument('--keyid', '-i',help="keyID")
    optparser.add_argument('--key', '-k',help="key")
    optparser.add_argument('--socket','-s',help="The socket for stratumkey", default='/var/lib/stratumkey/sock_ctl')
    optparser.add_argument('--socket-mode', '-m', action='store_const', const='1',help="use socket mode")
    global args
    args = optparser.parse_args()
    if args.socket_mode:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(args.socket)
        if args.add:
            if args.keyid:
                key=None
                if not args.key:
                    if os.path.exists('dev/hwrng'):
                        randomsocket = open('dev/hwrng', 'rb')
                    else:
                        randomsocket = open('/dev/random', 'rb')
                    key= bytearray()
                    for x in range(0,32):
                        key.append(randomsocket.read(1))
                else:
                    key=args.key
                cmd = protocol.modify_command("add",args.keyid,key)
                sock.send(pickle.dumps(cmd))
                while True:
                    data = sock.recv(1024)
                    if not data:
                        continue
                    res = pickle.loads(data)
                    if str(res.__class__) == "protocol.response": 
                        print "Command "+res.command+ " returned " +res.result
                        if res.result == "OK":
                            print "KeyID "+args.keyid+ " added with key:"
                            for b in key:
                                sys.stdout.write(str(b))
                    else:
                        print "hmmmm"
                        print res.__class__
                    sock.close()
                    sys.exit(0)
    if not args.create_new:
        if not os.path.exists(args.dbfile):
            print "ERROR: dbfile not found, try to create a new one wite --create-new"
            sys.exit(1)
    db= keydb.KeyDB(args.dbfile)
    if args.create_new:
        db.createTable()
    if args.add:
        if args.keyid!=None:
            if args.key!=None:
                db.addKey(args.keyid, args.key)
                print "added "+ args.keyid +"with key: "+ args.key 
            else:
                if os.path.exists('dev/hwrng'):
                    randomsocket = open('dev/hwrng', 'rb')
                else:
                    randomsocket = open('/dev/random', 'rb')
                    key= bytearray()
                    for x in range(0,32):
                        key.append(randomsocket.read(1))
                    db.addKey(args.keyid, key)
                    print "added "+ args.keyid +" with key: " 
                    for b in key:
                        sys.stdout.write(str(b))
    if args.delete:
        print "not implemented"

if __name__ == '__main__':
    main()
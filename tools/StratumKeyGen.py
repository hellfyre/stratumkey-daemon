#!/usr/bin/python

import sys
import os
import argparse
import uuid
from Crypto.Cipher import AES

def main():
    optparser = argparse.ArgumentParser(description="StratumKeyGen")
    optparser.add_argument('--outputdir', '-o', help="Output directory")

    args = optparser.parse_args()

    outdir = os.path.abspath(os.path.curdir)
    if args.outputdir:
        outdir = args.outputdir
        if not os.path.isdir(outdir):
            print "\"" + outdir + "\" either doesn't exist or is not a directory."
            sys.exit(1)
    else:
        outdir = os.path.join(outdir, 'StratumKeyGen')
        try:
            os.mkdir(outdir)
        except OSError as error:
            print "Couldn't create \"" + outdir + "\": " + error.strerror
            sys.exit(1)

    uuidFile = open(os.path.join(outdir, 'uuid'), 'w')
    uuidFile.write(str(uuid.uuid4()))
    uuidFile.close()

    randomsocket = open('/dev/urandom', 'rb')

    key1file = open(os.path.join(outdir, 'key1.bare'), 'w')
    key1 = randomsocket.read(32)
    key1file.write(key1)
    key1file.close()

    key2file = open(os.path.join(outdir, 'key2'), 'w')
    key2 = randomsocket.read(32)
    key2file.write(key2)
    key2file.close()

    ivfile = open(os.path.join(outdir, 'iv'), 'w')
    iv = randomsocket.read(16)
    ivfile.write(iv)
    ivfile.close()

    cipher = AES.new(key2, AES.MODE_CFB, iv)
    key1cryptfile = open(os.path.join(outdir, 'key1.aes'), 'w')
    key1crypt = cipher.encrypt(key1)
    key1cryptfile.write(key1crypt)
    key1cryptfile.close()

if __name__ == '__main__':
    main()

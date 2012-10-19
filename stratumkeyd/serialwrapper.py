import serial
import struct
import hashlib

class Serial:
    def __init__(self, port):
        try:
            self.ser = serial.Serial(port, 9600, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, None, 0, 0, None)
        except serial.SerialException:
            raise

        self.ser.open()
        self.ser.flushInput()
        self.cipher = hashlib.sha256()

    def __del__(self):
        self.ser.close()

    def readBytes(self, count):
        arr = bytearray()
        for _ in range(count):
            arr.append(struct.unpack('B', self.ser.read(1))[0])
        return arr

    def writeBytes(self, data):
        return self.ser.write(buffer(data))

    def readCommand(self):
        cmd = struct.unpack('B', self.ser.read(1))[0]
        return cmd

    def readID(self):
        d1=struct.unpack('B', self.ser.read(1))[0]
        d2=struct.unpack('B', self.ser.read(1))[0]
        return (d1<<8) + d2

    def flushInput(self):
        self.ser.flushInput()

    def flushOutput(self):
        self.ser.flushOutput()

    def timeout_en(self):
        self.ser.timeout=0.5

    def timeout_dis(self):
        self.ser.timeout=None

    def openDoor(self):
        #self.ser.writeBytes('\x10')
        print 'Stub: open door'
        
    def relayDoorBell(self):
        print "Relaying door bell ;P"
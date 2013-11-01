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

    def read(self, count):
        return self.ser.read(count)

    def write(self, data):
        return self.ser.write(data)

    def flushInput(self):
        self.ser.flushInput()

    def flushOutput(self):
        self.ser.flushOutput()

# vim: set expandtab shiftwidth=4 tabstop=4:

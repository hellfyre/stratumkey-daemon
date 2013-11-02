import serial
import hashlib

class SerialWrapper:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE

        self.cipher = hashlib.sha256()

    def __del__(self):
        self.ser.close()

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, self.bytesize, self.parity, self.stopbits, None, 0, 0, None)
        except serial.SerialException:
            raise
        self.ser.open()
        self.ser.flushInput()

    def read(self, count):
        return self.ser.read(count)

    def write(self, data):
        return self.ser.write(data)

    def flushInput(self):
        self.ser.flushInput()

    def flushOutput(self):
        self.ser.flushOutput()

# vim: set expandtab shiftwidth=4 tabstop=4:

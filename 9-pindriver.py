# This driver implements the ESC/P standard for communicating with
# 9-pin head impact mactrix printers via an emulated parallel port.
# It has been tested against a MT81 Tally printer using a raspberrypi
# host.
# Parallel port emulation hardware was provided by the broadcomm gpio
# module and an external 8-bit gpio expander (PCF8574A) connected via
# the smbus I2c module.
#
# Author: Simone Pilon <wertyseek@gmail.com>
# Creation: 25-02-2018

import smbus            # I2c
import RPi.GPIO as gpio # GPIO
from time import sleep  # Timing
from PIL import Image   # Read images

class ParallelAdapter:
    """Driver to communicate with the printer."""
    # Define special ASCII characters.
    NUL = 0     #Null char
    SOH = 1     #Start of Heading
    STX = 2     #Start of Text
    ETX = 3     #End of Text
    EOT = 4     #End of Transmission
    ENQ = 5     #Enquiry
    ACK = 6     #Acknowledgment
    BEL = 7     #Bell
    BS = 8      #Back Space
    HT = 9      #Horizontal Tab
    LF = 10     #Line Feed
    VT = 11     #Vertical Tab
    FF = 12     #Form Feed
    CR = 13     #Carriage Return
    SO = 14     #Shift Out / X-On
    SI = 15     #Shift In / X-Off
    DLE = 16    #Data Line Escape
    DC1 = 17    #Device Control 1 (oft. XON)
    DC2 = 18    #Device Control 2
    DC3 = 19    #Device Control 3 (oft. XOFF)
    DC4 = 20    #Device Control 4
    NAK = 21    #Negative Acknowledgement
    SYN = 22    #Synchronous Idle
    ETB = 23    #End of Transmit Block
    CAN = 24    #Cancel
    EM = 25     #End of Medium
    SUB = 26    #Substitute
    ESC = 27    #Escape
    FS = 28     #File Separator
    GS = 29     #Group Separator
    RS = 30     #Record Separator
    US  = 31    #Unit Separator

    def __init__(self):
        # Define timings:
        self.i2c_delay = 0.001          # Delay between i2c comunication and valid data on device [S].
        self.strobe_duration = 0.01     # Width of the strobe active pulse.
        self.busy_polling_delay = 0.01  # Delay between polls of busy.
        # Init i2c:
        self.i2c_address = 56           # Address of GPIO expander (all address pins grounded).
        self.i2c_bus = smbus.SMBus(1)   # i2c bus connected to GPIO expander.
        # Set all ports in expander to high impedance.
        if not(self.i2c_bus.write_byte( self.i2c_address, 0b11111111) == 0):
            print("Error: Could not write to i2c device.")
        # Init GPIO:
        self.strobe = 4
        self.busy = 17
        gpio.setmode( gpio.BCM)
        gpio.setup( channel=self.strobe, direction=gpio.OUT, initial=gpio.HIGH)
        gpio.setup( channel=self.busy, direction=gpio.IN, pull_up_down=gpio.PUD_UP)

    def __del__(self):
        # reset i2c device to safe state:
        if not(self.i2c_bus.write_byte( self.i2c_address, 0b11111111) == 0):
            print("Error: Could not write to i2c device.")
        # release i2c bus
        self.i2c_bus.close()
        # clean gpio
        gpio.cleanup()
        print("Released all resources.")

    def putchar(self, *values):
        """Sends the values via the parallel bus.
    The parallel bus emulation is implemented in this function.
    values : int
        8-bit values to transmit."""
        for val in values:
            # Set parallel data bus to value:
            if not (self.i2c_bus.write_byte( self.i2c_address, val) == 0):
                print("Error: Could not write to i2c device.")
                return
            sleep( self.i2c_delay )     # Wait for valid data at gpio expander.
            # Send strobe pulse.
            gpio.output( self.probe, gpio.LOW)
            sleep( self.strobe_duration)
            gpio.output( self.probe, gpio.HIGH)
            # Wait for the printer to be ready again.
            while ( gpio.input( self.busy) == gpio.HIGH):
                sleep( self.busy_polling_delay)

    def write_string(self, message):
        """Writes a string message on parallel bus.
    The message will not be printed immediately unless it is
    terminated by a CR.
    message : string"""
       message = list(message)
        for char in message:
            char = ord(char)
            self.putchar(char)

    def writeln(self, message):
        """Writes a string message, CR signal is appended automatically.
    message : string"""
        self.write_string(message)
        self.putchar( self.CR)

    def write_file(self, filename):
        """Writes characters from a file.
    filename : string
        Path to file."""
        with open( file, "r") as source:
            for line in source:
                self.print(line)

    def set_bold(self):
        """Select bold font."""
        self.putchar( self.ESC, ord('E'))

    def unset_bold(self):
        """Cancel bold font."""
        self.puchar( self.ESC, ord('F'))

    def set_italics(self):
        """Select italics font."""
        self.putchar( self.ESC, ord('4'))

    def unset_italics(self):
        """Cancel italics font."""
        self.putchar( self.ESC, ord('5'))

    def write_image(self, filename, m=5):
        """Writes pixel values from an image file.
    filename : string
        Path to image file
    m : int
        printing mode as defined in ESC/P standard."""
        bytes_per_column = 1
        if (m > 7):
            bytes_per_column = 3
        if (m > 40):
            bytes_per_column = 6
        with Image.open( filename) as image:
            cols = image.width
            rows = image.height/(8*bytes_per_column) + 1
            if (rows > 1):
                #Adjust line spacing
                self.putchar( self.ESC, ord('3'), 24)
            self.putchar( self.ESC, ord('*'), m, cols%256, cols/256)
            for row in range(0, rows):
                for col in range(0, cols):
                    for i in range(0, bytes_per_column):
                        val = 0
                        for j in range(0, 8):
                            pixel = image.getpixel( ( row, col*8*bytes_per_column + 8*i + j))
                            if ( pixel[0] == 0):
                                val += 2**j
                        self.putchar( val)
            if (rows > 1):
                #Reset line spacing to default
                self.putchar( self.ESC, ord('2'))

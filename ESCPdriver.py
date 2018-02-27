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
        self.i2c_delay = 0.0001          # Delay between i2c comunication and valid data on device [S].
        self.strobe_duration = 0.001     # Width of the strobe active pulse.
        self.busy_polling_delay = 0.001  # Delay between polls of busy.
        # Define character sequences:
        self.NL = ( self.CR,)           # New Line (default is hardware autofeed enabled)
        # Init i2c:
        self.i2c_address = 56           # Address of GPIO expander (all address pins grounded).
        self.i2c_bus = smbus.SMBus(1)   # i2c bus connected to GPIO expander.
        # Set all ports in expander to high impedance.
        err = self.i2c_bus.write_byte( self.i2c_address, 0b11111111)
        if not(err == None):
            print("Error " +str(err)+ " : Could not write to i2c device.")
        # Init GPIO:
        self.strobe = 4
        self.busy = 17
        gpio.setmode( gpio.BCM)
        gpio.setup( channel=self.strobe, direction=gpio.OUT, initial=gpio.HIGH)
        gpio.setup( channel=self.busy, direction=gpio.IN, pull_up_down=gpio.PUD_UP)

    def __del__(self):
        # reset i2c device to safe state:
        err = self.i2c_bus.write_byte( self.i2c_address, 0b11111111)
        if not(err == None):
            print("Error " +str(err)+ " : Could not write to i2c device.")
        # release i2c bus
        self.i2c_bus.close()
        # clean gpio
        gpio.cleanup()
        print("Released all resources.")

    def putchar(self, *values):
        """Sends the values via the parallel bus.
    The parallel bus emulation is implemented mostly in this function.
    values : int
        8-bit values to transmit."""
        for val in values:
            # Set parallel data bus to value:
            err = self.i2c_bus.write_byte( self.i2c_address, val)
            if not(err == None):
                print("Error " +str(err)+ " : Could not write to i2c device.")
                return
            sleep( self.i2c_delay )     # Wait for valid data at gpio expander.
            # Send strobe pulse.
            gpio.output( self.strobe, gpio.LOW)
            sleep( self.strobe_duration)
            gpio.output( self.strobe, gpio.HIGH)
            # Wait for the printer to be ready again.
            sleep( self.busy_polling_delay)
            while ( gpio.input( self.busy) == gpio.HIGH):
                sleep( self.busy_polling_delay)

    def write_string(self, message):
        """Writes a string message on parallel bus.
    The message will not be printed immediately unless it is
    terminated by a newline.
    message : string"""
        message = list(message)
        for char in message:
            char = ord(char)
            self.putchar(char)

    def writeln(self, message):
        """Writes a string message, newline signal is appended automatically.
    message : string"""
        self.write_string(message)
        self.putchar( *(self.NL))

    def write_file(self, filename):
        """Writes characters from a file.
    filename : string
        Path to file."""
        with open( filename, "r") as source:
            for line in source:
                self.write_string(line)

    def set_right_margin(self, n):
        """Set the right margin to n number of columns
    in the current character pitch.
    n : int
        1 <= n <= 255"""
        self.putchar( self.ESC, ord('Q'), n)

    def set_left_margin(self, n):
        """Set the left margin to n number of columns
    in the current character pitch.
    n : int
        1 <= n <= 255"""
        self.putchar( self.ESC, ord('l'), n)

    def set_page_length_lines(self, n):
        """Set the page length to n lines in the current
    line spacing.
    n : int
        1 <= n <= 127"""
        self.putchar( self.ESC, ord('C'), n)

    def set_page_length_inches(self, n):
        """Set the page length to n inches.
    n : int
        1 <= n <= 22"""
        self.putchar( self.ESC, ord('C'), self.NUL, n)

    def set_bottom_margin(self, n):
        """Set the bottom margin on continuous paper to n lines
    from the top-of-form position on the next page.
    n : int
        1 <= n <= 127"""
        self.putchar( self.ESC, ord('N'), n)

    def unset_vertical_margin(self):
        """Cancel top and bottom margin setting
    (Cancel skip-over-perforation)."""
        self.putchar( self.ESC, ord('O'))

    def set_autofeed_method(self, method):
        """Set autofeed.
    method : string
        'hard' = Grounds AUTOF pin, the printer will
                perform a LF at every CR.
                If '\\n' is expanded to CR+LF, line spacing will be double.
        'soft' = The adapter appends LF to CR when calling new_line().
                If '\\n' is expanded to CR only, the printer won't feed a new line.
        'none' = LF has to be explicitly written to advance lines."""
        if (method == 'hard'):
            self.NL = ( self.CR,)
            #TODO self.autofeed to LOW
        elif (method == 'soft'):
            self.NL = ( self.CR, self.LF)
            #TODO self.autofeed to HIGH
        elif (method == 'none'):
            self.NL = ( self.CR,)
            #TODO self.autofeed to HIGH
        else:
            print("Error: "+method+" is not a valid method.")

    def reverse_paper_feed(self, n):
        """Reverse feed paper (negative y direction) by n/216 inches.
    n : int
        0 <= n <= 255"""
        self.putchar( self.ESC, ord('j'), n)

    def set_immediate_print_mode(self):
        """Sets character by character printing."""
        self.putchar( self.ESC, ord('i'), 1)

    def unset_immediate_print_mode(self):
        """Sets line by line printing."""
        self.putchar( self.ESC, ord('i'), 0)

    def set_double_height(self):
        """Turns on double-height printing."""
        self.putchar( self.ESC, ord('w'), 1)

    def unset_double_height(self):
        """Turns off double-height printing."""
        self.putchar( self.ESC, ord('w'), 0)

    def set_line_spacing(self, n):
        """Set line spacing to n/216 inches.
    n : int
        0 <= n <= 255"""
        self.putchar( self.ESC, ord('3'), n)

    def unset_line_spacing(self):
        """Set line spacing to default (1/6 inch)."""
        self.putchar( self.ESC, ord('2'))

    def assign_char_table(self, d1, d2, d3):
        """Assign char table specified by d2 and d3 to d1.
    d1 : int
        d1 = 0 Default char table (italics)
        d1 = 1 Symbol char table
    d2, d3 : int
        0 <= d2, d3 <= 255
        See ESC/P specification for available tables."""
        self.putchar( self.ESC, ord('('), ord('t'), 3, 0, d1, d2, d3)

    def set_symbol_char_table(self):
        """Select the symbol char table."""
        self.putchar( self.ESC, ord('t'), 1)

    def unset_symbol_char_table(self):
        """Select the default char table (italics)."""
        self.putchar( self.ESC, ord('t'), 0)

    def set_NLQ(self):
        """Select Near Letter Quality printing."""
        self.putchar( self.ESC , ord('x'), 1)

    def unset_NLQ(self):
        """Select draft quality printing."""
        self.putchar( self.ESC , ord('x'), 0)

    def set_typeface_roman(self):
        """Set typeface font for NLQ printing to Roman (default)."""
        self.putchar( self.ESC, ord('k'), 0)

    def set_typeface_sansserif(self):
        """Set typeface font for NLQ printing to Sans serif."""
        self.putchar( self.ESC, ord('k'), 1)

    def set_pitch_10cpi(self):
        """Set pitch to 10-cpi (default)."""
        self.putchar( self.ESC, ord('P'))

    def set_pitch_12cpi(self):
        """Set pitch to 12-cpi."""
        self.putchar( self.ESC, ord('M'))

    def set_pitch_15cpi(self):
        """Set pitch to 15-cpi."""
        self.putchar( self.ESC, ord('g'))

    def set_pitch_proportional(self):
        """Set pitch to proportional spacing."""
        self.putchar( self.ESC, ord('p'), 1)

    def unset_pitch_proportional(self):
        """Set pitch to last fixed value set."""
        self.putchar( self.ESC, ord('p'), 0)

    def set_interchar_space(self, n):
        """Increases the space between characters by n/120 inches.
        (default n = 0)
        n : int
            0 <= n <= 127"""
        self.putchar( self.ESC, 32, n)

    def set_bold(self):
        """Select bold font."""
        self.putchar( self.ESC, ord('E'))

    def unset_bold(self):
        """Cancel bold font."""
        self.putchar( self.ESC, ord('F'))

    def set_italics(self):
        """Select italics font."""
        self.putchar( self.ESC, ord('4'))

    def unset_italics(self):
        """Cancel italics font."""
        self.putchar( self.ESC, ord('5'))

    def set_double_strike(self):
        """Each dot is printed twice with an offset to make characters bold."""
        self.putchar( self.ESC, ord('G'))

    def unset_double_strike(self):
        """Cancel double strike printing."""
        self.putchar( self.ESC, ord('H'))

    def set_underline(self):
        """Print a line below characters."""
        self.putchar( self.ESC, ord('-'), 1)

    def unset_underline(self):
        """Cancel underline."""
        self.putchar( self.ESC, ord('-'), 0)

    def set_superscript(self):
        """Set superscript layout."""
        self.putchar( self.ESC, ord('S'), 0)

    def set_subscript(self):
        """Set subscript layout."""
        self.putchar( self.ESC, ord('S'), 1)

    def unset_script(self):
        """Cancel super or subscript commands."""
        self.putchar( self.ESC, ord('T'))

    def beep(self):
        """Beeps the printer for 1/10 of a second."""
        self.putchar( self.BEL)

    def write_image(self, filename):
        """Writes pixel values from an image file.
    filename : string
        Path to image file"""
        with Image.open( filename) as image:
            cols = image.width
            rows = image.height/8 + 1
            if (rows > 1):
                self.set_line_spacing( 24)  # This spacing matches the height of the print head.
            for row in range(0, rows):
                self.putchar( self.ESC, ord('*'), 5, cols%256, cols/256)
                for col in range(0, cols):
                    val = 0
                    for i in range(0, 8):
                        xy = ( col, row*8 + i)
                        if ( xy[1] < image.height):
                            pixel = image.getpixel( xy)
                            try:
                                if ( pixel[0] == 0):
                                    val += 2**(7-i)
                            except TypeError:
                                if ( pixel == 0):
                                    val += 2**(7-i)
                    self.putchar( val)
                self.putchar( *(self.NL))
            if (rows > 1):
                self.unset_line_spacing()
    

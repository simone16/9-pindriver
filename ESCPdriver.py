# This driver implements the ESC/P standard for communicating with
# 9-pin head impact mactrix printers via an emulated parallel port.
# It has been tested against a MT81 Tally printer using a raspberrypi
# host.
# Parallel port emulation hardware was provided by an external 16-bit 
# gpio expander (MCP23017) connected via the smbus I2c module.
# The parallel SelectIn pin (number 17 on the DB25 connector) is hardware
# grounded.
# Older versions used the PCF8574 (8-bit expander) plus some GPIO pins
# from the raspberry broadcomm module.
# If you want to use different hardware, see the putchar() function,
# __init__(), set_autofeed_method() and status() will require modifiction too.
#
# Author: Simone Pilon <wertyseek@gmail.com>
# Creation: 25-02-2018

from smbus import SMBus # I2c
from time import sleep  # Timing
from PIL import Image   # Read images

class ParallelAdapter:
    """A driver to communicate with 9-pin dot matrix printers.
    The 9-pin ESC/P standard is implemented."""
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

    # Define GPIO pins ( PORTA is directly connected to parallel data bus D0-D7)
    # so only the B index is required.
    _STROBE = 0     #OUT, Active LOW
    _ACK = 1        #IN,  Active HIGH
    _BUSY = 2       #IN,  Active HIGH
    _PAPEREND = 3   #IN,  Active HIGH
    _SELECT = 4     #IN,  Active HIGH
    _AUTOFEED = 5   #OUT, Active LOW
    _ERROR = 6      #IN,  Active LOW
    _INIT = 7       #OUT, Active LOW
    #_SELECTIN = None #OUT, Active LOW

    def __init__(self):
        # Define timings:
        self.i2c_delay = 0.001         # Delay between i2c comunication and valid data on device (max. 3.45uS by datasheet) [S].
        self.strobe_duration = 0.001     # Width of the strobe active pulse.
        self.busy_polling_delay = 0.001  # Delay between polls of busy.
        # Define character sequences:
        self.NL = ( self.CR,)            # New Line (default is hardware autofeed enabled)
        self._hard_autofeed = True       # hardware autofeed enabled
        # Init external circuit:
        self.gpio = MCP23017()
        self.gpio.write( self.gpio.IODIRA, 0)   # PORTA all output
        io = 2**self._ACK + 2**self._BUSY + 2**self._PAPEREND + 2**self._SELECT + 2**self._ERROR
        self.gpio.write( self.gpio.IODIRB, io)  # Set the input pins

    def putchar(self, *values):
        """Sends the values via the parallel bus.
    The parallel bus emulation is implemented mostly in this function.
    values : int
        8-bit values to transmit."""
        for val in values:
            error = True
            while error:
                # Set parallel data bus to value:
                self.gpio.write( self.gpio.GPIOA, val)
                sleep( self.i2c_delay )     # Wait for valid data at gpio expander.
                # Send strobe pulse.
                valB = 0b11111111
                if ( self._hard_autofeed):
                    valB ^= (0b1 << self._AUTOFEED)
                self.gpio.write( self.gpio.GPIOB, valB)
                sleep( self.strobe_duration)
                valB ^= (0b1 << self._STROBE)
                self.gpio.write( self.gpio.GPIOB, valB)
                # Wait for the printer to be ready again.
                ready = False
                while (not ready):
                    sleep( self.busy_polling_delay)
                    stt = self.status()
                    if ( (stt['PAPEREND'] == 1) or (stt['SELECT'] == 0) or (stt['ERROR'] == 0)):
                        print("Error(s) encountered by the printer:")
                        if (stt['PAPEREND'] == 1):
                            print("Out of paper.")
                        if (stt['SELECT'] == 0):
                            print("Printer not selected.")
                        if (stt['ERROR'] == 0):
                            print("Printer error (maybe not online?).")
                        action = input("Would you like to resume printing? (y/n):")
                        if (action == 'n'):
                            raise KeyboardInterrupt
                        else:
                            break
                    if ( (stt['BUSY'] == 0) and (stt['ACK'] == 1)):
                        ready = True
                        error = False

    def status(self):
        """Returns the status of the printer by reading the
    ACK, BUSY, PAPEREND, SELECT and ERROR pins."""
        valB = self.gpio.read( self.gpio.GPIOB)
        stt = {}
        stt['ACK'] = (valB >> self._ACK)%2
        stt['BUSY'] = (valB >> self._BUSY)%2
        stt['PAPEREND'] = (valB >> self._PAPEREND)%2
        stt['SELECT'] = (valB >> self._SELECT)%2
        stt['ERROR'] = (valB >> self._ERROR)%2
        return stt

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

    def set_autofeed_method(self, method):
        """Set autofeed.
    method : string
        'hard' = Grounds AUTOF pin, the printer will
                perform a LF at every CR.
                If '\\n' is expanded to CR+LF, line spacing will be double.
                N.B. If the program exits before printing is complete,
                the AUTOF pin will float and the printer will misbehave.
        'soft' = The adapter appends LF to CR when calling writeln() and write_image().
                If '\\n' is expanded to CR only, the printer won't feed a new line.
        'none' = LF has to be explicitly written to advance lines."""
        if (method == 'hard'):
            self.NL = ( self.CR,)
            self._hard_autofeed = True
        elif (method == 'soft'):
            self.NL = ( self.CR, self.LF)
            self._hard_autofeed = False
        elif (method == 'none'):
            self.NL = ( self.CR,)
            self._hard_autofeed = False
        else:
            print("Error: "+method+" is not a valid method.")

    def set_abs_hor_pos(self, n):
        """Set absolute horizontal print position to n in 1/60inch units
    from the left margin.
    n : int
        0 <= n <= 32767"""
        self.putchar( self.ESC, ord('$'), n%256, n/256)

    def set_rel_hor_pos(self, n):
        """Set relative horizontal print position to n in 1/120inch units.
    n : signed int
        -16384 <= n <= 16384"""
        nl = 0
        nh = 0
        if (n < 0):
            nl = 32768 - ((-n)%256)
            nh = 32768 - ((-n)/256)
        else:
            nl = n%256
            nh = n/256
        self.putchar( self.ESC, ord('\\'), nl, nh)

    def paper_feed(self, n):
        """Advance print position vertically by n/216 inches.
    n : int
        0 <= n <= 255"""
        self.putchar( self.ESC, ord('J'), n)

    def hor_skip(self, n):
        """Prints n spaces.
    n : int
        0 <= n <= 127"""
        self.putchar( self.ESC, ord('f'), 0, n)

    def ver_skip(self, n):
        """Perform n LFs and a CR.
    n : int
        0 <= n <= 127"""
        self.putchar( self.ESC, ord('f'), 1, n)

    def set_line_spacing(self, n):
        """Set line spacing to n/216 inches.
    n : int
        0 <= n <= 255"""
        self.putchar( self.ESC, ord('3'), n)

    def set_one8_line_spacing(self):
        """Set line spacing to 1/8 inch."""
        self.putchar( self.ESC, ord('0'))

    def unset_line_spacing(self):
        """Set line spacing to default (1/6 inch)."""
        self.putchar( self.ESC, ord('2'))

    def set_hor_tabs(self, *n):
        """Set the position of consecutive tabs at n characters from left margin.
    n : int
        1 <= n <= 255, up to 32 tabs."""
        n = list(n)
        n.sort()
        self.putchar( self.ESC, ord('D'), *n)
        self.putchar( self.NUL)

    def set_ver_tabs(self, *n):
        """Set the position of consecutive vertical tabs at n lines from top of form.
    n : int
        1 <= n <= 255, up to 16 tabs."""
        n = list(n)
        n.sort()
        self.putchar( self.ESC, ord('B'), *n)
        self.putchar( self.NUL)

    def set_hor_tab_increment(self, n):
        """Set tabs every n characters in the current pitch.
    n : int
        1 <= n <= 21, 25, 36 for 10cpi, 12cpi, condensed."""
        self.putchar( self.ESC, ord('e'), 0, n)

    def set_ver_tab_increment(self, n):
        """Set vertical tabs every n lines.
    n : int
        1 <= n <= 127"""
        self.putchar( self.ESC, ord('e'), 1, n)

    def set_justification(self, justification):
        """Set justification according to value.
    justification : string
        'left' = flush left
        'right' = flush right
        'center' = centered
        'full' = full justification"""
        n = 0
        if ( justification == 'left'):
            pass
        elif ( justification == 'right'):
            n = 2
        elif ( justification == 'center'):
            n = 1
        elif ( justification == 'full'):
            n = 3
        else:
            print('Error: '+justification+" invalid justification value.")
            return
        self.putchar( self.ESC, ord('a'), n)

    def reverse_paper_feed(self, n):
        """Reverse feed paper (negative y direction) by n/216 inches.
    n : int
        0 <= n <= 255"""
        self.putchar( self.ESC, ord('j'), n)

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

    def set_international_charset(self, n):
        """Set the char table to one of the following:
    n : int
        n = 0 USA
            1 France
            2 Germany
            3 United Kingdom
            4 Denmark I
            5 Sweden
            6 Italy
            7 Spain I
            8 Japan (English)
            9 Norway
            10 Denmark II
            11 Spain II
            12 Latin America"""
        self.putchar( self.ESC, ord('R'), n)

    def define_draft_char(self, start_code, *glyphs):
        """Define custom characters in device RAM memory.
    start_code : int
        ASCII code to assign to first glyph defined, the code increases
        by one for each additional gliph provided.
    glyphs : ParallelAdapter.Glyph
        Define glyphs data."""
        end_code = start_code + len(glyphs) - 1
        self.putchar( self.ESC, ord('&'), self.NUL, start_code, end_code)
        for glyph in glyphs:
            self.putchar( glyph._a, *(glyph.data))

    def define_NLQ_char(self, start_code, *glyphs):
        """Define custom characters in device RAM memory.
    start_code : int
        ASCII code to assign to first glyph defined, the code increases
        by one for each additional gliph provided.
    glyphs : ParallelAdapter.Glyph
        Define glyphs data."""
        end_code = start_code + len(glyphs) - 1
        self.putchar( self.ESC, ord('&'), self.NUL, start_code, end_code, 0)
        for glyph in glyphs:
            self.putchar( len(glyph.data)/3, 0, *(glyph.data))

    def roman_to_RAM(self):
        """Copies the roman charset to the RAM memory of the device."""
        self.putchar( self.ESC, ord(':'), self.NUL, 0, 0)

    def sansserif_to_RAM(self):
        """Copies the sans serif charset to the RAM memory of the device."""
        self.putchar( self.ESC, ord(':'), self.NUL, 1, 0)

    def set_RAM_char_table(self):
        """Set the source of the current char table to device's RAM."""
        self.putchar( self.ESC, ord('%'), 1)

    def unset_RAM_char_table(self):
        """Set the source of the current char table to device's ROM (default)."""
        self.putchar( self.ESC, ord('%'), 0)

    class Glyph:
        """Create objects of this class to define custom characters as
    list of 8 bit values (columns from left to right) with LSB at the bottom.
    A bit value of 1 is a black pixel."""
        def __init__(self):
            self.data = []
            self._a = 1

        def set_draft(self, before, after, upper):
            """Set the glyph as draft type.
        before : int
            0 to 7, number of empty columns before char in proportional mode.
        after : int
            1 to 11, number of empty columns after char in proportional mode.
        upper : bool
            use the upper 8 pins of the head (default is bottom pins)."""
            self._a = after
            if (before == 0):
                pass
            elif( before == 1):
                self._a += 16
            elif( before == 2):
                self._a += 32
            elif( before == 3):
                self._a += 48
            elif( before == 4):
                self._a += 64
            elif( before == 5):
                self._a += 80
            elif( before == 6):
                self._a += 96
            else:
                self._a += 112
            if (upper):
                self._a += 128

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

    def set_condensed(self):
        """Increases the pitch depending on the value set."""
        self.putchar( self.SI)

    def unset_condensed(self):
        """Restores the normal pitch."""
        self.putchar( self.DC2)

    def set_double_width(self):
        """Select double width mode. All characters and
    spaces are twice as wide."""
        self.putchar( self.ESC, ord('W'), 1)

    def unset_double_width(self):
        """Cancel double width printing."""
        self.putchar( self.ESC, ord('W'), 0)

    def set_double_height(self):
        """Turns on double-height printing."""
        self.putchar( self.ESC, ord('w'), 1)

    def unset_double_height(self):
        """Turns off double-height printing."""
        self.putchar( self.ESC, ord('w'), 0)

    def set_print_control_codes(self):
        """Treat codes 0-6, 16, 17, 21-23, 25, 26, 28-31, and 128-159 as
    printable characters (by default they are commands).
    N.B. the default char table does not define gliphs for these codes
    and the command is ignored."""
        self.putchar( self.ESC, ord('I'), 1)

    def unset_print_control_codes(self):
        """Treat control codes as codes (default)."""
        self.putchar( self.ESC, ord('I'), 0)

    def set_print_upper_control_codes(self):
        """Treat codes from 128 to 159 as printable characters.
        N.B. the default char table does not define gliphs for these codes
    and the command is ignored."""
        self.putchar( self.ESC, ord('6'))

    def unset_print_upper_control_codes(self):
        """Treat control codes 128 to 159 as codes (default)."""
        self.putchar( self.ESC, ord('7'))

    def beep(self):
        """Beeps the printer for 1/10 of a second."""
        self.putchar( self.BEL)

    def reset_printer(self):
        """Reset printer settings to default.
    Not all settings are affected."""
        self.putchar( self.ESC, ord('@'))

    def reset_hard(self):
        """Reset printer settings to default.
    Uses the RESET pin on the parallel port."""
        valB = 0b11111111
        if ( self._hard_autofeed):
                valB ^= (0b1 << self._AUTOFEED)
        self.gpio.write( self.gpio.GPIOB, valB ^ (0b1 << self._INIT))
        sleep(self.strobe_duration)
        self.gpio.write( self.gpio.GPIOB, valB)
        self.putchar(ord(' '))  # Wait for the printer to be ready.

    def set_immediate_print_mode(self):
        """Sets character by character printing."""
        self.putchar( self.ESC, ord('i'), 1)

    def unset_immediate_print_mode(self):
        """Sets line by line printing."""
        self.putchar( self.ESC, ord('i'), 0)

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
                            pixel = 0
                            try:
                                pixel = image.getpixel( xy)
                            except:
                                pass
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
    
class MCP23017:
    """Provide helpful values and functions to communicate
    with the external MCP23017 device."""

    # register addresses:
    
    @property
    def IODIRA(self):
        return self._IODIRA[self._BANK]
    
    @property
    def IODIRB(self):
        return self._IODIRB[self._BANK]

    @property
    def IPOLA(self):
        return self._IPOLA[self._BANK]

    @property
    def IPOLB(self):
        return self._IPOLB[self._BANK]

    @property
    def GPINTENA(self):
        return self._GPINTENA[self._BANK]

    @property
    def GPINTENB(self):
        return self._GPINTENB[self._BANK]

    @property
    def DEFVALA(self):
        return self._DEFVALA[self._BANK]

    @property
    def DEFVALB(self):
        return self._DEFVALB[self._BANK]

    @property
    def INTCONA(self):
        return self._INTCONA[self._BANK]

    @property
    def DEFVALB(self):
        return self._DEFVALB[self._BANK]

    @property
    def INTCONA(self):
        return self._INTCONA[self._BANK]

    @property
    def INTCONB(self):
        return self._INTCONB[self._BANK]

    @property
    def IOCON(self):
        return self._IOCON[self._BANK]

    @property
    def GPPUA(self):
        return self._GPPUA[self._BANK]

    @property
    def GPPUB(self):
        return self._GPPUB[self._BANK]

    @property
    def INTFA(self):
        return self._INTFA[self._BANK]

    @property
    def INTFB(self):
        return self._INTFB[self._BANK]

    @property
    def INTCAPA(self):
        return self._INTCAPA[self._BANK]

    @property
    def INTCAPB(self):
        return self._INTCAPB[self._BANK]

    @property
    def GPIOA(self):
        return self._GPIOA[self._BANK]

    @property
    def GPIOB(self):
        return self._GPIOB[self._BANK]

    @property
    def OLATA(self):
        return self._OLATA[self._BANK]

    @property
    def OLATB(self):
        return self._OLATB[self._BANK]

    # Internal registers addresses for IOCON.BANK = 0 and IOCON.BANK = 1
    _IODIRA = (0, 0)
    _IODIRB = (1, 16)
    _IPOLA = (2, 1)
    _IPOLB = (3, 17)
    _GPINTENA = (4, 2)
    _GPINTENB = (5, 18)
    _DEFVALA = (6, 3)
    _DEFVALB = (7, 19)
    _INTCONA = (8, 4)
    _INTCONB = (9, 20)
    _IOCON = (10, 5)
    _GPPUA = (12, 6)
    _GPPUB = (13, 22)
    _INTFA = (14, 7)
    _INTFB = (15, 23)
    _INTCAPA = (16, 8)
    _INTCAPB = (17,24)
    _GPIOA = (18, 9)
    _GPIOB = (19, 25)
    _OLATA = (20, 10)
    _OLATB = (21, 26)

    def __init__(self, address = 32):
        """The device is assumed to be in the POR/Reset state."""
        self.address = address
        self._BANK = 0
        self.i2c_bus = SMBus(1)

    def __del__(self):
        """The device is left in a safe state (all ports are high impedance)."""
        self.write( self.IODIRB, 0b11111111)
        self.write( self.IODIRA, 0b11111111)
        self.i2c_bus.close()
        print("Closed i2c bus.")
        
    def write(self, register, value):
        """Writes value to device register.
    register : int
        8 bit internal address of the device register.
        All addresses are defined by this class.
    value : int
        8 bit value to assign to register."""
        err = self.i2c_bus.write_byte_data( self.address, register, value)
        if not (err == None):
            print("SMBus error "+str(err)+".")

    def read(self, register):
        """Read  value from device register.
    register : int
        8 bit internal address of the device register.
        All addresses are defined by this class.
    return : int
        8 bit value read from register."""
        return self.i2c_bus.read_byte_data( self.address, register)

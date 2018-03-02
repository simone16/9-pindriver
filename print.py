# -*- coding: utf-8 -*-
# This script prints a text file using the ESCPdriver library.
# The input file is provided as first command line argument, 
# if no argument is given, the stdin is read instead.
# Basic markdown syntax is supported for the input file (see 
# markdown_specification file within this package).
#
# Author: Simone Pilon <wertyseek@gmail.com>

import sys      # cmdline arguments
import fileinput# read stdin
import ESCPdriver#write to printer

# status variables:
emphasis = False
strong = False
olist_index = 0         # Last index of numbered list
verbatim = False        # verbatim

# Initialize interface:
pa = ESCPdriver.ParallelAdapter()
pa.reset_printer()
pa.set_right_margin(65)
pa.set_page_length_inches(12)
pa.set_bottom_margin(4)
pa.set_symbol_char_table()
pa.set_autofeed_method( "soft")
pa.set_pitch_12cpi()

# Line parsing block:
def readline( line):
    global emphasis
    global strong
    global olist_index
    global verbatim
    global pa
    line = list( line)
    i = 0
    if ( line[i] == '1' and line[i+1] == '.'):
            olist_index +=1
            i += 1
            pa.write_string( str(olist_index))
    elif not(line[i] == ' ' or line[i] == '    '):
            olist_index = 0
    while (i < len(line)):
        if ( line[i] == '\\'):
            # Ignore and print next char without interpretation
            i += 1
            #pa.write_string( line[i])
            pa.write_string( line[i])
        elif ( line[i] == '`'):
            # Toggle verbatim
            if (verbatim):
                verbatim = False
            else:
                verbatim = True
        elif (verbatim):
            # print without interpretation
            pa.write_string( line[i])
        elif ( line[i] == '#'):
            level = 1
            while ( line[i+level] == '#'):
                level += 1
            if (level == 1):
                pa.set_pitch_10cpi()
                pa.set_double_height()
                pa.set_double_width()
                pa.set_line_spacing(60)
                pa.write_string( "".join(line[i+level:]))
                pa.unset_double_height()
                pa.unset_double_width()
                pa.unset_line_spacing()
                pa.set_pitch_12cpi()
            elif (level == 2):
                pa.set_pitch_10cpi()
                pa.set_double_height()
                pa.set_line_spacing(60)
                pa.write_string( "".join(line[i+level:]))
                pa.unset_double_height()
                pa.unset_line_spacing()
                pa.set_pitch_12cpi()
            elif (level == 3):
                pa.set_pitch_10cpi()
                pa.set_bold()
                pa.write_string( "".join(line[i+level:]))
                pa.unset_bold()
                pa.set_pitch_12cpi()
            else:
                pa.set_pitch_10cpi()
                pa.write_string( "".join(line[i+level:]))
                pa.set_pitch_12cpi()
            i += level - 1
            olist_index = 0
            return
        elif ( line[i] == '-' and line[i+1] == '-'
                and line[i+2] == '-' and line[i+3] == '-'):
            pa.putchar(*([196]*65))
            olist_index = 0
            return
        elif ( line[i] == '=' and line[i+1] == '='
                and line[i+2] == '=' and line[i+3] == '='):
            pa.putchar(*([205]*65))
            olist_index = 0
            return
        elif ( line[i] == '+' or line[i] == '-'):
            pa.putchar(249)
            olist_index = 0
        elif ( line[i] == '*'):
            if ( line[i+1] == '*'):
                if ( strong):
                    strong = False
                    pa.unset_bold()
                else:
                    strong = True
                    pa.set_bold()
                i += 1
            else:
                if (emphasis):
                    emphasis = False
                    pa.unset_italics()
                else:
                    emphasis = True
                    pa.set_italics()
        elif ( line[i] == '_'):
            if ( line[i+1] == '_'):
                if ( strong):
                    strong = False
                    pa.unset_bold()
                else:
                    strong = True
                    pa.set_bold()
                i += 1
            else:
                if (emphasis):
                    emphasis = False
                    pa.unset_italics()
                else:
                    emphasis = True
                    pa.set_italics()
        elif ( line[i] == '!' and line[i+1] == '['):
            j = i
            while not( line[j] == ']'):
                j += 1
            alt_text = line[i+2:j]
            i = j
            while not( line[i] == '('):
                i += 1
            j = i
            while not( line[j] == ')'):
                j += 1
            path = line[i+1:j]
            i = j+1
            if not(i == 0):
                pa.write_string("\n")
            try:
                pa.write_image("".join(path))
            except:
                pa.writeln("".join(alt_text))
        else:
            pa.write_string( line[i])
        i += 1

# Input reading block:
if ( len(sys.argv) >= 2):
    #try:
    with open( sys.argv[1], 'r') as infile:
        for line in infile:
            readline( line)
    #except:
     #   print("Error: could not open "+ sys.argv[1] + ".")
else:
    for line in fileinput.input():
        readline( line)


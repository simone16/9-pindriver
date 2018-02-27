# This script provides an example of usage of the ESC/P driver.
# Part of the wikipedia page on the Wittig reaction is printed.
#
# Author: Simone Pilon <wertyseek@gmail.com>

from ESCPdriver import ParallelAdapter

pa = ParallelAdapter()

pa.set_left_margin(0)
pa.set_right_margin(65)
linewidth = 65

pa.set_double_height()
pa.set_line_spacing(60)
pa.writeln("Wittig reaction")
pa.unset_line_spacing()
pa.unset_double_height()
pa.set_underline()
pa.writeln(" "*linewidth)
pa.unset_underline()

pa.set_subscript()
pa.writeln("From Wikipedia, the free encyclopedia")
pa.unset_script()

pa.write_string("\nThe ")
pa.set_bold()
pa.write_string("Wittig reaction ")
pa.unset_bold()
pa.write_string("or Wittig olefination is a chemical reaction of an aldehyde or ketone with a triphenyl phosphonium ylide (often called a ")
pa.set_bold()
pa.write_string("Wittig reagent")
pa.unset_bold()
pa.write_string(") to give an alkene and triphenylphosphine oxide.")
pa.set_superscript()
pa.write_string("[1][2]")
pa.unset_script()
pa.writeln("")

pa.set_left_margin(10)
pa.write_image("Wittig.png")
pa.set_left_margin(0)

pa.write_string("\nThe Wittig reaction was discovered in 1954 by Georg Wittig, for which he was awarded the Nobel Prize in Chemistry in 1979. It is widely used in organic synthesis for the preparation of alkenes.")
pa.set_superscript()
pa.write_string("[3][4][5]")
pa.unset_script()
pa.write_string("It should not be confused with the Wittig rearrangement.\n")
pa.writeln("Wittig reactions are most commonly used to couple aldehydes and ketones to singly substituted phosphine ylides. With unstabilised ylides this results in almost exclusively the Z-alkene product. In order to obtain the E-alkene, stabilised ylides are used in the Horner-Wadsworth-Emmons reaction or unstabilised ylides are used in the Schlosser modification of the Wittig reaction.")

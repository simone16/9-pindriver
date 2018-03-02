from ESCPdriver import ParallelAdapter

pa = ParallelAdapter()

pa.reset_printer()
pa.set_line_spacing(60)
pa.writeln("Testing printing of user-defined characters:")
pa.roman_to_RAM()
pa.set_double_width()
pa.set_double_height()

smile = pa.Glyph()
smile.data = [ 0, 4, 0, 122, 0, 2, 120, 2, 4, 0, 0]
pa.define_draft_char( 65, smile)

pa.set_RAM_char_table()
pa.putchar( 65, 65, 65, 65, 65, 66)
pa.writeln("SMILE: A")

smile.data = [0, 16, 0, 0, 8, 0, 15, 136, 0, 0, 8, 0, 0, 8, 0, 15, 136, 0, 0, 8, 0, 0, 8, 0, 0, 16, 0]
pa.set_NLQ()
pa.sansserif_to_RAM()
pa.define_NLQ_char(65, smile)
pa.putchar( 65, 65, 65, 65, 65, 66)
pa.writeln("SMILE: A")

pa.unset_RAM_char_table()
pa.writeln("NON SMILE: A")

pa.unset_NLQ()
pa.unset_double_width()
pa.unset_double_height()

smile.data = [60, 66, 129, 0, 66, 36, 0, 60, 0, 36, 24]
pa.define_draft_char(66, smile)
pa.set_double_width()
pa.set_RAM_char_table()
pa.writeln('AAAAABBBB')
pa.set_italics()
pa.writeln('AAAAABBBBB')
pa.unset_double_width()

input()

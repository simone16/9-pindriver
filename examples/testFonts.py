from ESCPdriver import ParallelAdapter

pa = ParallelAdapter()

print('pa = ParallelAdapter()')

msg = "This is a test string, pitch="

pa.reset_printer()
pa.writeln(msg+" 10cpi")
pa.set_pitch_12cpi()
pa.writeln(msg+" 12cpi")
pa.set_pitch_15cpi()
pa.writeln(msg+" 15cpi")
pa.set_condensed()
pa.set_pitch_10cpi()
pa.writeln(msg+" 10cpi condensed")
pa.set_pitch_12cpi()
pa.writeln(msg+" 12cpi condensed")
pa.set_pitch_15cpi()
pa.writeln(msg+" 15cpi condensed")
pa.unset_condensed()
pa.set_pitch_proportional()
pa.writeln(msg+" 10cpi proportional")
pa.set_pitch_12cpi()
pa.writeln(msg+" 12cpi proportional")
pa.set_pitch_15cpi()
pa.writeln(msg+" 15cpi proportional")
pa.unset_pitch_proportional()
pa.set_double_width()
pa.writeln(msg+" 10cpi double")
pa.set_pitch_12cpi()
pa.writeln(msg+" 12cpi double")
pa.set_pitch_15cpi()
pa.writeln(msg+" 15cpi double")
pa.set_condensed()
pa.set_pitch_10cpi()
pa.writeln(msg+" 10cpi condensed")
pa.set_pitch_12cpi()
pa.writeln(msg+" 12cpi condensed")
pa.set_pitch_15cpi()
pa.writeln(msg+" 15cpi condensed")
pa.unset_condensed()
pa.unset_double_width()
input()

from ESCPdriver import ParallelAdapter
import sys

pa = ParallelAdapter()

#pa.set_right_margin(65)

pa.write_image(sys.argv[1])

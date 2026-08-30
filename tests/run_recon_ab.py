import os
import runpy
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = [os.path.join(os.path.dirname(__file__), "recon_archive", "akd56_16063_ab.py")] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")

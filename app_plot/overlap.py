import os
import sys
import shutil
import logging
sys.path.append('/home/jqwu/projects/gnss_scripts')
from funcs import GnssTime, GnssConfig, GrtOrbdif

year=2021
proj = "/home/jqwu/projects/POD_MF/GR_12/L2_PCO/dd_fix"
for i in range(1, 2):
#for i in [95, 100, 105, 110, 115]:
    wkdir = f"{proj}/{year}/{i:0>3d}_test1"
    os.chdir(wkdir)
    config = GnssConfig.from_file('config.ini')
    GrtOrbdif(config, "overlap", overlap=True).run()
    f_ovlap = f"{wkdir}/orbdif/overlap_{year}{i:0>3d}"
    f_dest  = f"{proj}/overlap/{year}"
    print(f"{i:0>3d}")
    if not os.path.isdir(f_dest):
        os.makedirs(f_dest)
    f_dest = f"{f_dest}/overlap_{year}{i:0>3d}"
    if os.path.isfile(f_ovlap):
        shutil.copy(f_ovlap, f_dest)

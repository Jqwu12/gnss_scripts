import os
import sys
import shutil
import logging
sys.path.append('/home/jqwu/projects/gnss_scripts')
from funcs import GnssTime, GnssConfig, GrtOrbdif

cen = 'gbm'
proj = "/home/jqwu/projects/POD_FIX/GEC_ud_chk"
for i in range(235, 236):
#for i in [95, 100, 105, 110, 115]:
    print(f"{i:0>3d}")
    wkdir = f"{proj}/2020/{i:0>3d}"
    os.chdir(wkdir)
    config = GnssConfig.from_file('config.ini')
    GrtOrbdif(config, f"orbdif_{cen}").run()
    f_ovlap = f"{wkdir}/orbdif/orbdif_2020{i:0>3d}_{cen}"
    f_dest  = f"{proj}/orbdif/2020"
    print(f"{i:0>3d}")
    if not os.path.isdir(f_dest):
        os.makedirs(f_dest)
    f_dest = f"{f_dest}/orbdif_2020{i:0>3d}_{cen}"
    if os.path.isfile(f_ovlap):
        shutil.copy(f_ovlap, f_dest)

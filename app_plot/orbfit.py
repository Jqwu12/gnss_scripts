import os
import sys
import shutil
import logging
import pandas as pd
sys.path.append('/home/jqwu/projects/gnss_scripts')
from funcs import mkdir, GnssTime, GnssConfig, GrtOi, GrtOrbfit, doy2mjd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)8s: %(message)s')

cf_file = '/home/jqwu/projects/gnss_scripts/app_plot/cf_orbfit.ini'
config = GnssConfig.from_file(cf_file)
proj = "/home/jqwu/projects/POD_MF/G_15/L2_PCO/dd_fix"
config.base_dir = proj
wkdir = f"{proj}/orbfit"
mkdir([wkdir])
os.chdir(wkdir)
mkdir(['ics', 'sp3', 'orb', 'ics_out', 'fit'])
#beta = pd.read_csv(f'/home/jqwu/projects/POD_MF/pco_G/statistics/beta_angle.csv', index_col=0)

year=2022
doy0 = 185
doy1 = 240
for i in range(doy0, doy1):
    config.beg_time = GnssTime.from_ydoy(year, i)
    config.end_time = config.beg_time + 48*3600 - config.intv
    logging.info(f"------------------------------------------------------------------------\n{' ' * 36}"
                    f"===> Process {year}-{i:0>3d}\n{' ' * 36}"
                    f"work directory = {wkdir}")

    sat_rm = ['E14', 'E18']
    mjd = doy2mjd(year, i)
    #sats = list(beta[(beta.mjd == mjd) & (beta.beta < 14) & (beta.beta > -14)].sat)
    #sat_rm = list(set(sat_rm + sats))
    #sat_rm.sort()
    #logging.warning(f"low beta angle: {' '.join(sat_rm)}")
    #config.sat_rm = sat_rm

    config.copy_sys_data()
    GrtOi(config, 'oi').run()
    GrtOrbfit(config, 'orbfit', sp3=True, trans='STRD').run()
    logging.info(f"------------------------------------------------------------------------\n")

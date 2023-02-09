import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import GnssTime, GnssConfig, GrtOrbdif, multi_run

def orbdif(config: GnssConfig, ref_cen: list):
    cmds = []
    for c in ref_cen:
        config.orb_ac = c
        cmds.extend(GrtOrbdif(config, f'orbdif_{c}').form_cmd())
    multi_run(cmds, "orbdif", 8)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)8s: %(message)s')
    cf_file = os.path.join(os.path.dirname(__file__), f'cf_orbdif.ini')
    if not os.path.isfile(cf_file):
        sys.exit()
    
    config = GnssConfig.from_file(cf_file)
    beg_time = GnssTime.from_ydoy(2020, 1)
    count = 366

    while count > 0:
        config.beg_time = beg_time
        config.end_time = config.beg_time + 86400 - config.intv
        wkdir = config.workdir
        if not os.path.isdir(wkdir):
            os.makedirs(wkdir)
        os.chdir(wkdir)

        crt_time = config.beg_time
        logging.info(f"------------------------------------------------------------------------\n{' ' * 36}"
                f"===> Process {crt_time.year}-{crt_time.doy:0>3d}\n{' ' * 36}"
                f"work directory = {wkdir}")

        req_dirs = ['xml', 'tmp', 'orbdif']
        for d in req_dirs:
            if not os.path.isdir(d):
                os.makedirs(d)
        
        #ref_cen = ['gbm', 'com', 'grm', 'wum']
        ref_cen = ['gr0']
        orbdif(config, ref_cen)

        # next day
        beg_time += 86400
        count -= 1
        logging.info(f"------------------------------------------------------------------------\n")

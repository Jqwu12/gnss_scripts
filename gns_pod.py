#!/home/jqwu/anaconda3/bin/python3
from gnss_config import GNSSconfig
from gnss_time import GNSStime, hms2sod
import gnss_tools as gt
# import gnss_files as gf
from constants import read_site_list
import os
import shutil
import logging
import platform
import argparse

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

# ------ Get args ----------------
parser = argparse.ArgumentParser(description='Run Precise Orbit Determination')
parser.add_argument('-n', dest='num', type=int, default=1, help='number of process days')
parser.add_argument('-l', dest='len', type=int, default=24, help='process time length (hours)')
parser.add_argument('-i', dest='intv', type=int, default=300, help='process interval (seconds)')
parser.add_argument('-c', dest='obs_comb', default='IF', choices={'UC', 'IF'}, help='Observation combination')
parser.add_argument('-est', dest='est', default='LSQ', choices={'EPO', 'LSQ'}, help='Estimator: LSQ or EPO')
parser.add_argument('-sys', dest='sys', default='G', help='used GNSS observations, e.g. G/GC/GREC')
parser.add_argument('-freq', dest='freq', type=int, default=2, help='used GNSS frequencies')
parser.add_argument('-cen', dest='cen', default='com', choices={'igs', 'cod', 'com', 'wum', 'gbm', 'grm', 'sgg'},
                    help='GNSS precise orbits and clocks')
parser.add_argument('-bia', dest='bia', default='cas', choices={'cod', 'cas', 'whu', 'sgg'},
                    help='bias files')
parser.add_argument('-s', dest='f_list', required=True, help='site_list file')
parser.add_argument('-y', dest='year', type=int, required=True, help='begin date: year')
parser.add_argument('-d', dest='doy', type=int, required=True, help='begin date: day of year')
parser.add_argument('-t', dest='hms', nargs='+', help='begin date: hh mm ss')
parser.add_argument('-sod', dest='sod', help='begin date: seconds of day')
args = parser.parse_args()

# ------ Path information --------
if platform.system() == 'Windows':
    grt_dir = r"C:\Users\jiaqi\GNSS_Software\branches"
    grt_bin = os.path.join(grt_dir, 'merge_navpod_merge_ppp', 'build', 'Bin', 'RelWithDebInfo')
    sys_data = r"C:\Users\jiaqi\GNSS_Project\sys_data"
    gns_data = r"C:\Users\jiaqi\GNSS_Project\gns_data"
    upd_data = r"C:\Users\jiaqi\GNSS_Project\gns_data\upd"
    base_dir = r"C:\Users\jiaqi\GNSS_Project"
else:
    grt_dir = "/home/jqwu/softwares/GREAT/branches"
    grt_bin = os.path.join(grt_dir, 'merge_navpod_merge_ppp', 'build', 'Bin')
    sys_data = "/home/jqwu/projects/sys_data"
    gns_data = "/home/jqwu/gns_data"
    upd_data = "/home/jqwu/gns_data/upd"
    base_dir = "/home/jqwu/projects"

# ------ Init config file --------
sta_list = read_site_list(args.f_list)
sta_list.sort()
f_config_tmp = 'gnspod_config.ini'
config = GNSSconfig(f_config_tmp)
config.update_pathinfo(sys_data, gns_data, upd_data)
config.update_gnssinfo(args.sys, args.freq, args.obs_comb, args.est)
if sta_list:
    config.update_stalist(sta_list)
else:
    raise SystemExit("No site to process")
if args.freq > 2:
    args.bia = "CAS"
config.update_prodinfo(args.cen, args.bia)

# ------ Start PPP process -------
proj_dir = os.path.join(base_dir, 'POD')
if args.sod:
    sod = args.sod
elif args.hms:
    sod = hms2sod(args.hms[0:3])
else:
    sod = hms2sod(0)
count = args.num
seslen = hms2sod(args.len)
t_beg0 = GNSStime()
t_beg0.set_ydoy(args.year, args.doy, sod)
# ------- daily loop -------------
while count > 0:
    t_beg = t_beg0
    t_end = t_beg.time_increase(seslen-args.intv)
    config.update_timeinfo(t_beg, t_end, args.intv)
    config.update_process(crd_constr='FIX')
    logging.info(f"\n===> Run POD for {t_beg.year}-{t_beg.doy:0>3d}\n")
    workdir = os.path.join(proj_dir, str(t_beg.year), f"{t_beg.doy:0>3d}_{args.sys}_{args.obs_comb}")
    if not os.path.isdir(workdir):
        os.makedirs(workdir)
    # else:
    #     shutil.rmtree(workdir)
    #     os.makedirs(workdir)
    os.chdir(workdir)
    gt.mkdir(['log_tb', 'ppp', 'ambupd', 'orbdif', 'clkdif'])
    logging.info(f"work directory is {workdir}")

    # ---------- Basic check ---------
    config.copy_sys_data()
    if config.basic_check(['estimator'], ['rinexo', 'rinexn', 'sp3', 'biabern']):
        logging.info("Basic check complete ^_^")
    else:
        logging.critical("Basic check failed! skip to next day")
        t_beg = t_beg.time_increase(86400)
        count -= 1
        continue

    f_config = os.path.join(workdir, 'config.ini')
    config.write_config(f_config)  # config file is only for check
    logging.info(f"config is {f_config}")

    # Run turboedit
    config.update_process(intv=30)
    nthread = min(len(config.all_receiver().split()), 10)
    # gt.run_great(grt_bin, 'great_turboedit', config, nthread=nthread)
    config.update_process(intv=args.intv)
    if config.basic_check(files=['ambflag']):
        logging.info("Ambflag is ok ^_^")
    else:
        logging.critical("NO ambflag files ! skip to next day")
        t_beg = t_beg.time_increase(86400)
        count -= 1
        continue
    # Generate initial orbit using BRD
    gt.run_great(grt_bin, 'great_preedit', config)
    gt.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gt.run_great(grt_bin, 'great_orbdif', config)
    gt.run_great(grt_bin, 'great_orbfit', config)
    gt.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gt.run_great(grt_bin, 'great_orbdif', config)
    gt.copy_result_files(config, ['orbdif', 'ics'], 'BRD', 'gns')

    # Run Precise Orbit Determination
    gt.run_great(grt_bin, 'great_podlsq', config, mode='POD_EST', out="podlsq.log")
    gt.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gt.run_great(grt_bin, 'great_orbdif', config)
    gt.copy_result_files(config, ['orbdif', 'ics'], 'F1', 'gns')

    gt.run_great(grt_bin, 'great_podlsq', config, mode='POD_EST', out="podlsq.log")
    gt.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gt.run_great(grt_bin, 'great_orbdif', config)
    gt.copy_result_files(config, ['orbdif', 'ics'], 'F2', 'gns')

    gt.run_great(grt_bin, 'great_podlsq', config, mode='POD_EST', out="podlsq.log")
    gt.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gt.run_great(grt_bin, 'great_orbdif', config)
    gt.copy_result_files(config, ['orbdif', 'ics'], 'F3', 'gns')

    # next day
    logging.info(f"Complete {t_beg.year}-{t_beg.doy:0>3d} ^_^\n")
    t_beg0 = t_beg0.time_increase(86400)
    count -= 1

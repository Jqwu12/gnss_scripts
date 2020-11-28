#!/home/jqwu/anaconda3/bin/python3
from gnss_config import GNSSconfig
from gnss_time import GNSStime, hms2sod
import gnss_tools as gt
# import gnss_files as gf
import gnss_run as gr
from constants import read_site_list
import os
import shutil
import logging
import platform
import argparse

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

# ------ Get args ----------------
parser = argparse.ArgumentParser(description='Perform Precise Point Positioning')
# Time argument
parser.add_argument('-n', dest='num', type=int, default=1, help='number of process days')
parser.add_argument('-l', dest='len', type=int, default=24, help='process time length (hours)')
parser.add_argument('-i', dest='intv', type=int, default=30, help='process interval (seconds)')
parser.add_argument('-t', dest='hms', nargs='+', help='begin date: hh mm ss')
parser.add_argument('-sod', dest='sod', help='begin date: seconds of day')
# Estimation argument
parser.add_argument('-c', dest='obs_comb', default='IF', choices={'UC', 'IF'}, help='observation combination')
parser.add_argument('-est', dest='est', default='EPO', choices={'EPO', 'LSQ'}, help='estimator: LSQ or EPO')
parser.add_argument('-sys', dest='sys', default='G', help='used GNSS observations, e.g. G/GC/GREC')
parser.add_argument('-freq', dest='freq', type=int, default=2, help='used GNSS frequencies')
# File argument
parser.add_argument('-cen', dest='cen', default='com', choices={'igs', 'cod', 'com', 'wum', 'gbm', 'grm', 'sgg', 'grt'},
                    help='GNSS precise orbits and clocks')
parser.add_argument('-bia', dest='bia', default='cas', choices={'cod', 'cas', 'whu', 'sgg'},
                    help='bias files')
parser.add_argument('-cf', dest='cf', default='cf_ppp.ini', help='config file')
parser.add_argument('-kp', dest='keep_dir', action='store_true', help='Keep the existing work dir')
# Required argument
parser.add_argument('-s', dest='f_list', required=True, help='site_list file')
parser.add_argument('-y', dest='year', type=int, required=True, help='begin date: year')
parser.add_argument('-d', dest='doy', type=int, required=True, help='begin date: day of year')
args = parser.parse_args()

# ------ Path information --------
if platform.system() == 'Windows':
    grt_dir = r"D:\GNSS_Software\GREAT"
    grt_bin = os.path.join(grt_dir, 'build', 'Bin', 'RelWithDebInfo')
    sys_data = r"D:\GNSS_Project\sys_data"
    gns_data = r"D:\GNSS_Project\gns_data"
    upd_data = r"D:\GNSS_Project\gns_data\upd"
    base_dir = r"D:\GNSS_Project"
else:
    grt_dir = "/home/jqwu/softwares/GREAT/branches"
    grt_bin = os.path.join(grt_dir, 'merge_navpod_merge_ppp', 'build', 'Bin')
    sys_data = "/home/jqwu/projects/sys_data"
    gns_data = "/home/jqwu/gns_data"
    upd_data = "/home/jqwu/projects/UPD"
    base_dir = "/home/jqwu/projects"

# ------ Init config file --------
sta_list = read_site_list(args.f_list)
sta_list.sort()
if not sta_list:
    raise SystemExit("No site to process")
if not os.path.isfile(args.cf):
    raise SystemExit("Cannot get config file >_<")
config = GNSSconfig(args.cf)
config.update_pathinfo(sys_data, gns_data, upd_data)
config.update_gnssinfo(args.sys, args.freq, args.obs_comb, args.est)
config.update_stalist(sta_list)
config.update_prodinfo(args.cen, args.bia)

# ------ Start PPP process -------
proj_dir = os.path.join(base_dir, 'PPP')
if args.sod:
    sod = args.sod
elif args.hms:
    if len(args.hms) > 2:
        sod = hms2sod(args.hms[0], args.hms[1], args.hms[2])
    elif len(args.hms) > 1:
        sod = hms2sod(args.hms[0], args.hms[1])
    else:
        sod = hms2sod(args.hms[0])
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
    config.update_process(crd_constr='EST')
    logging.info(f"\n===> Run PPP for {t_beg.year}-{t_beg.doy:0>3d}\n")
    workdir = os.path.join(proj_dir, str(t_beg.year), f"{t_beg.doy:0>3d}_{args.sys}_test7")
    if not os.path.isdir(workdir):
        os.makedirs(workdir)
    else:
        if not args.keep_dir:
            shutil.rmtree(workdir)
            os.makedirs(workdir)
    os.chdir(workdir)
    gt.mkdir(['log_tb', 'enu', 'flt', 'ppp', 'ambupd', 'res', 'tmp'])
    logging.info(f"work directory is {workdir}")

    # ---------- Basic check ---------
    config.copy_sys_data()
    if config.basic_check(['estimator'], ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']):
        logging.info("Basic check complete ^_^")
    else:
        logging.critical("Basic check failed ! skip to next day")
        t_beg = t_beg.time_increase(86400)
        count -= 1
        continue

    f_config = os.path.join(workdir, 'config.ini')
    config.write_config(f_config)  # config file is only for check
    logging.info(f"config is {f_config}")

    # Run turboedit
    config.update_process(frequency='3')
    nthread = min(len(config.all_receiver().split()), 8)
    gr.run_great(grt_bin, 'great_turboedit', config, nthread=nthread)
    config.remove_sta(gt.check_turboedit_log(nthread))
    if config.basic_check(files=['ambflag']):
        logging.info("Ambflag is ok ^_^")
    else:
        logging.critical("NO ambflag files ! skip to next day")
        t_beg = t_beg.time_increase(86400)
        count -= 1
        continue

    # Run Precise Point Positioning
    config.update_gnssinfo(obs_model='UC', freq=3)
    gr.run_great(grt_bin, 'great_ppplsq', config, mode='PPP_EST', newxml=True, nthread=nthread, fix_mode="NO",
                 out=os.path.join('tmp', 'ppplsq'))
    gr.run_great(grt_bin, 'great_ppplsq', config, mode='PPP_EST', newxml=True, nthread=nthread, fix_mode="SEARCH",
                 out=os.path.join('tmp', 'ppplsq'))

    config.update_gnssinfo(obs_model='UC', freq=2)
    gr.run_great(grt_bin, 'great_ppplsq', config, mode='PPP_EST', newxml=True, nthread=nthread, fix_mode="NO",
                 out=os.path.join('tmp', 'ppplsq'))
    gr.run_great(grt_bin, 'great_ppplsq', config, mode='PPP_EST', newxml=True, nthread=nthread, fix_mode="SEARCH",
                 out=os.path.join('tmp', 'ppplsq'))

    config.update_gnssinfo(obs_model='IF', freq=3)
    gr.run_great(grt_bin, 'great_ppplsq', config, mode='PPP_EST', newxml=True, nthread=nthread, fix_mode="NO",
                 out=os.path.join('tmp', 'ppplsq'))
    gr.run_great(grt_bin, 'great_ppplsq', config, mode='PPP_EST', newxml=True, nthread=nthread, fix_mode="SEARCH",
                 out=os.path.join('tmp', 'ppplsq'))

    config.update_gnssinfo(obs_model='IF', freq=2)
    gr.run_great(grt_bin, 'great_ppplsq', config, mode='PPP_EST', newxml=True, nthread=nthread, fix_mode="NO",
                 out=os.path.join('tmp', 'ppplsq'))
    gr.run_great(grt_bin, 'great_ppplsq', config, mode='PPP_EST', newxml=True, nthread=nthread, fix_mode="SEARCH",
                 out=os.path.join('tmp', 'ppplsq'))

    # next day
    logging.info(f"Complete {t_beg.year}-{t_beg.doy:0>3d} ^_^\n")
    t_beg0 = t_beg0.time_increase(86400)
    count -= 1

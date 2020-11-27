#!/home/jqwu/anaconda3/bin/python3
from gnss_config import GNSSconfig
from gnss_time import GNSStime, hms2sod
import gnss_tools as gt
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
parser = argparse.ArgumentParser(description='Run Precise Orbit Determination')
# Time argument
parser.add_argument('-n', dest='num', type=int, default=1, help='number of process days')
parser.add_argument('-l', dest='len', type=int, default=24, help='process time length (hours)')
parser.add_argument('-i', dest='intv', type=int, default=300, help='process interval (seconds)')
parser.add_argument('-t', dest='hms', nargs='+', help='begin date: hh mm ss')
parser.add_argument('-sod', dest='sod', help='begin date: seconds of day')
# Estimation argument
parser.add_argument('-c', dest='obs_comb', default='IF', choices={'UC', 'IF'}, help='observation combination')
parser.add_argument('-est', dest='est', default='LSQ', choices={'EPO', 'LSQ'}, help='estimator: LSQ or EPO')
parser.add_argument('-sys', dest='sys', default='G', help='used GNSS observations, e.g. G/GC/GREC')
parser.add_argument('-freq', dest='freq', type=int, default=2, help='used GNSS frequencies')
# File argument
parser.add_argument('-cen', dest='cen', default='com', choices={'igs', 'cod', 'com', 'wum', 'gbm', 'grm', 'sgg', 'grt'},
                    help='GNSS precise orbits and clocks')
parser.add_argument('-bia', dest='bia', default='cas', choices={'cod', 'cas', 'whu', 'sgg'},
                    help='bias files')
parser.add_argument('-cf', dest='cf', default='cf_gnspod.ini', help='config file')
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
    upd_data = "/home/jqwu/gns_data/upd"
    base_dir = "/home/jqwu/projects"

# ------ Init config file --------
sta_list = read_site_list(args.f_list)
sta_list.sort()
if not os.path.isfile(args.cf):
    raise SystemExit("Cannot get config file >_<")
config = GNSSconfig(args.cf)
config.update_pathinfo(sys_data, gns_data, upd_data)
config.update_gnssinfo(args.sys, args.freq, args.obs_comb, args.est)
if sta_list:
    config.update_stalist(sta_list)
else:
    raise SystemExit("No site to process!")
if args.freq > 2:
    args.bia = "CAS"
config.update_prodinfo(args.cen, args.bia)

# ------ Start PPP process -------
proj_dir = os.path.join(base_dir, 'POD')
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
    config.update_gnssinfo(sat_rm=[])
    config.update_process(crd_constr='EST')
    logging.info(f"\n===> Run POD for {t_beg.year}-{t_beg.doy:0>3d}\n")
    workdir = os.path.join(proj_dir, str(t_beg.year), f"{t_beg.doy:0>3d}_{args.sys}_{args.freq}_{args.obs_comb}")
    if not os.path.isdir(workdir):
        os.makedirs(workdir)
    else:
        if not args.keep_dir:
            shutil.rmtree(workdir)
            os.makedirs(workdir)
    os.chdir(workdir)
    gt.mkdir(['log_tb', 'tmp', 'orbdif', 'clkdif'])
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
    # gr.run_great(grt_bin, 'great_turboedit', config, nthread=nthread, out=os.path.join("tmp", "turboedit"))
    config.update_process(intv=args.intv)
    if config.basic_check(files=['ambflag']):
        logging.info("Ambflag is ok ^_^")
    else:
        logging.critical("NO ambflag files ! skip to next day")
        t_beg = t_beg.time_increase(86400)
        count -= 1
        continue

    # Generate initial orbit using BRD
    gr.run_great(grt_bin, 'great_preedit', config)
    gr.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gr.run_great(grt_bin, 'great_orbdif', config)
    gr.run_great(grt_bin, 'great_orbfit', config)
    gr.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gr.run_great(grt_bin, 'great_orbdif', config)
    config.update_gnssinfo(sat_rm=gt.check_brd_orbfit(config.get_filename('orbdif')))
    gt.copy_result_files(config, ['orbdif', 'ics'], 'BRD', 'gns')

    # Run Precise Orbit Determination
    # 1st
    gr.run_great(grt_bin, 'great_podlsq', config, mode='POD_EST', str_args="-brdm", out=os.path.join("tmp", "podlsq"))
    gr.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gr.run_great(grt_bin, 'great_orbdif', config)
    gr.run_great(grt_bin, 'great_clkdif', config)
    gt.copy_result_files(config, ['orbdif', 'clkdif', 'ics'], 'F1', 'gns')
    gr.run_great(grt_bin, 'great_editres', config, nshort=600, bad=80, jump=80)

    # 2nd
    gr.run_great(grt_bin, 'great_podlsq', config, mode='POD_EST', out=os.path.join("tmp", "podlsq"))
    gr.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gr.run_great(grt_bin, 'great_orbdif', config)
    gr.run_great(grt_bin, 'great_clkdif', config)
    gt.copy_result_files(config, ['orbdif', 'clkdif', 'ics'], 'F2', 'gns')
    gr.run_great(grt_bin, 'great_editres', config, nshort=600, bad=40, jump=40)

    # 3rd
    gr.run_great(grt_bin, 'great_podlsq', config, mode='POD_EST', out=os.path.join("tmp", "podlsq"))
    gr.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gr.run_great(grt_bin, 'great_orbdif', config)
    gr.run_great(grt_bin, 'great_clkdif', config)
    gt.copy_result_files(config, ['orbdif', 'clkdif', 'ics', 'orb', 'satclk', 'recclk'], 'F3', 'gns')

    # Ambiguity fix solution
    config.update_process(intv=30)
    config.update_process(crd_constr='FIX')
    gr.run_great(grt_bin, 'great_ambfixDd', config, out=os.path.join("tmp", "ambfix"))
    config.update_process(intv=args.intv)
    gr.run_great(grt_bin, 'great_podlsq', config, mode='POD_EST', str_args="-ambfix", ambcon=True, use_res_crd=True,
                 out=os.path.join("tmp", "podlsq"))
    gr.run_great(grt_bin, 'great_oi', config, sattype='gns')
    gr.run_great(grt_bin, 'great_orbdif', config)
    gr.run_great(grt_bin, 'great_clkdif', config)
    gt.copy_result_files(config, ['orbdif', 'clkdif', 'ics', 'orb', 'satclk', 'recclk'], 'AR', 'gns')

    # next day
    logging.info(f"Complete {t_beg.year}-{t_beg.doy:0>3d} ^_^\n")
    t_beg0 = t_beg0.time_increase(86400)
    count -= 1

from gnss_config import GNSSconfig
from gnss_time import GNSStime, hms2sod
import gnss_tools as gt
# import gnss_files as gf
from constants import form_leolist
import os
import shutil
import logging
import platform
import argparse

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

# ------ Get args ----------------
parser = argparse.ArgumentParser(description='Perform LEO reduced dynamic POD')
parser.add_argument('-n', dest='num', type=int, default=1, help='number of process days')
parser.add_argument('-l', dest='len', type=int, default=30, help='process time length (hours)')
parser.add_argument('-i', dest='intv', type=int, default=10, help='process interval (seconds)')
parser.add_argument('-sys', dest='sys', default='G', help='used GNSS observations, e.g. G/GC/GREC')
parser.add_argument('-freq', dest='freq', type=int, default=2, help='used GNSS frequencies')
parser.add_argument('-cen', dest='cen', default='grm', choices={'igs', 'cod', 'com', 'wum', 'gbm', 'grm', 'sgg'},
                    help='GNSS precise orbits and clocks')
parser.add_argument('-bia', dest='bia', default='', choices={'cod', 'cas', 'whu', 'sgg'},
                    help='bias files')
parser.add_argument('-sta', dest='sta_list', nargs='+', help='list of Ground stations')
parser.add_argument('-y', dest='year', type=int, required=True, help='begin date: year')
parser.add_argument('-d', dest='doy', type=int, required=True, help='begin date: day of year')
parser.add_argument('-t', dest='hms', nargs='+', help='begin date: hh mm ss')
parser.add_argument('-sod', dest='sod', help='begin date: seconds of day')
parser.add_argument('-s', dest='leo_list', required=True, nargs='+',
                    help='LEO satellite list with short name or long name, e.g. grac grace-d swarm-a')
args = parser.parse_args()

# ------ Path information --------
if platform.system() == 'Windows':
    grt_dir = r"C:\Users\jiaqi\GNSS_Software\branches"
    grt_bin = os.path.join(grt_dir, 'merge_navpod_merge_ppp', 'build', 'Bin', 'RelWithDebInfo')
    sys_data = r"C:\Users\jiaqi\GNSS_Project\sys_data"
    gns_data = r"C:\Users\jiaqi\GNSS_Project\gns_data"
else:
    grt_dir = "/home/yuanyongqiang/data_new/WJQ/softwares/great/branches"
    grt_bin = os.path.join(grt_dir, 'merge_navpod_merge_ppp', 'build', 'Bin')
    sys_data = "/home/yuanyongqiang/data_new/WJQ/projects/LEO_POD_grt/sys_data"
    gns_data = "/home/yuanyongqiang/data_new/WJQ/data"


# ------ Init config file --------
leo_list = form_leolist(args.leo_list)
if not leo_list:
    raise SystemExit("LEO list is empty!")
sta_list = args.sta_list
f_config_tmp = os.path.abspath('leopod_config.ini')
config = GNSSconfig(f_config_tmp)
config.update_pathinfo(sys_data, gns_data)
config.update_gnssinfo(args.sys, args.freq, 'IF')
config.update_leolist(leo_list)
if sta_list:
    config.update_stalist(sta_list)
config.update_prodinfo(args.cen, args.bia)
base_dir = os.getcwd()

# ------ Start POD process -------
if sta_list:  # the multi-LEO POD and LEO+Station POD are not tested
    proj = f"leo{len(leo_list)}_sta{len(sta_list)}"
    proj_dir = os.path.join(base_dir, 'leo_sta', proj, f"Dyn_{args.len}h_{args.cen}")
else:
    if len(leo_list) > 1:
        proj = f"{leo_list[0]}_{len(leo_list)}"
        proj_dir = os.path.join(base_dir, 'leo_net', proj, f"Dyn_{args.len}h_{args.cen}")
    else:
        proj = leo_list[0]
        proj_dir = os.path.join(base_dir, 'single_leo', proj, f"Dyn_{args.len}h_{args.cen}")
if args.sod:
    sod = args.sod
elif args.hms:
    sod = hms2sod(args.hms[0:3])
else:
    sod = hms2sod(20)
count = args.num
seslen = hms2sod(args.len + 2)
t_beg0 = GNSStime()
t_beg0.set_ydoy(args.year, args.doy, sod)
# ------- daily loop -------------
while count > 0:
    t_beg = t_beg0
    t_end = t_beg.time_increase(seslen-args.intv)
    config.update_timeinfo(t_beg, t_end, args.intv)
    config.update_process(leopodmod='K', crd_constr='KIN')
    logging.info(f"\n===> Run {proj.upper()} RD POD for {t_beg.year}-{t_beg.doy:0>3d}\n")
    workdir = os.path.join(proj_dir, str(t_beg.year), f"{t_beg.doy:0>3d}")
    if not os.path.isdir(workdir):
        os.makedirs(workdir)
    #else:
    #    shutil.rmtree(workdir)
    #    os.makedirs(workdir)
    os.chdir(workdir)
    if not os.path.isdir('orbdif'):
        os.makedirs('orbdif')
    logging.info(f"work directory is {workdir}")

    # ---------- Basic check ---------
    config.copy_sys_data()
    # Currently, attitude file is necessary for kinematic POD
    # The attitude file header will be changed to GREAT format; and the antenna name in RINEXO will be
    isok = config.basic_check(['leopodmod', 'estimator'], ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern', 'attitude'])
    if isok:
        logging.info("Basic check complete ^_^")
    else:
        logging.critical("Basic check failed ! skip to next day")
        t_beg = t_beg.time_increase(86400)
        count -= 1
        continue

    f_config = os.path.join(workdir, 'config.ini')
    config.write_config(f_config)  # config file is only for check
    logging.info(f"config is {f_config}")

    # ------ Start LEO KIN POD for init orbit ------
    # SP3ORB NAV
    # gt.run_great(grt_bin, 'great_sp3orb', config, sattype='gns')
    # # Run turboedit
    # nthread = min(len(config.all_receiver().split()), 8)
    # gt.run_great(grt_bin, 'great_turboedit', config, nthread=nthread)
    # # Run Kinematic POD for init positions and velocities
    # gt.run_great(grt_bin, 'great_podlsq', config, mode='LEO_KIN', ambcon=False, newxml=True)
    # gt.run_great(grt_bin, 'great_podlsq', config, mode='LEO_KIN', ambcon=False, newxml=True)
    # gt.run_great(grt_bin, 'great_podlsq', config, mode='LEO_KIN', ambcon=False, newxml=True)
    # # Generate ICS and Orb
    # t_beg = t_beg.time_increase(3600)
    # t_end = t_end.time_increase(-3600)
    # config.update_timeinfo(t_beg, t_end, args.intv)
    gt.run_great(grt_bin, 'great_sp3orb', config, sattype='leo', newxml=True)
    gt.run_great(grt_bin, 'great_orbfitleo', config, fit=False, sattype='leo', newxml=True)
    gt.copy_result_files(config, ['kin', 'orbdif'], 'K', 'leo')
    gt.run_great(grt_bin, 'great_oi', config, str_args="-leo", sattype='leo', newxml=True)

    logging.info("------------------------------")
    logging.info("Start LEO Reduced Dynamic POD")
    logging.info("------------------------------")
    config.update_process(leopodmod='D', crd_constr='EST')

    # gt.run_great(grt_bin, 'great_turboedit', config, nthread=nthread)
    gt.run_great(grt_bin, 'great_podlsq', config, mode='LEO_DYN', ambcon=False, newxml=True)
    gt.run_great(grt_bin, 'great_oi', config, str_args="-leo", sattype='leo', newxml=True)
    gt.run_great(grt_bin, 'great_orbfitleo', config, fit=False, sattype='leo', newxml=True)
    gt.copy_result_files(config, ['orbdif', 'ics'], 'D1', 'leo')
    gt.run_great(grt_bin, 'great_editres', config, nshort=120, bad=80, jump=80)

    gt.run_great(grt_bin, 'great_podlsq', config, mode='LEO_DYN', ambcon=False)
    gt.run_great(grt_bin, 'great_oi', config, str_args="-leo", sattype='leo')
    gt.run_great(grt_bin, 'great_orbfitleo', config, fit=False, sattype='leo')
    gt.copy_result_files(config, ['orbdif', 'ics'], 'D2', 'leo')
    gt.run_great(grt_bin, 'great_editres', config, nshort=120, bad=40, jump=40)

    gt.run_great(grt_bin, 'great_podlsq', config, mode='LEO_DYN', ambcon=False)
    gt.run_great(grt_bin, 'great_oi', config, str_args="-leo", sattype='leo')
    gt.run_great(grt_bin, 'great_orbfitleo', config, fit=False, sattype='leo')
    gt.copy_result_files(config, ['orbdif', 'ics'], 'D3', 'leo')

    # ambiguity-fixed solution
    gt.run_great(grt_bin, 'great_ambfixD', config)
    for i in range(1, 3):
        gt.run_great(grt_bin, 'great_podlsq', config, mode='LEO_DYN', str_args="-ambfix", ambcon=True)
        gt.run_great(grt_bin, 'great_oi', config, str_args="-leo", sattype='leo')
        gt.run_great(grt_bin, 'great_orbfitleo', config, fit=False, sattype='leo')
        gt.copy_result_files(config, ['orbdif'], f"DFIX{i}", 'leo')

    # next day
    t_beg0 = t_beg0.time_increase(86400)
    count -= 1

#!/home/jqwu/anaconda3/bin/python3
from gnss_config import GNSSconfig
from gnss_time import GNSStime, hms2sod
import gnss_tools as gt
import gnss_run as gr
from constants import read_site_list
import os
import logging
import argparse


class RunGen:
    def __init__(self, config=None):
        self.args = self.get_args()
        if not config:
            self.config = GNSSconfig(self.args.cf)
            self.config.update_pathinfo()  # to be changed
            self.config.update_gnssinfo(self.args.sys, self.args.freq, self.args.obs_comb, self.args.est)
            if self.args.freq > 2:
                self.args.bia = "CAS"
            self.config.update_prodinfo(self.args.cen, self.args.bia)
            self.sta_list = read_site_list(self.args.f_list)
            self.grt_bin = self.config.config.get('common', 'grt_bin')
        else:
            self.config = config
            self.sta_list = config.stalist()
            self.grt_bin = config.config.get('common', 'grt_bin')

        self.required_subdir = ['log_tb', 'tmp']
        self.required_opt = []
        self.required_file = ['rinexo']

    # ------ Get args ----------------
    def get_args(self, intv=300, freq=2, est='LSQ', obs_comb='IF', cf='cf_gnspod.ini'):
        parser = argparse.ArgumentParser(description='GREAT Data Processing')
        # Time argument
        parser.add_argument('-n', dest='num', type=int, default=1, help='number of process days')
        parser.add_argument('-l', dest='len', type=int, default=24, help='process time length (hours)')
        parser.add_argument('-i', dest='intv', type=int, default=intv, help='process interval (seconds)')
        parser.add_argument('-t', dest='hms', nargs='+', help='begin date: hh mm ss')
        parser.add_argument('-sod', dest='sod', help='begin date: seconds of day')
        # Estimation argument
        parser.add_argument('-c', dest='obs_comb', default=obs_comb, choices={'UC', 'IF'}, help='observation combination')
        parser.add_argument('-est', dest='est', default=est, choices={'EPO', 'LSQ'}, help='estimator: LSQ or EPO')
        parser.add_argument('-sys', dest='sys', default='G', help='used GNSS observations, e.g. G/GC/GREC')
        parser.add_argument('-freq', dest='freq', type=int, default=freq, help='used GNSS frequencies')
        # File argument
        parser.add_argument('-cen', dest='cen', default='com', choices={'igs', 'cod', 'com', 'wum', 'gbm', 'grm', 'sgg', 'grt'},
                            help='GNSS precise orbits and clocks')
        parser.add_argument('-bia', dest='bia', default='cas', choices={'cod', 'cas', 'whu', 'sgg'},
                            help='bias files')
        parser.add_argument('-cf', dest='cf', default=cf, help='config file')
        parser.add_argument('-kp', dest='keep_dir', action='store_true', help='Keep the existing work dir')
        # Required argument
        parser.add_argument('-s', dest='f_list', required=True, help='site_list file')
        parser.add_argument('-y', dest='year', type=int, required=True, help='begin date: year')
        parser.add_argument('-d', dest='doy', type=int, required=True, help='begin date: day of year')
        args = parser.parse_args()
        return args

    def beg_time(self):
        if self.args.sod:
            sod = self.args.sod
        elif self.args.hms:
            if len(self.args.hms) > 2:
                sod = hms2sod(self.args.hms[0], self.args.hms[1], self.args.hms[2])
            elif len(self.args.hms) > 1:
                sod = hms2sod(self.args.hms[0], self.args.hms[1])
            else:
                sod = hms2sod(self.args.hms[0])
        else:
            sod = hms2sod(0)
        t_beg0 = GNSStime()
        t_beg0.from_ydoy(self.args.year, self.args.doy, sod)
        return t_beg0

    def update_path(self, all_path):
        self.config.update_pathinfo(all_path)
        self.grt_bin = self.config.config.get('common', 'grt_bin')

    def init_daily(self, crt_time, seslen):
        self.config.update_timeinfo(crt_time, crt_time + (seslen - self.args.intv), self.args.intv)
        self.config.update_stalist(self.sta_list)
        self.config.update_gnssinfo(sat_rm=[])
        self.config.update_process(crd_constr='EST')

    def prepare_obs(self):
        # ---------- Basic check ---------
        gt.mkdir(self.required_subdir)
        self.config.copy_sys_data()
        if self.config.basic_check(self.required_opt, self.required_file):
            logging.info("Basic check complete ^_^")
        else:
            logging.critical("Basic check failed! skip to next day")
            return False

        self.config.write_config('config.ini')

        logging.info(f"===> Preprocess RINEXO files with Turboedit")
        self.config.update_process(intv=30)
        nthread = min(len(self.config.all_receiver().split()), 10)
        logging.info(f"number of stations = {len(self.config.stalist())}, number of threads = {nthread}")
        gr.run_great(self.grt_bin, 'great_turboedit', self.config, nthread=nthread, out=os.path.join("tmp", "turboedit"))
        self.config.update_process(intv=self.args.intv)
        gt.check_turboedit_log(self.config, nthread)
        if self.config.basic_check(files=['ambflag']):
            logging.info("Ambflag is ok ^_^")
            return True
        else:
            logging.critical("NO ambflag files ! skip to next day")
            return False

    def prepare_ics(self):
        logging.info(f"===> Prepare initial orbits using broadcast ephemeris")
        gr.run_great(self.grt_bin, 'great_preedit', self.config)
        gr.run_great(self.grt_bin, 'great_oi', self.config, sattype='gns')
        gr.run_great(self.grt_bin, 'great_orbdif', self.config, out=os.path.join("tmp", "orbdif"))
        gr.run_great(self.grt_bin, 'great_orbfit', self.config, out=os.path.join("tmp", "orbfit"))
        gr.run_great(self.grt_bin, 'great_oi', self.config, sattype='gns')
        gr.run_great(self.grt_bin, 'great_orbdif', self.config, out=os.path.join("tmp", "orbdif"))
        sat_rm = gt.check_brd_orbfit(self.config.get_filename('orbdif'))
        self.config.update_gnssinfo(sat_rm=sat_rm)
        gt.copy_result_files(self.config, ['orbdif', 'ics'], 'BRD', 'gns')
        gt.backup_files(self.config, ['ics'])
        return True

    def process_daily(self):
        pass


if __name__ == '__main__':
    pass

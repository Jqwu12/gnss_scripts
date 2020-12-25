#!/home/jqwu/anaconda3/bin/python3
from funcs.gnss_config import GnssConfig
from funcs.gnss_time import GnssTime, hms2sod
from funcs import gnss_tools as gt, gnss_run as gr
from funcs.constants import read_site_list, _MAX_THREAD
import os
import shutil
import logging
import argparse
import platform


class ProcGen:
    def __init__(self):
        self.default_args = {
            'dsc': 'GREAT Data Processing',
            'num': 1, 'len': 24, 'intv': 300, 'obs_comb': 'IF', 'est': 'LSQ', 'sys': 'G',
            'freq': 2, 'cen': 'com', 'bia': 'cas', 'cf': 'cf_pod.ini'
        }
        self.args = None
        self.config = None
        self.sta_list = []
        self.grt_bin = ''
        self.proj_dir = ''
        self.result_dir = ''
        self.xml_dir = 'xml'
        self.required_subdir = ['log_tb', 'tmp']
        self.required_opt = []
        self.required_file = ['rinexo']

    def init_proc(self, config=None):
        if not config:
            self.args = self.get_args()
            self.config = GnssConfig(self.args.cf)
            self.config.update_pathinfo(check=False)  # to be changed
            self.config.update_gnssinfo(self.args.sys, self.args.freq, self.args.obs_comb, self.args.est)
            if self.args.freq > 2:
                self.args.bia = "CAS"
            self.config.update_timeinfo(intv=self.args.intv)
            self.config.update_prodinfo(self.args.cen, self.args.bia)
            self.sta_list = read_site_list(self.args.f_list)
            self.grt_bin = self.config.config.get('common', 'grt_bin')
        else:
            self.config = config
            self.sta_list = config.stalist()
            self.grt_bin = config.config.get('common', 'grt_bin')

    # ------ Get args ----------------
    def get_args(self):
        parser = argparse.ArgumentParser(description=self.default_args['dsc'])
        # Time argument
        parser.add_argument('-n', dest='num', type=int, default=self.default_args['num'],
                            help='number of process days')
        parser.add_argument('-l', dest='len', type=int, default=self.default_args['len'],
                            help='process time length (hours)')
        parser.add_argument('-i', dest='intv', type=int, default=self.default_args['intv'],
                            help='process interval (seconds)')
        parser.add_argument('-t', dest='hms', nargs='+', help='begin date: hh mm ss')
        parser.add_argument('-sod', dest='sod', help='begin date: seconds of day')
        # Estimation argument
        parser.add_argument('-c', dest='obs_comb', default=self.default_args['obs_comb'], choices={'UC', 'IF'},
                            help='observation combination')
        parser.add_argument('-est', dest='est', default=self.default_args['est'], choices={'EPO', 'LSQ'},
                            help='estimator: LSQ or EPO')
        parser.add_argument('-sys', dest='sys', default=self.default_args['sys'],
                            help='used GNSS observations, e.g. G/GC/GREC')
        parser.add_argument('-freq', dest='freq', type=int, default=self.default_args['freq'],
                            help='used GNSS frequencies')
        # File argument
        parser.add_argument('-cen', dest='cen', default=self.default_args['cen'],
                            choices={'igs', 'cod', 'com', 'wum', 'gbm', 'grm', 'sgg', 'grt'},
                            help='GNSS precise orbits and clocks')
        parser.add_argument('-bia', dest='bia', default=self.default_args['bia'], choices={'cod', 'cas', 'whu', 'sgg'},
                            help='bias files')
        parser.add_argument('-cf', dest='cf', default=self.default_args['cf'], help='config file')
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
        t_beg0 = GnssTime()
        t_beg0.from_ydoy(self.args.year, self.args.doy, sod)
        return t_beg0

    def nthread(self):
        return min(len(self.config.all_receiver().split()), _MAX_THREAD)

    def update_path(self, all_path):
        self.config.update_pathinfo(all_path)
        self.grt_bin = self.config.config.get('common', 'grt_bin')

    def init_daily(self, crt_time, seslen):
        self.config.update_timeinfo(crt_time, crt_time + (seslen - self.config.intv()), self.config.intv())
        self.config.update_stalist(self.sta_list)
        self.config.update_gnssinfo(sat_rm=[])
        # self.config.change_data_path('rinexo', 'obs')
        self.config.update_process(crd_constr='EST')

    def basic_check(self):
        # ---------- Basic check ---------
        gt.mkdir(self.required_subdir)
        self.config.copy_sys_data()
        if self.config.basic_check(self.required_opt, self.required_file):
            logging.info("Basic check complete ^_^")
        else:
            logging.critical("Basic check failed! skip to next day")
            return False
        if self.config.is_integer_clock() and not self.config.is_integer_clock_osb():
            gt.get_grg_wsb(self.config)
        return True

    def prepare_obs(self):
        logging.info(f"===> Preprocess RINEXO files with Clock-Repair and Turboedit")
        intv = self.config.intv()
        self.config.update_process(intv=30)
        logging.info(f"number of stations = {len(self.config.stalist())}, number of threads = {self.nthread()}")
        # gr.run_great(self.grt_bin, 'great_clockrepair', self.config, label='clockrepair',
        #              xmldir=self.xml_dir, nthread=self.nthread())
        # self.config.change_data_path('rinexo', 'obs_trimcor')
        tb_label = 'turboedit'
        gr.run_great(self.grt_bin, 'great_turboedit', self.config, label=tb_label,
                     xmldir=self.xml_dir, nthread=self.nthread())
        self.config.update_process(intv=intv)
        gt.check_turboedit_log(self.config, self.nthread(), label=tb_label, path=self.xml_dir)
        if self.config.basic_check(files=['ambflag']):
            logging.info("Ambflag is ok ^_^")
            return True
        else:
            logging.critical("NO ambflag files ! skip to next day")
            return False

    def prepare_ics(self):
        logging.info(f"===> Prepare initial orbits using broadcast ephemeris")
        cen = self.config.config['process_scheme']['cen']
        self.config.update_process(cen='brd')
        gr.run_great(self.grt_bin, 'great_preedit', self.config, label='preedit', xmldir=self.xml_dir)
        # do not change the label and xmldir of preedit
        gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)
        gr.run_great(self.grt_bin, 'great_orbfit', self.config, label='orbfit', xmldir=self.xml_dir)
        gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)
        gr.run_great(self.grt_bin, 'great_orbfit', self.config, label='orbfit', xmldir=self.xml_dir)
        sat_rm = gt.check_brd_orbfit(self.config.get_filename('orbdif'))
        self.config.update_gnssinfo(sat_rm=sat_rm)
        gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)
        self.config.update_process(cen=cen)
        gt.backup_files(self.config, ['ics', 'orb'])
        return True

    def prepare(self):
        with gt.timeblock("Finished prepare obs"):
            if not self.prepare_obs():
                return False

        return True

    def process_daily(self):
        pass

    def save_results(self, x):
        pass

    def generate_products(self, x=None):
        pass

    def process_batch(self):
        # logging.basicConfig(level=logging.INFO,
        #                     format='%(asctime)s - %(filename)20s[line:%(lineno)5d] - %(levelname)8s: %(message)s')
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)8s: %(message)s')
        # ------ Path information --------
        if platform.system() == 'Windows':
            all_path = {
                'grt_bin': r"D:\GNSS_Software\GREAT\build\Bin\RelWithDebInfo",
                'base_dir': r"D:\GNSS_Project",
                'sys_data': r"D:\GNSS_Project\sys_data",
                'gns_data': r"D:\GNSS_Project\gns_data",
                'upd_data': r"D:\GNSS_Project\gns_data\upd"
            }
        else:
            all_path = {
                'grt_bin': "/home/jqwu/softwares/GREAT/GREAT/build/Bin",
                'base_dir': "/home/jqwu/projects",
                'sys_data': "/home/jqwu/projects/sys_data",
                'gns_data': "/home/jqwu/gns_data",
                'upd_data': "/home/jqwu/gns_data/upd"
            }

        # ------ Init config file --------
        self.init_proc()
        if not self.sta_list:
            raise SystemExit("No site to process!")
        self.update_path(all_path)
        # ------ Set process time --------
        step = 86400
        beg_time = self.beg_time()
        end_time = beg_time + self.args.num * step - self.args.intv
        seslen = hms2sod(self.args.len)

        # ------- daily loop -------------
        crt_time = beg_time
        while crt_time < end_time:
            # reset daily config
            self.init_daily(crt_time, seslen)
            logging.info(f"------------------------------------------------------------------------")
            logging.info(f"===> Process {crt_time.year}-{crt_time.doy:0>3d}")
            if self.config.work_dir():
                workdir = self.config.work_dir()
            else:
                workdir = os.path.join(self.proj_dir, str(crt_time.year), f"{crt_time.doy:0>3d}_{self.args.sys}")
            if not os.path.isdir(workdir):
                os.makedirs(workdir)
            else:
                if not self.args.keep_dir:
                    shutil.rmtree(workdir)
                    os.makedirs(workdir)
            os.chdir(workdir)
            logging.info(f"work directory = {workdir}")

            if not self.basic_check():
                crt_time += step
                continue

            with gt.timeblock("Finished prepare"):
                if not self.prepare():
                    crt_time += step
                    continue

            self.config.write_config('config.ini')
            with gt.timeblock(f"Finished process {crt_time.year}-{crt_time.doy:0>3d}"):
                self.process_daily()

            # next day
            logging.info(f"------------------------------------------------------------------------\n")
            crt_time += step


if __name__ == '__main__':
    pass

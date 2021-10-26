import os
import shutil
import logging
import argparse
from funcs import GnssConfig, GnssTime, gns_sat, hms2sod, read_site_list, MAX_THREAD, timeblock, mkdir, \
    get_grg_wsb, check_turboedit_log, check_brd_orbfit, backup_files, edit_ics, \
    GrtClockRepair, GrtTurboedit, GrtPreedit, GrtOi, GrtOrbfit, GrtEditres


def basic_args(default_args: dict):
    parser = argparse.ArgumentParser(description=default_args['dsc'])
    # Time argument
    parser.add_argument('-n', dest='num', type=int, default=1, help='number of process days')
    parser.add_argument('-l', dest='seslen', type=int, help='process time length (hours)')
    parser.add_argument('-i', dest='intv', type=int, help='process interval (seconds)')
    parser.add_argument('-t', dest='hms', nargs='+', help='begin date: hh mm ss')
    parser.add_argument('-sod', dest='sod', help='begin date: seconds of day')
    # Estimation argument
    parser.add_argument('-c', dest='obs_comb', help='observation combination')
    parser.add_argument('-est', dest='lsq_mode', help='estimator: LSQ or EPO')
    parser.add_argument('-sys', dest='sys', help='used GNSS observations, e.g. G/GC/GREC')
    parser.add_argument('-freq', dest='freq', type=int, help='used GNSS frequencies')
    parser.add_argument('-rt', dest='real_time', action='store_true', help='real-time processing')
    parser.add_argument('-lite', dest='lite_tb', action='store_true', help='lite mode for turboedit')
    parser.add_argument('-ultra', dest='ultra_sp3', action='store_true', help='use ultra sp3')
    # File argument
    parser.add_argument('-s', dest='f_list', help='site_list file')
    parser.add_argument('-cen', dest='cen', help='GNSS precise orbits and clocks')
    parser.add_argument('-bia', dest='bia', help='bias files')
    parser.add_argument('-cf', dest='cf', default=default_args['cf'], help='config file')
    parser.add_argument('-kp', dest='kp_dir', action='store_true', help='Keep the existing work dir')
    return parser


def get_args_config(args) -> GnssConfig:
    config = GnssConfig.from_file(args.cf)
    config.obs_comb = args.obs_comb if args.obs_comb else config.obs_comb
    config.orb_ac = args.cen if args.cen else config.orb_ac
    config.bia_ac = args.bia if args.bia else config.bia_ac
    if config.orb_ac == 'cod':
        config.bia_ac = 'COD'
    # if config.freq > 2:
    #     config.bia_ac = 'CAS'

    if args.sys:
        config.gsys = args.sys
    if args.freq:
        config.freq = args.freq
    if args.lsq_mode:
        config.lsq_mode = args.lsq_mode
    if args.intv:
        config.intv = args.intv

    # true if option in arg or config file is true
    config.lite_mode = config.lite_mode or args.lite_tb
    config.real_time = config.real_time or args.real_time
    config.ultra_sp3 = config.ultra_sp3 or args.ultra_sp3
    # set time
    sod = 0
    if args.sod:
        sod = args.sod
    elif args.hms:
        hh, mm, ss, *_ = args.hms + [0, 0]
        sod = hms2sod(hh, mm, ss)
    config.beg_time = GnssTime.from_ydoy(args.year, args.doy, sod)
    if args.seslen is not None:
        config.end_time = config.beg_time + 3600 * args.seslen - config.intv
    else:
        config.end_time = config.beg_time + 86400 - config.intv
    # set sites
    if args.f_list:
        config.site_list = read_site_list(args.f_list)
    elif config.site_file:
        config.site_list = read_site_list(config.site_file)
    return config


class ProcGen:
    default_args = {
        'dsc': 'GREAT Data Processing',
        'num': 1, 'seslen': 24, 'intv': 300, 'obs_comb': 'IF', 'est': 'LSQ', 'sys': 'G',
        'freq': 2, 'cen': 'com', 'bia': 'cas', 'cf': 'cf_pod.ini'
    }

    proj_id = ''

    required_subdir = ['log_tb', 'tmp', 'xml']
    required_opt = []
    required_file = ['rinexo']

    sat_rm = []

    def __init__(self, config: GnssConfig, ndays=1, kp_dir=False):
        self._config = config
        self._ndays = ndays
        self._kp_dir = kp_dir
        self._site_list = self._config.site_list
        self._intv = self._config.intv
        self._gsys = ''.join(self._config.gsys)
        self._workdir = self._config.workdir
        sat_rm = self._config.sat_rm
        for s in self._config.sys_rm:
            sat_rm.extend(gns_sat(s))
        sat_rm = list(set(sat_rm))
        self.sat_rm = sat_rm

    @classmethod
    def from_args(cls):
        args = cls.get_args(cls.default_args)
        cf = get_args_config(args)
        return cls(cf, args.num, args.kp_dir)

    @staticmethod
    def get_args(default_args):
        parser = basic_args(default_args)
        # Required argument
        parser.add_argument('-y', dest='year', type=int, required=True, help='begin date: year')
        parser.add_argument('-d', dest='doy', type=int, required=True, help='begin date: day of year')
        args = parser.parse_args()
        return args

    @property
    def nthread(self):
        return min(len(self._config.all_sites), MAX_THREAD)

    @property
    def base_dir(self):
        return self._config.base_dir

    @property
    def year(self):
        return self._config.beg_time.year

    @property
    def doy(self):
        return self._config.beg_time.doy

    def basic_check(self, opts=None, files=None):
        if files is None:
            files = []
        if opts is None:
            opts = []
        if not self._config.site_list:
            logging.error(f'cannot find site list in args or config.ini')
            return False
        return self._config.basic_check(opts, files)

    def set_workdir(self):
        if not self._config.workdir:
            self._workdir = os.path.join(self.base_dir, self.proj_id, str(self.year), f"{self.doy:0>3d}_{self._gsys}")
        else:
            self._workdir = self._config.workdir
        if not os.path.isdir(self._workdir):
            os.makedirs(self._workdir)
        else:
            if not self._kp_dir:
                shutil.rmtree(self._workdir)
                os.makedirs(self._workdir)

    def init_daily(self):
        # --- reset process scheme
        self._config.site_list = self._site_list
        self._config.sat_rm = self.sat_rm
        # self._config.crd_constr = 'EST'
        # self.config.change_data_path('rinexo', 'obs')
        self.set_workdir()
        os.chdir(self._workdir)
        mkdir(self.required_subdir)
        self._config.copy_sys_data()
        if self._config.upd_mode == 'IRC':
            get_grg_wsb(self._config)
        # --- daily check
        if self.basic_check(self.required_opt, self.required_file):
            logging.info("Basic check complete ^_^")
            self._config.write('config.ini')
            return True
        else:
            logging.critical("Basic check failed! skip to next day")
            return False

    def next_day(self):
        self._config.beg_time += 86400
        self._config.end_time += 86400
        self._ndays -= 1

    def prepare_obs(self):
        if self._config.lite_mode or self._config.real_time:
            logging.info("Real-time Turboedit mode...")
            return True
        if not self._config.ext_ambflag:
            logging.info(f"===> Preprocess RINEXO files with Clock-Repair and Turboedit\n{' ' * 36}"
                        f"number of receivers = {len(self._config.all_sites)}, number of threads = {self.nthread}")
            self._config.intv = min(30, self._intv)
            # GrtClockRepair(self._config, 'clockrepair', nmp=self.nthread).run()
            # self._config.change_data_path('rinexo', 'obs_trimcor')
            # if not self._config.basic_check(files=['rinexo']):
            #     return False
            tb_label = 'turboedit'
            GrtTurboedit(self._config, tb_label, nmp=self.nthread).run()
            self._config.intv = self._intv
            check_turboedit_log(self._config, self.nthread, label=tb_label)
        if self.basic_check(files=['ambflag']):
            logging.info("Ambflag is ok ^_^")
            return True
        else:
            logging.critical("NO ambflag files ! skip to next day")
            return False

    def prepare_ics(self):
        logging.info(f"===> Prepare initial orbits using broadcast ephemeris")
        if self._config.ext_ics:
            if self._config.get_xml_file('ics', check=True) and self._config.get_xml_file('ics', check=True):
                backup_files(self._config, ['ics', 'orb'])
                return True
            else:
                return False
        orb_ac = self._config.orb_ac
        self._config.orb_ac = 'brd'

        GrtPreedit(self._config).run()
        GrtOi(self._config, 'oi').run()
        GrtOrbfit(self._config, 'orbfit').run()
        GrtOi(self._config, 'oi').run()
        GrtOrbfit(self._config, 'orbfit').run()

        sat_rm = check_brd_orbfit(self._config.get_xml_file('orbdif')[0])
        self._config.sat_rm += sat_rm
        edit_ics(self._config.get_xml_file('ics')[0], sat_rm)
        GrtOi(self._config, 'oi').run()
        self._config.orb_ac = orb_ac
        backup_files(self._config, ['ics', 'orb'])
        return True

    def prepare(self):
        with timeblock('Finished prepare obs'):
            if not self.prepare_obs():
                return False
        return True

    def editres(self, bad=80, jump=80, nshort=600, edt_amb=False, all_sites=False):
        nmp = self.nthread if all_sites else 1
        kwargs = {'nmp': nmp, 'bad': bad, 'jump': jump, 'nshort': nshort, 'edt_amb': edt_amb, 'all_sites': all_sites}
        if self._config.obs_comb == 'IF':
            GrtEditres(self._config, 'editres12', mode='L12', freq='LC12', **kwargs).run()
            if self._config.freq > 2:
                GrtEditres(self._config, 'editres13', mode='L13', freq='LC13', **kwargs).run()
            if self._config.freq > 3:
                GrtEditres(self._config, 'editres14', mode='L14', freq='LC14', **kwargs).run()
            if self._config.freq > 4:
                GrtEditres(self._config, 'editres15', mode='L15', freq='LC15', **kwargs).run()
        else:
            GrtEditres(self._config, 'editres01', mode='L12', freq='L1', **kwargs).run()
            GrtEditres(self._config, 'editres02', mode='L12', freq='L2', **kwargs).run()
            if self._config.freq > 2:
                GrtEditres(self._config, 'editres03', mode='L13', freq='L3', **kwargs).run()
            if self._config.freq > 3:
                GrtEditres(self._config, 'editres04', mode='L14', freq='L4', **kwargs).run()
            if self._config.freq > 4:
                GrtEditres(self._config, 'editres05', mode='L15', freq='L5', **kwargs).run()
        self.basic_check(files=['ambflag'])

    def process_daily(self):
        raise NotImplementedError

    def save_results(self, **kwargs):
        pass

    def generate_products(self, **kwargs):
        pass

    def process_batch(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)8s: %(message)s')
        # ------- daily loop -------------
        while self._ndays > 0:
            if not self.init_daily():
                self.next_day()
                continue
            crt_time = self._config.beg_time
            # set logger
            logger = logging.getLogger()
            fh = logging.FileHandler(f"proc_{crt_time.year}{crt_time.doy:0>3d}.log")
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)8s: %(message)s'))
            logger.addHandler(fh)
            logging.info(f"------------------------------------------------------------------------\n{' ' * 36}"
                         f"===> Process {crt_time.year}-{crt_time.doy:0>3d}\n{' ' * 36}"
                         f"work directory = {self._workdir}")

            with timeblock("Finished prepare"):
                if not self.prepare():
                    logger.removeHandler(fh)
                    self.next_day()
                    continue

            with timeblock(f"Finished process {crt_time.year}-{crt_time.doy:0>3d}"):
                self.process_daily()

            # next day
            logging.info(f"------------------------------------------------------------------------\n")
            logger.removeHandler(fh)
            self.next_day()


if __name__ == '__main__':
    raise NotImplementedError

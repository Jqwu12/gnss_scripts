import os
import shutil
import logging
from proc_gen import ProcGen, basic_args, get_args_config
from funcs import timeblock, copy_result_files, GrtSp3orb, GrtOrbfitLeo, GrtPodleo, GrtOi, GrtAmbfixD


# Todo:  test 30h POD; test irc, osb, upd AR POD

class ProcLeo(ProcGen):
    default_args = {
        'dsc': 'LEO reduced dynamic POD Processing',
        'num': 1, 'seslen': 24, 'intv': 30, 'obs_comb': 'IF', 'est': 'LSQ', 'sys': 'G',
        'freq': 2, 'cen': 'grm', 'bia': '', 'cf': 'cf_leo.ini'
    }

    proj_id = 'LEO'

    required_subdir = ['log_tb', 'tmp', 'xml', 'orbdif']
    required_file = ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern', 'attitude']

    @classmethod
    def from_args(cls):
        args = cls.get_args(cls.default_args)
        cf = get_args_config(args)
        cf.site_list = []
        cf.leo_list = args.sat
        return cls(cf, args.num, args.kp_dir)

    @staticmethod
    def get_args(default_args):
        parser = basic_args(default_args)
        # Required argument
        parser.add_argument('-s', dest='sat', nargs='+', required=True, help='LEO satellite')
        parser.add_argument('-y', dest='year', type=int, required=True, help='begin date: year')
        parser.add_argument('-d', dest='doy', type=int, required=True, help='begin date: day of year')
        args = parser.parse_args()
        return args

    def set_workdir(self):
        if not self._config.workdir:
            self._workdir = os.path.join(self.base_dir, 'LEO', self._config.leo_sats[0],
                                         f'Dyn_{int(self._config.seslen / 3600) - 1:0>2d}h_{self._config.orb_ac}',
                                         str(self.year), f"{self.doy:0>3d}")
        else:
            self._workdir = self._config.workdir
        if not os.path.isdir(self._workdir):
            os.makedirs(self._workdir)
        else:
            if not self._kp_dir:
                shutil.rmtree(self._workdir)
                os.makedirs(self._workdir)

    def kin_pod(self):
        self._config.leo_mode = 'K'
        self._config.crd_constr = 'K'
        GrtSp3orb(self._config, 'sp3orb').run()
        GrtPodleo(self._config, 'podlsq_k').run()
        GrtPodleo(self._config, 'podlsq_k').run()
        GrtPodleo(self._config, 'podlsq_k').run()

    def prepare_ics(self):
        self.kin_pod()
        self._config.beg_time += 3600
        self._config.end_time -= 3600
        GrtSp3orb(self._config, 'sp3orb', sattype='leo').run()
        GrtOrbfitLeo(self._config, 'orbfit').run()
        copy_result_files(self._config, ['orbdif', 'ics'], 'K', 'leo')
        GrtOi(self._config, 'oi', sattype='leo').run()
        return True

    def prepare(self):
        with timeblock('Finished prepare obs'):
            if not self.prepare_obs():
                return False
        with timeblock('Finished prepare ics'):
            if not self.prepare_ics():
                return False
        return True

    def rd_pod(self, label='', fix_amb=False):
        self._config.leo_mode = 'D'
        self._config.crd_constr = 'EST'
        GrtPodleo(self._config, 'podlsq_d', fix_amb=fix_amb).run()
        GrtOi(self._config, 'oi', sattype='leo').run()
        GrtOrbfitLeo(self._config, 'orbfit').run()
        if label:
            copy_result_files(self._config, ['orbdif', 'ics'], label, 'leo')

    def ambfix(self):
        GrtAmbfixD(self._config, 'ambfix', stop=False).run()

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' ' * 36}"
                     f"Everything is ready: number of LEOs = {len(self._config.leo_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")
        self.rd_pod('D1')
        self.editres(bad=80, jump=80, nshort=120)
        self.rd_pod('D2')
        self.editres(bad=40, jump=40, nshort=120)
        self.rd_pod('D3')
        self.ambfix()
        self.rd_pod('AR', True)

        self._config.beg_time -= 3600
        self._config.end_time += 3600


if __name__ == '__main__':
    proc = ProcLeo.from_args()
    proc.process_batch()

import os
import sys
import shutil
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from proc_gen import ProcGen
from funcs import GnssConfig, GrtPpplsq, GrtAmbfix


class ProcPPP(ProcGen):

    description = 'GREAT Precise Point Positioning'
    default_config = 'cf_ppp.ini'

    def __init__(self, config: GnssConfig, ndays=1, kp_dir=False):
        super().__init__(config, ndays, kp_dir)
        self.required_subdir += ['enu', 'flt', 'ppp', 'ratio', 'ambupd', 'res', 'ambcon']
        self.required_opt += ['estimator']
        self.required_file += ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']
        self.proj_id = 'PPP'

    # def prepare(self):
    #     shutil.copy('/home/jqwu/projects/PPP/2021/preedit.xml', 'xml/preedit.xml')
    #     return super().prepare()

    def process_ppp(self, freq=None, obs_comb=None, fix=True):
        if freq is not None:
            self._config.freq = int(freq)
        if obs_comb is not None:
            self._config.obs_comb = str(obs_comb)
        amb = 'AR' if fix else 'F'
        GrtPpplsq(self._config, f'ppplsq_{self._config.freq}_{self._config.obs_comb}_{amb}', nmp=self.nthread, fix_amb=fix).run()

    def save_results(self, label):
        if not os.path.isdir('ratio'):
            os.makedirs('ratio')
        for site in self._config.site_list:
            f_ratio = f"ratio-{site.upper()}"
            if os.path.isfile(f_ratio):
                f_new = os.path.join('ratio', f"{f_ratio}-{label}")
                shutil.move(f_ratio, f_new)

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n"
                     f"{' '*36}Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")

        # self._config.obs_comb = 'IF'
        # self._config.copy_sys_data()
        #self._config.carrier_range = False
        self.process_ppp(freq=2, fix=False)
        self.process_ppp(freq=2, fix=True)
        # self._config.carrier_range = True
        # self.process_ppp(freq=2, fix=False)
        #self.process_ppp(freq=2, fix=True)
        # self.process_ppp(freq=3, fix=False)
        # self.process_ppp(freq=3, fix=True)

        # self._config.obs_comb = 'UC'
        # self._config.copy_sys_data()
        # self.process_ppp(freq=2, fix=False)
        # self.process_ppp(freq=2, fix=True)
        # self.process_ppp(freq=3, fix=False)
        # self.process_ppp(freq=3, fix=True)


if __name__ == '__main__':
    proc = ProcPPP.from_args()
    proc.process_batch()

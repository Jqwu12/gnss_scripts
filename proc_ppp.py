#!/home/jqwu/anaconda3/bin/python3
from funcs import gnss_run as gr
from proc_gen import ProcGen
import os
import logging


class ProcPpp(ProcGen):
    def __init__(self):
        super().__init__()

        self.default_args['dsc'] = "GREAT Precise Point Positioning"
        self.default_args['intv'] = 30
        self.default_args['freq'] = 3
        self.default_args['obs_comb'] = 'UC'
        self.default_args['est'] = 'EPO'
        self.default_args['cf'] = 'cf_ppp.ini'

        self.required_subdir = ['log_tb', 'enu', 'flt', 'ppp', 'ambupd', 'res', 'tmp']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'PPP')

    def process_ppp(self, freq=None, obs_comb=None, fix=True):
        if freq:
            self.config.update_gnssinfo(freq=int(freq))
        if obs_comb:
            self.config.update_gnssinfo(obs_comb=str(obs_comb))
            self.config.copy_sys_data()

        if not fix:
            gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', newxml=True, nthread=self.nthread(),
                         fix_mode="NO", label=f"ppplsq_{obs_comb}_{freq}_F", xmldir=self.xml_dir)
        else:
            gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', newxml=True, nthread=self.nthread(),
                         fix_mode="SEARCH", label=f"ppplsq_{obs_comb}_{freq}_AR", xmldir=self.xml_dir)

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(proc.config.stalist())}, "
                     f"number of satellites = {len(proc.config.all_gnssat())}")

        self.process_ppp(obs_comb='IF', freq=2, fix=False)
        self.process_ppp(obs_comb='IF', freq=2, fix=True)
        self.process_ppp(obs_comb='IF', freq=3, fix=False)
        self.process_ppp(obs_comb='IF', freq=3, fix=True)

        self.process_ppp(obs_comb='UC', freq=2, fix=False)
        self.process_ppp(obs_comb='UC', freq=2, fix=True)
        self.process_ppp(obs_comb='UC', freq=3, fix=False)
        self.process_ppp(obs_comb='UC', freq=3, fix=True)


if __name__ == '__main__':
    proc = ProcPpp()
    proc.process_batch()

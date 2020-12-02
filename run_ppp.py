#!/home/jqwu/anaconda3/bin/python3
import gnss_run as gr
import gnss_tools as gt
from run_gen import RunGen
import os
import logging


class RunPpp(RunGen):
    def __init__(self, config=None):
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
        if not fix:
            gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', newxml=True, nthread=self.nthread(),
                         fix_mode="NO", label='ppplsq')
        else:
            gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', newxml=True, nthread=self.nthread(),
                         fix_mode="SEARCH", label='ppplsq')

    def process_daily(self):
        with gt.timeblock("PPP-UC-3-AR"):
            self.process_ppp(obs_comb='UC', freq=3, fix=True)

        with gt.timeblock("PPP-UC-3-F"):
            self.process_ppp(obs_comb='UC', freq=3, fix=False)

        with gt.timeblock("PPP-UC-2-AR"):
            self.process_ppp(obs_comb='UC', freq=2, fix=True)

        with gt.timeblock("PPP-UC-2-F"):
            self.process_ppp(obs_comb='UC', freq=2, fix=False)

        with gt.timeblock("PPP-IF-3-AR"):
            self.process_ppp(obs_comb='IF', freq=3, fix=True)

        with gt.timeblock("PPP-IF-3-F"):
            self.process_ppp(obs_comb='IF', freq=3, fix=False)

        with gt.timeblock("PPP-IF-2-AR"):
            self.process_ppp(obs_comb='IF', freq=2, fix=True)

        with gt.timeblock("PPP-IF-2-F"):
            self.process_ppp(obs_comb='IF', freq=2, fix=False)


if __name__ == '__main__':
    proc = RunPpp()
    proc.process_batch()

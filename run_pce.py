#!/home/jqwu/anaconda3/bin/python3
import gnss_tools as gt
import gnss_run as gr
from run_gen import RunGen
import os
import logging


class RunPce(RunGen):
    def __init__(self, config=None):
        super().__init__()

        self.default_args['dsc'] = "GREAT Precise Clock Estimation"
        self.default_args['intv'] = 300
        self.default_args['freq'] = 2
        self.default_args['obs_comb'] = 'IF'
        self.default_args['cf'] = 'cf_pce.ini'

        self.required_subdir = ['log_tb', 'clkdif', 'tmp']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'sp3', 'biabern']

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'PCE')

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")

        with gt.timeblock("Precise clock estimation"):
            gr.run_great(self.grt_bin, 'great_pcelsq', self.config, mode='PCE_EST', label='pcelsq')
        gr.run_great(self.grt_bin, 'great_clkdif', self.config, label='clkdif')


if __name__ == '__main__':
    proc = RunPce()
    proc.process_batch()

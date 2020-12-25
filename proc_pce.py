#!/home/jqwu/anaconda3/bin/python3
from funcs import gnss_tools as gt, gnss_run as gr
from proc_gen import ProcGen
import os
import logging


class ProcPce(ProcGen):
    def __init__(self):
        super().__init__()

        self.default_args['dsc'] = "GREAT Precise Clock Estimation"
        self.default_args['intv'] = 300
        self.default_args['freq'] = 2
        self.default_args['obs_comb'] = 'IF'
        self.default_args['cf'] = 'cf_pce.ini'

        self.required_subdir = ['log_tb', 'clkdif', 'tmp']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'sp3', 'biabern']

        self.ref_cen = ['com', 'gbm', 'wum']

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'PCE')

    def evl_clkdif(self, label=None):
        for c in self.ref_cen:
            self.config.update_process(cen=c)
            gr.run_great(self.grt_bin, 'great_clkdif', self.config, label='clkdif', xmldir=self.xml_dir, stop=False)
            if label:
                gt.copy_result_files(self.config, ['clkdif'], label, 'gns')

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")

        self.config.update_gnssinfo(freq=2)
        self.config.update_band('G', '12')  # chang GPS bands to 1 2
        gr.run_great(self.grt_bin, 'great_pcelsq', self.config, mode='PCE_EST', label='pcelsq', xmldir=self.xml_dir)
        gt.copy_result_files(self.config, ['satclk', 'recclk', 'recover'], 'b12')  # save 12 results
        self.evl_clkdif('b12')

        self.config.update_band('G', '15')  # chang GPS bands to 1 5
        gr.run_great(self.grt_bin, 'great_pcelsq', self.config, mode='PCE_EST', label='pcelsq', xmldir=self.xml_dir)
        gt.copy_result_files(self.config, ['satclk', 'recclk', 'recover'], 'b15')  # save 15 results
        self.evl_clkdif('b15')


if __name__ == '__main__':
    proc = ProcPce()
    proc.process_batch()

#!/home/jqwu/anaconda3/bin/python3
from gnss_time import hms2sod
import gnss_tools as gt
import gnss_run as gr
from run_gen import RunGen
import os
import shutil
import logging
import platform


class RunTurboedit(RunGen):
    def __init__(self, config=None):
        super().__init__()

        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'PCE')
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'biabern']

        self.default_args['dsc'] = "GREAT Turboedit"
        self.default_args['intv'] = 30
        self.default_args['freq'] = 3
        self.default_args['cf'] = 'cf_ppp.ini'

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'TB')


if __name__ == '__main__':
    proc = RunTurboedit()
    proc.process_batch()

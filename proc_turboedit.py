#!/home/jqwu/anaconda3/bin/python3
from proc_gen import ProcGen
import os


class ProcTurboedit(ProcGen):
    def __init__(self):
        super().__init__()

        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'TB')
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
    proc = ProcTurboedit()
    proc.process_batch()

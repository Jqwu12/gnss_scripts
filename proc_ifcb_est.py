from funcs import gnss_tools as gt, gnss_run as gr
from proc_upd import ProcUpd
import os
import logging


class ProcIfcb(ProcUpd):
    def __init__(self):
        super().__init__()

        self.default_args['dsc'] = "GREAT IFCB Estimation"
        self.default_args['intv'] = 30
        self.default_args['freq'] = 3
        self.default_args['obs_comb'] = 'UC'
        self.default_args['cf'] = 'cf_ifcb.ini'

        self.keep_dir = True
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'biabern']

    def process_upd(self, obs_comb=None):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")
        upd_results = []

        if self.process_ifcb():
            upd_results.append('ifcb')

        return upd_results

    def process_daily(self):
        self.save_results(self.process_upd())


if __name__ == '__main__':
    proc = ProcIfcb()
    proc.process_batch()

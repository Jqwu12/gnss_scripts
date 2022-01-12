import logging
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import GnssConfig
from proc_upd import ProcUpd


class ProcIfcb(ProcUpd):

    description = 'GREAT IFCB Estimation'
    default_config = 'cf_ifcb.ini'

    def __init__(self, config: GnssConfig, ndays=1, kp_dir=False):
        super().__init__(config, ndays, kp_dir)
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'biabern']

    def process_upd(self, obs_comb=None, fix=False):
        return ['ifcb'] if self.process_ifcb() else []

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")
        self.save_results(self.process_upd())


if __name__ == '__main__':
    proc = ProcIfcb.from_args()
    proc.process_batch()

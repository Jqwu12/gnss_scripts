import logging
from proc_upd import ProcUpd


class ProcIfcb(ProcUpd):

    default_args = {
        'dsc': 'GREAT IFCB Estimation',
        'num': 1, 'seslen': 24, 'intv': 30, 'obs_comb': 'IF', 'est': 'LSQ', 'sys': 'G',
        'freq': 3, 'cen': 'com', 'bia': 'cas', 'cf': 'cf_ifcb.ini'
    }

    required_opt = ['estimator']
    required_file = ['rinexo', 'biabern']

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

import os
import sys
import shutil
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from proc_gen import ProcGen
from funcs import GnssConfig, timeblock, copy_dir, copy_result_files_to_path


class ProcPrepare(ProcGen):

    description = 'GREAT preprocess observations and generate init orbits'
    default_config = 'cf_prepare.ini'

    def __init__(self, config: GnssConfig, ndays=1, kp_dir=False):
        super().__init__(config, ndays, kp_dir)
        self.required_subdir += ['orbdif']
        self.required_opt += ['estimator']
        self.required_file += ['rinexo', 'rinexn']
        self.proj_id = 'PREPARE'

    def prepare(self):
        with timeblock('Finished prepare ics'):
            # return self.prepare_ics()
            self._config.intv = 300
            if not self.prepare_ics():
                return False
        return super().prepare()

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")
        ics_dir = os.path.join(self._config.gnss_data, 'ics', str(self.year))
        logging.info(f"===> Copy ics and orb file to {ics_dir}")
        copy_result_files_to_path(self._config, ['ics', 'orb'], ics_dir)

        ambflag_dir = os.path.join(self._config.gnss_data, 'obs', 'log_tb', str(self.year), f'{self.doy:0>3d}')
        logging.info(f"===> Copy ambflag files to {ambflag_dir}")
        copy_dir('log_tb', ambflag_dir)


if __name__ == '__main__':
    proc = ProcPrepare.from_args()
    proc.process_batch()

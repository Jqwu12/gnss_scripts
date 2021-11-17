import os
import sys
import shutil
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from proc_gen import ProcGen
from funcs import timeblock, copy_dir, copy_result_files_to_path


class ProcPrepare(ProcGen):
    default_args = {
        'dsc': 'GREAT preprocess observations and generate init orbits',
        'num': 1, 'seslen': 24, 'intv': 300, 'obs_comb': 'IF', 'est': 'LSQ', 'sys': 'G',
        'freq': 2, 'cen': 'com', 'bia': '', 'cf': 'cf_prepare.ini'
    }

    proj_id = 'PREPARE'

    required_subdir = ['log_tb', 'tmp', 'xml', 'orbdif', 'clkdif', 'figs']
    required_opt = ['estimator']
    required_file = ['rinexo', 'rinexn']

    sat_rm = ['C01', 'C02', 'C03', 'C04', 'C05', 'C59', 'C60']

    def prepare(self):
        with timeblock('Finished prepare ics'):
            #return self.prepare_ics()
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
        #return 

        ambflag_dir = os.path.join(self._config.gnss_data, 'obs', 'log_tb', str(self.year), f'{self.doy:0>3d}')
        logging.info(f"===> Copy ambflag files to {ambflag_dir}")
        copy_dir('log_tb', ambflag_dir)


if __name__ == '__main__':
    proc = ProcPrepare.from_args()
    proc.process_batch()

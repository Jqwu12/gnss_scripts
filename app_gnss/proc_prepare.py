import os
import sys
import shutil
import logging

from sympy import true
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from proc_gen import ProcGen
from funcs import GnssConfig, timeblock, copy_dir, copy_result_files_to_path, GrtMwobs


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
        #return super().prepare()
        with timeblock('Finished prepare ics'):
            self._config.intv = 300
            if not self.prepare_ics():
                return False
        # return True
        return super().prepare()

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")

        # GrtMwobs(self._config, 'mwobs').run()
        # mw_dir = self._config.get_xml_file_str('mw_dir', sec='output_files')
        # logging.info(f"===> Copy mw obs to {mw_dir}")
        # copy_dir('mw_obs', mw_dir)

        ics_dir = self._config.get_xml_file_str('ics_dir', sec='output_files')
        logging.info(f"===> Copy ics and orb file to {ics_dir}")
        copy_result_files_to_path(self._config, ['ics', 'orb'], ics_dir)

        ambflag_dir = self._config.get_xml_file_str('ambflag_out', sec='output_files')
        logging.info(f"===> Copy ambflag files to {ambflag_dir}")
        copy_dir('log_tb', ambflag_dir)


if __name__ == '__main__':
    proc = ProcPrepare.from_args()
    proc.process_batch()

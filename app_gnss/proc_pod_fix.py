import os
import sys
import shutil
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app_gnss.proc_pod import ProcPod
from funcs import GnssConfig, timeblock, copy_result_files, GrtAmbfix


class ProcPodFix(ProcPod):

    description = 'GREAT GNSS Precise Orbit Determination (fix solution)'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
    default_config = 'cf_pod_fix.ini'
    ref_cen = ['com', 'gbm', 'wum', 'esm']

    def __init__(self, config: GnssConfig, ndays=1, kp_dir=False):
        super().__init__(config, ndays, kp_dir)
        self.required_subdir += ['orbdif', 'clkdif', 'ambupd']
        self.required_opt += ['estimator']
        self.required_file += ['rinexo', 'rinexn', 'biabern']
        self.proj_id = 'POD_FIX'

    def process_ambfix(self):
        #gsys = ''.join([s for s in self._gsys if s != "R"])
        #self._config.gsys = gsys
        GrtAmbfix(self._config, None, 'ambfix').run()
        #self._config.gsys = self._gsys

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")
        
        logging.info(f"===> 1st iteration for precise orbit determination")
        self._config.ambupd = True
        with timeblock('Finished fixed POD'):
            self.process_ambfix()
            if self._config.amb_type.upper() == "UD":
                self._config.carrier_range = True
                if not self.process_float_pod('AR', True, True):
                    return
            else:
                if not self.process_fix_pod('AR', True, True):
                    return
            copy_result_files(self._config, ['ics', 'orb', 'satclk', 'recclk', 'recover'], 'AR')
        
        self.save_results(['AR'])


if __name__ == '__main__':
    proc = ProcPodFix.from_args()
    proc.process_batch()

import os
import sys
import shutil
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app_gnss.proc_pod import ProcPod
from funcs import GnssConfig, read_site_list, timeblock, copy_result_files, backup_files, backup_dir, recover_files, GrtAmbfix, GrtPodlsq


class ProcPodFix(ProcPod):

    description = 'GREAT GNSS Precise Orbit Determination (fix solution)'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
    default_config = 'cf_pod_fix.ini'
    ref_cen = ['com', 'gbm', 'wum', 'esm']

    def __init__(self, config: GnssConfig, ndays=1, kp_dir=False):
        super().__init__(config, ndays, kp_dir)
        self.required_subdir += ['orbdif', 'clkdif', 'ambupd', 'ambinp', 'ambcon']
        self.required_opt += ['estimator']
        self.required_file += ['rinexo', 'rinexn', 'biabern']
        self.proj_id = 'POD_FIX'

    def process_ambfix(self):
        #gsys = ''.join([s for s in self._gsys if s != "R"])
        #self._config.gsys = gsys
        freq = self._config.freq
        # self._config.freq = min(freq, 2)
        if self._config.obs_comb == 'IF':
            self._config.intv = 30
        #self._config.end_time = self._config.beg_time + 86400 - 30
        GrtAmbfix(self._config, None, 'ambfix').run()
        self._config.intv = self._intv
        #self._config.end_time = self._config.beg_time + 86400 - self._intv
        #self._config.gsys = self._gsys
        self._config.freq = freq

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")
        
        # if self._config.obs_comb == 'UC' and self._config.amb_type.upper() != "UD":
        #     if not self.process_float_pod('F3', True, True):
        #         return
        #     copy_result_files(self._config, ['ics', 'orb', 'satclk', 'recclk', 'recover'], 'F3')
        #     self.save_results(['F3'])
        #     return

        #self._config.ambupd = True
        self.process_ambfix()
        if self._config.amb_type.upper() == "UD":

            backup_files(self._config, ['ics', 'orb', 'satclk', 'recclk'])
            self._config.carrier_range = True
            logging.info(f"===> 1st iteration for precise orbit determination")
            if not self.process_float_pod('AR', True, True):
                return

            # recover_files(self._config, ['ics', 'orb', 'satclk', 'recclk'])
            # logging.info(f"===> 2nd iteration for precise orbit determination")
            # self.editres(jump=50, edt_amb=True)
            # if not self.process_float_pod('AR', True, True):
            #     return
            # copy_result_files(self._config, ['recover', 'orb'], 'AR')

            # logging.info(f"===> 3rd iteration for precise orbit determination")
            # self.editres(jump=40, edt_amb=True)
            # if not self.process_float_pod('AR3', True, True):
            #     return
        else:
            logging.info(f"===> 1st iteration for precise orbit determination")
            if not self.process_fix_pod('AR', True, True):
                return
            
        copy_result_files(self._config, ['ics', 'orb', 'satclk', 'recclk', 'recover'], 'AR')
        self.save_results(['AR'])


if __name__ == '__main__':
    proc = ProcPodFix.from_args()
    proc.process_batch()

import logging
import sys
import os
import shutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from proc_gen import ProcGen
from funcs import GnssConfig, check_res_sigma, GrtPpplsq, GrtAmbfix, backup_dir, copy_ambflag_from


class ProcCarRng(ProcGen):

    description = 'GREAT Carrier-range observation generation'
    default_config = 'cf_carrng.ini'

    def __init__(self, config: GnssConfig, ndays=1, kp_dir=False):
        super().__init__(config, ndays, kp_dir)
        self.required_subdir += ['ambupd', 'res', 'ambcon', 'enu']
        self.required_opt += ['estimator']
        self.required_file += ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']
        self.proj_id = 'CarRng'

    def init_daily(self):
        self._config.carrier_range = False
        self._config.carrier_range_out = True
        return super().init_daily()

    def ppp_clean(self):
        logging.info(f"===> Detect outliers in carrier-range by PPP")
        # self._config.crd_constr = 'FIX'
        self._config.carrier_range = True
        GrtPpplsq(self._config, 'ppplsq', nmp=self.nthread).run()
        #check_res_sigma(self._config, max_sig=12)
        #self.editres(jump=40, edt_amb=True, all_sites=True)

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")

        logging.info(f"===> Calculate float ambiguities by precise point positioning")
        # GrtPpplsq(self._config, 'ppplsq_F', nmp=self.nthread).run()
        # self.basic_check(files=['recover_all', 'ambupd_in'])
        # backup_dir('log_tb', 'log_tb_save')
        # backup_dir('res', 'res_F0')
        # self.editres(bad=80, jump=80, nshort=600, all_sites=True)

        # GrtPpplsq(self._config, 'ppplsq_F', nmp=self.nthread).run()
        # # check_res_sigma(self._config)
        # self.basic_check(files=['recover_all', 'ambupd_in'])
        # backup_dir('log_tb', 'log_tb_save1')
        # backup_dir('res', 'res_F1')
        # self.editres(bad=40, jump=40, nshort=600, all_sites=True)
        
        GrtPpplsq(self._config, 'ppplsq_F', nmp=self.nthread).run()
        self.basic_check(files=['recover_all', 'ambupd_in'])
        GrtAmbfix(self._config, 'SD', 'ambfix', nmp=self.nthread, all_sites=True).run()
        backup_dir('log_tb', 'log_tb_edtres')
        backup_dir('res', 'res_F')
        backup_dir('ambcon', 'ambcon_SD')

        GrtPpplsq(self._config, 'ppplsq_AR', nmp=self.nthread, fix_amb=True).run()
        check_res_sigma(self._config)
        backup_dir('res', 'res_AR')
        self.basic_check(files=['recover_all', 'ambupd_in'])

        logging.info(f"===> Fix UD ambiguities of each site")
        GrtAmbfix(self._config, 'UD', 'ambfix', nmp=self.nthread, all_sites=True).run()
        
        self.ppp_clean()


if __name__ == '__main__':
    proc = ProcCarRng.from_args()
    proc.process_batch()

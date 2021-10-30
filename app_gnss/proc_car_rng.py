import logging
import sys
import os
import shutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from proc_gen import ProcGen
from funcs import check_res_sigma, GrtPpplsq, GrtAmbfix, backup_dir, copy_ambflag_from


class ProcCarRng(ProcGen):

    default_args = {
        'dsc': 'GREAT Carrier-range observation generation',
        'num': 1, 'seslen': 24, 'intv': 30, 'obs_comb': 'UC', 'est': 'LSQ', 'sys': 'G',
        'freq': 3, 'cen': 'com', 'bia': '', 'cf': 'cf_carrng.ini'
    }

    proj_id = 'CarRng'

    required_subdir = ['log_tb', 'xml', 'ambupd', 'res', 'tmp', 'ambcon']
    required_opt = ['estimator']
    required_file = ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']

    def init_daily(self):
        self._config.carrier_range = False
        self._config.carrier_range_out = True
        return super().init_daily()

    def ppp_clean(self):
        logging.info(f"===> Detect outliers in carrier-range by PPP")
        # self._config.crd_constr = 'FIX'
        self._config.carrier_range = True
        GrtPpplsq(self._config, 'ppplsq', nmp=self.nthread).run()
        check_res_sigma(self._config)
        self.editres(jump=40, edt_amb=True, all_sites=True)
        
    # def prepare_obs(self):
    #     shutil.rmtree('log_tb')
    #     os.makedirs('log_tb')
    #     ambflagdir = os.path.join(self.base_dir, 'POD', str(self.year), f"{self.doy:0>3d}_GEC_2_IF_new", 'log_tb')
    #     copy_ambflag_from(ambflagdir)
    #     if self.basic_check(files=['ambflag']):
    #         logging.info("Ambflag is ok ^_^")
    #         return True
    #     else:
    #         logging.critical("NO ambflag files ! skip to next day")
    #         return False

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")

        logging.info(f"===> Calculate float ambiguities by precise point positioning")
        # GrtPpplsq(self._config, 'ppplsq_F', nmp=self.nthread).run()
        # self.basic_check(files=['recover_all', 'ambupd_in'])
        backup_dir('log_tb', 'log_tb_save')
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
        self.basic_check(files=['recover_all', 'ambupd_in'])

        logging.info(f"===> Fix UD ambiguities of each site")
        GrtAmbfix(self._config, 'UD', 'ambfix', nmp=self.nthread, all_sites=True).run()
        
        self.ppp_clean()


if __name__ == '__main__':
    proc = ProcCarRng.from_args()
    proc.process_batch()

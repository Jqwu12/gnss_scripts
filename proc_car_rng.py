from proc_upd import ProcUpd
from funcs import gnss_tools as gt, gnss_run as gr
import os
import logging


class ProcCarRng(ProcUpd):
    def __init__(self):
        super().__init__()

    # def prepare(self):
    #     return True

    def process_ppp(self):
        logging.info(f"===> Calculate float ambiguities by precise point positioning")
        gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', nthread=self.nthread(), fix_mode="NO",
                     label='ppplsq', xmldir=self.xml_dir)
        self.config.basic_check(files=['recover_all', 'ambupd_in'])

        self.process_edtres(bad=80, jump=80, nshort=750, all_sites=True)

        gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', nthread=self.nthread(), fix_mode="NO",
                     use_res_crd=True, label='ppplsq', xmldir=self.xml_dir)
        self.config.basic_check(files=['recover_all', 'ambupd_in'])
        gt.check_res_sigma(self.config)

        self.process_edtres(bad=40, jump=40, nshort=750, all_sites=True)

    def ppp_clean(self):
        logging.info(f"===> Detect outliers in carrier-range by PPP")
        self.config.update_process(crd_constr='FIX')
        self.config.update_process(apply_carrier_range='true', append=True)
        gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', nthread=self.nthread(),
                     fix_mode="NO", use_res_crd=True, label='ppplsq', xmldir=self.xml_dir)
        self.process_edtres(jump=50, edt_amb=True, all_sites=True)

    def process_daily(self):
        self.config.update_process(apply_carrier_range='false', append=True)
        self.config.update_ambiguity(carrier_range='YES', append=True)
        super().process_upd(obs_comb='UC')
        # gt.backup_dir('ambupd', 'ambupd_save')
        # # self.ppp_clean()
        # logging.info(f"===> Generate RINEX Carrier-range observation")
        # gr.run_great(self.grt_bin, "great_convobs", self.config, nthread=self.nthread(),
        #              label='convobs', xmldir=self.xml_dir)


if __name__ == '__main__':
    proc = ProcCarRng()
    proc.process_batch()

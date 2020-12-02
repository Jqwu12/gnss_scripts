#!/home/jqwu/anaconda3/bin/python3
import gnss_tools as gt
import gnss_run as gr
from run_gen import RunGen
from constants import get_gns_name
import os
import logging


class RunUpd(RunGen):
    def __init__(self):
        super().__init__()

        self.default_args['dsc'] = "GREAT Uncalibrated Phase Delay Estimation"
        self.default_args['intv'] = 30
        self.default_args['freq'] = 3
        self.default_args['obs_comb'] = 'UC'
        self.default_args['cf'] = 'cf_upd.ini'

        self.required_subdir = ['log_tb', 'enu', 'flt', 'ppp', 'ambupd', 'res', 'tmp']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']

    def init_proc(self, config=None):
        super().init_proc(config)
        if self.args.freq > 3 and self.args.obs_comb != "UC":
            raise SystemExit("4- and 5-frequency UPD estimation currently only supports uncombined observation model")

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'UPD')

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")
        upd_results = []

        # with gt.timeblock("Finished IFCB estimation"):
        #     if self.args.freq > 2 and "G" in self.args.sys:
        #         self.config.update_process(sys='G')
        #         gt.run_great(self.grt_bin, 'great_updlsq', self.config, mode='ifcb', label="ifcb")
        #         self.config.update_process(sys=self.args.sys)
        #         upd_results.append('ifcb')

        logging.info(f"===> Calculate float ambiguities by precise point positioning")
        gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', nthread=self.nthread(), fix_mode="NO",
                     label='ppplsq')

        for gsys in self.args.sys:
            self.config.update_process(sys=gsys)
            mfreq = self.config.gnsfreq(gsys)
            logging.info(f"===> Start to process {get_gns_name(gsys)} UPD")
            if mfreq == 5:
                gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='EWL25', label=f"upd_ewl25_{gsys}")
                if 'upd_ewl25' not in upd_results:
                    upd_results.append('upd_ewl25')

            if mfreq >= 4:
                gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='EWL24', label=f"upd_ewl24_{gsys}")
                if 'upd_ewl24' not in upd_results:
                    upd_results.append('upd_ewl24')

            if mfreq >= 3:
                gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='EWL', label=f"upd_ewl_{gsys}")
                if 'upd_ewl' not in upd_results:
                    upd_results.append('upd_ewl')

            gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='WL', label=f"upd_wl_{gsys}")
            if 'upd_wl' not in upd_results:
                upd_results.append('upd_wl')

            gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='NL', label=f"upd_nl_{gsys}")
            if 'upd_nl' not in upd_results:
                upd_results.append('upd_nl')

        # Merge multi-GNSS UPD
        if len(self.args.sys) > 1:
            logging.info(f"===> Merge UPD: {gt.list2str(upd_results)}")
            gt.merge_upd_all(self.config, self.args.sys)

        # Copy results
        upd_data = self.config.config.get("common", "upd_data")
        logging.info(f"===> Copy UPD results to {upd_data}")
        gt.copy_result_files_to_path(self.config, upd_results, os.path.join(upd_data, f"{self.config.beg_time().year}"))

    def ppp_clean(self):
        # detect outliers in carrier-range by PPP
        if not os.path.isdir("ambupd_save"):
            os.rename("ambupd", "ambupd_save")
        self.config.update_process(crd_constr='FIX')
        self.config.update_process(apply_carrier_range='true', append=True)
        with gt.timeblock("Finished PPP"):
            gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', nthread=self.nthread(), fix_mode="NO",
                         use_res_crd=True, label='ppplsq')
        gr.run_great(self.grt_bin, 'great_editres', self.config, nthread=self.nthread(), jump=50,
                     mode="L12", edt_amb=True, all_sites=True, label='editres12')
        if self.args.freq > 2:
            gr.run_great(self.grt_bin, 'great_editres', self.config, nthread=self.nthread(), jump=50,
                         mode="L13", edt_amb=True, all_sites=True, label='editres13')

    def process_carrier_range(self):
        # not test yet!
        self.process_daily()
        self.ppp_clean()
        gr.run_great(self.grt_bin, "great_convobs", self.config, nthread=self.nthread(), label='convobs')


if __name__ == '__main__':
    proc = RunUpd()
    proc.process_batch()

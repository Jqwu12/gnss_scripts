#!/home/jqwu/anaconda3/bin/python3
from funcs import gnss_tools as gt, gnss_run as gr
from proc_gen import ProcGen
from funcs.constants import get_gns_name
import os
import logging


class ProcUpd(ProcGen):
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

    # def init_proc(self, config=None):
    #     super().init_proc(config)
    #     if self.args.freq > 3 and self.args.obs_comb != "UC":
    #         raise SystemExit("4- and 5-frequency UPD estimation currently only supports uncombined observation model")

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'UPD')

    def process_ppp(self):
        logging.info(f"===> Calculate float ambiguities by precise point positioning")
        gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', nthread=self.nthread(), fix_mode="NO",
                     label='ppplsq', xmldir=self.xml_dir)

    def process_upd(self, obs_comb=None):
        if obs_comb:
            self.config.update_gnssinfo(obs_comb=obs_comb)
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")
        upd_results = []

        f_ifcb = self.config.get_filename('ifcb', check=True)
        # if no ifcb file in current dir, run ifcb estimation
        if not f_ifcb:
            if self.args.freq > 2 and "G" in self.args.sys:
                with gt.timeblock("Finished IFCB estimation"):
                    self.config.update_process(sys='G')
                    gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='ifcb', label="ifcb", xmldir=self.xml_dir)
                    self.config.update_process(sys=self.args.sys)
                    upd_results.append('ifcb')

        self.process_ppp()

        for gsys in self.args.sys:
            self.config.update_process(sys=gsys)
            mfreq = self.config.gnsfreq(gsys)
            logging.info(f"===> Start to process {get_gns_name(gsys)} UPD")
            if mfreq == 5:
                gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='EWL25',
                             label=f"upd_ewl25_{gsys}", xmldir=self.xml_dir)
                if 'upd_ewl25' not in upd_results:
                    upd_results.append('upd_ewl25')

            if mfreq >= 4:
                gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='EWL24',
                             label=f"upd_ewl24_{gsys}", xmldir=self.xml_dir)
                if 'upd_ewl24' not in upd_results:
                    upd_results.append('upd_ewl24')

            if mfreq >= 3:
                gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='EWL',
                             label=f"upd_ewl_{gsys}", xmldir=self.xml_dir)
                if 'upd_ewl' not in upd_results:
                    upd_results.append('upd_ewl')

            gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='WL',
                         label=f"upd_wl_{gsys}", xmldir=self.xml_dir)
            if 'upd_wl' not in upd_results:
                upd_results.append('upd_wl')

            gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='NL',
                         label=f"upd_nl_{gsys}", xmldir=self.xml_dir)
            if 'upd_nl' not in upd_results:
                upd_results.append('upd_nl')

        # Merge multi-GNSS UPD
        if len(self.args.sys) > 1:
            logging.info(f"===> Merge UPD: {gt.list2str(upd_results)}")
            gt.merge_upd_all(self.config, self.args.sys, upd_results)

        return upd_results

    def save_results(self, upd_results):
        # Copy results
        upd_data = self.config.config.get("common", "upd_data")
        logging.info(f"===> Copy UPD results to {upd_data}")
        gt.copy_result_files_to_path(self.config, upd_results, os.path.join(upd_data, f"{self.config.beg_time().year}"))

    def process_daily(self):
        with gt.timeblock("Finish process UC upd"):
            upd_results = self.process_upd(obs_comb='UC')
            self.save_results(upd_results)
            gt.backup_dir('ambupd', 'ambupd_UC')

        with gt.timeblock("Finish process IF upd"):
            upd_results = self.process_upd(obs_comb='IF')
            self.save_results(upd_results)
            gt.backup_dir('ambupd', 'ambupd_IF')


if __name__ == '__main__':
    proc = ProcUpd()
    proc.process_batch()

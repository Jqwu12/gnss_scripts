#!/home/jqwu/anaconda3/bin/python3
from funcs import gnss_tools as gt, gnss_run as gr
from proc_gen import ProcGen
import os
import logging


class ProcGnsPod(ProcGen):
    def __init__(self):
        super().__init__()

        self.default_args['dsc'] = "GREAT GNSS Precise Orbit Determination"
        self.default_args['cf'] = 'cf_gnspod.ini'

        self.required_subdir = ['log_tb', 'tmp', 'orbdif', 'clkdif']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'sp3', 'biabern']

        self.ref_cen = ['com', 'gbm', 'wum']

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'POD')
        self.result_dir = os.path.join(self.proj_dir, f"results_{self.args.sys}")

    def init_daily(self, crt_time, seslen):
        self.config.update_timeinfo(crt_time, crt_time + (seslen - self.args.intv), self.args.intv)
        self.config.update_stalist(self.sta_list)
        self.config.update_gnssinfo(sat_rm=['C01', 'C02', 'C03', 'C04', 'C05'])
        # self.config.change_data_path('rinexo', 'obs')
        self.config.update_process(crd_constr='EST')

    def prepare(self):
        with gt.timeblock("Finished prepare obs"):
            if not self.prepare_obs():
                return False

        with gt.timeblock("Finished prepare ics"):
            if not self.prepare_ics():
                return False

        return True

    def evl_orbdif(self, label=None):
        for c in self.ref_cen:
            self.config.update_process(cen=c)
            gr.run_great(self.grt_bin, 'great_orbdif', self.config, label='orbdif', xmldir=self.xml_dir, stop=False)
            gr.run_great(self.grt_bin, 'great_clkdif', self.config, label='clkdif', xmldir=self.xml_dir, stop=False)
            if label:
                gt.copy_result_files(self.config, ['orbdif', 'clkdif'], label, 'gns')

    def detect_outliers(self):
        for i in range(4):
            if i != 0:
                logging.info(f"reprocess-{i} great_podlsq due to bad stations or satellites")
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', str_args="-brdm",
                         label='podlsq', xmldir=self.xml_dir)
            bad_site, bad_sat = gt.check_pod_residuals(self.config)
            if (not bad_site and not bad_sat) or i == 3:
                if i != 0:
                    logging.info(f"After quality control: number of stations = {len(self.config.stalist())}, "
                                 f"number of satellites = {len(self.config.all_gnssat())}")
                break
            gt.recover_files(self.config, ['ics'])
            # first remove bad stations
            if bad_site:
                self.config.remove_sta(bad_site)
            # second remove bad satellites
            if bad_sat:
                self.config.update_gnssinfo(sat_rm=self.config.sat_rm() + bad_sat)

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(proc.config.stalist())}, "
                     f"number of satellites = {len(proc.config.all_gnssat())}")
        logging.info(f"===> 1st iteration for precise orbit determination")
        # quality control
        with gt.timeblock("Finished 1st POD"):
            self.detect_outliers()
            gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)

        self.evl_orbdif('F1')
        gr.run_great(self.grt_bin, 'great_editres', self.config, nshort=600, bad=80, jump=80,
                     label='editres', xmldir=self.xml_dir)

        logging.info(f"===> 2nd iteration for precise orbit determination")
        with gt.timeblock("Finished 2nd POD"):
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', label='podlsq', xmldir=self.xml_dir)
            gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)

        self.evl_orbdif('F2')
        gr.run_great(self.grt_bin, 'great_editres', self.config, nshort=600, bad=40, jump=40,
                     label='editres', xmldir=self.xml_dir)

        logging.info(f"===> 3rd iteration for precise orbit determination")
        with gt.timeblock("Finished 3rd POD"):
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', label='podlsq', xmldir=self.xml_dir)
            gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)

        self.evl_orbdif('F3')
        gt.copy_result_files(self.config, ['ics', 'orb', 'satclk', 'recclk'], 'F3', 'gns')

        logging.info(f"===> Double-difference ambiguity resolution")
        self.config.update_process(intv=30)
        gr.run_great(self.grt_bin, 'great_ambfixDd', self.config, label="ambfix", xmldir=self.xml_dir)
        self.config.update_process(intv=self.args.intv)

        logging.info(f"===> 4th iteration for precise orbit determination")
        self.config.update_process(crd_constr='FIX')
        with gt.timeblock("Finished 4th POD"):
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', str_args="-ambfix", ambcon=True,
                         use_res_crd=True, label='podlsq', xmldir=self.xml_dir)
            gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)

        self.evl_orbdif('AR')
        gt.copy_result_files(self.config, ['ics', 'orb', 'satclk', 'recclk'], 'AR', 'gns')
        self.save_results(['F3', 'AR'])

    def save_results(self, labels):
        save_dir = os.path.join(self.result_dir, "orbdif", f"{self.config.beg_time().year}")
        for c in self.ref_cen:
            self.config.update_process(cen=c)
            gt.copy_result_files_to_path(self.config, ['orbdif'], save_dir, labels)


if __name__ == '__main__':
    proc = ProcGnsPod()
    proc.process_batch()

#!/home/jqwu/anaconda3/bin/python3
from gnss_time import hms2sod
import gnss_tools as gt
import gnss_run as gr
from run_gen import RunGen
import os
import logging


class RunGnsPod(RunGen):
    def __init__(self, config=None):
        super().__init__()

        self.default_args['dsc'] = "GREAT GNSS Precise Orbit Determination"
        self.default_args['cf'] = 'cf_gnspod.ini'

        self.required_subdir = ['log_tb', 'tmp', 'orbdif', 'clkdif']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'sp3', 'biabern']

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'POD')

    def prepare(self):
        with gt.timeblock("Finished prepare obs"):
            if not self.prepare_obs():
                return False

        with gt.timeblock("Finished prepare ics"):
            if not self.prepare_ics():
                return False

        return True

    def process_one_pod(self, ambfix=False, lsq=True):
        if lsq:
            if not ambfix:
                gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', label='podlsq')
            else:
                gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', str_args="-ambfix", ambcon=True,
                             use_res_crd=True, label='podlsq')
        gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi')
        gr.run_great(self.grt_bin, 'great_orbdif', self.config, label='orbdif')
        gr.run_great(self.grt_bin, 'great_clkdif', self.config, label='clkdif')

    def detect_outliers(self):
        for i in range(4):
            if i != 0:
                logging.info(f"reprocess-{i} great_podlsq due to bad stations or satellites")
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', str_args="-brdm", label='podlsq')
            bad_site, bad_sat = gt.check_pod_residuals(self.config)
            if i == 0 and not bad_site:
                break
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
            if bad_sat and i != 0:
                self.config.update_gnssinfo(sat_rm=self.config.sat_rm() + bad_sat)

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(proc.config.stalist())}, "
                     f"number of satellites = {len(proc.config.all_gnssat())}")
        logging.info(f"===> 1st iteration for precise orbit determination")
        # quality control
        with gt.timeblock("Finished 1st POD"):
            with gt.timeblock("Finished Detect outliers"):
                self.detect_outliers()
            self.process_one_pod(lsq=False)
        gt.copy_result_files(self.config, ['orbdif', 'clkdif', 'ics'], 'F1', 'gns')
        gr.run_great(self.grt_bin, 'great_editres', self.config, nshort=600, bad=80, jump=80, label='editres')

        logging.info(f"===> 2nd iteration for precise orbit determination")
        with gt.timeblock("Finished 2nd POD"):
            self.process_one_pod()
        gt.copy_result_files(self.config, ['orbdif', 'clkdif', 'ics'], 'F2', 'gns')
        gr.run_great(self.grt_bin, 'great_editres', self.config, nshort=600, bad=40, jump=40, label='editres')

        logging.info(f"===> 3rd iteration for precise orbit determination")
        with gt.timeblock("Finished 3rd POD"):
            self.process_one_pod()
        gt.copy_result_files(self.config, ['orbdif', 'clkdif', 'ics', 'orb', 'satclk', 'recclk'], 'F3', 'gns')

        logging.info(f"===> Double-difference ambiguity resolution")
        self.config.update_process(intv=30)
        gr.run_great(self.grt_bin, 'great_ambfixDd', self.config, label="ambfix")
        self.config.update_process(intv=self.args.intv)

        logging.info(f"===> 4th iteration for precise orbit determination")
        self.config.update_process(crd_constr='FIX')
        with gt.timeblock("Finished 4th POD"):
            self.process_one_pod(ambfix=True)
        gt.copy_result_files(self.config, ['orbdif', 'clkdif', 'ics', 'orb', 'satclk', 'recclk'], 'AR', 'gns')


if __name__ == '__main__':
    proc = RunGnsPod()
    proc.process_batch()

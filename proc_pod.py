#!/home/jqwu/anaconda3/bin/python3
from funcs import gnss_tools as gt, gnss_run as gr
from proc_gen import ProcGen
import os
import shutil
import logging


class ProcPod(ProcGen):
    def __init__(self):
        super().__init__()

        self.default_args['dsc'] = "GREAT GNSS Precise Orbit Determination"
        self.default_args['cf'] = 'cf_pod.ini'

        self.required_subdir = ['log_tb', 'tmp', 'orbdif', 'clkdif', 'figs']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'biabern']

        self.ref_cen = ['com', 'gbm', 'wum']

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'POD')
        self.result_dir = os.path.join(self.proj_dir, f"results_{self.gsys}")

    def init_daily(self, crt_time, seslen):
        self.config.update_timeinfo(crt_time, crt_time + (seslen - self.config.intv()), self.config.intv())
        self.config.update_stalist(self.sta_list)
        self.config.update_gnssinfo(sat_rm=[
            'C01', 'C02', 'C03', 'C04', 'C05', 'C59', 'C60',
            'C39', 'C40', 'C41', 'C42', 'C43', 'C44', 'C45', 'C46'
        ]) # BDS GEO satellites and new satellites
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
        cen = self.config.igs_ac()
        for c in self.ref_cen:
            self.config.update_process(cen=c)
            gr.run_great(self.grt_bin, 'great_orbdif', self.config, label='orbdif', xmldir=self.xml_dir, stop=False)
            gr.run_great(self.grt_bin, 'great_clkdif', self.config, label='clkdif', xmldir=self.xml_dir, stop=False)
            if label:
                gt.copy_result_files(self.config, ['orbdif', 'clkdif'], label, 'gns')
        self.config.update_process(cen=cen)

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
            gt.recover_files(self.config, ['ics', 'orb'])
            # first remove bad stations
            if bad_site:
                self.config.remove_sta(bad_site)
            # second remove bad satellites
            if bad_sat:
                self.config.update_gnssinfo(sat_rm=self.config.sat_rm() + bad_sat)

    def process_1st_pod(self, label='F1', evl=True, prod=False):
        self.detect_outliers()
        gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)
        if evl:
            self.evl_orbdif(label)
        if prod:
            self.generate_products(label)

    def process_float_pod(self, label='F1', evl=True, prod=False, fix_crd=False):
        if fix_crd:
            self.config.update_process(crd_constr='FIX')
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', use_res_crd=True,
                         label='podlsq', xmldir=self.xml_dir)
            self.config.update_process(crd_constr='EST')
        else:
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', label='podlsq', xmldir=self.xml_dir)
        gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)
        if evl:
            self.evl_orbdif(label)
        if prod:
            self.generate_products(label)

    def process_fix_pod(self, label='AR', evl=True, prod=False, fix_crd=True):
        if fix_crd:
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', str_args="-ambfix", ambcon=True,
                         use_res_crd=True, label='podlsq', xmldir=self.xml_dir)
        else:
            self.config.update_process(crd_constr='FIX')
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', str_args="-ambfix", ambcon=True,
                         label='podlsq', xmldir=self.xml_dir)
            self.config.update_process(crd_constr='EST')
        gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)
        if evl:
            self.evl_orbdif(label)
        if prod:
            self.generate_products(label)

    def process_ambfix(self):
        intv = self.config.intv()
        self.config.update_process(intv=30)
        gr.run_great(self.grt_bin, 'great_ambfixDd', self.config, label="ambfix", xmldir=self.xml_dir)
        self.config.update_process(intv=intv)

    def save_results(self, labels):
        orbdif_dir = os.path.join(self.result_dir, "orbdif", f"{self.config.beg_time().year}")
        clkdif_dir = os.path.join(self.result_dir, "clkdif", f"{self.config.beg_time().year}")
        for c in self.ref_cen:
            self.config.update_process(cen=c)
            gt.copy_result_files_to_path(self.config, ['orbdif'], orbdif_dir, labels)
            gt.copy_result_files_to_path(self.config, ['clkdif'], clkdif_dir, labels)

    def generate_products(self, label=None):
        gr.run_great(self.grt_bin, 'great_orbsp3', self.config, label='orb2sp3', xmldir=self.xml_dir)
        f_sp31 = self.config.get_filename('sp3_out', check=True)
        f_clk0 = self.config.get_filename('satclk', check=True)
        f_clk1 = self.config.get_filename('clk_out', check=False)
        if f_clk0:
            shutil.copy(f_clk0, f_clk1)
        else:
            logging.warning(f"failed to find clk file {f_clk0}")
        if label:
            if f_sp31:
                shutil.copy(f_sp31, f"{f_sp31}_{label}")
            if os.path.isfile(f_clk1):
                shutil.copy(f_clk1, f"{f_clk1}_{label}")

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")

        logging.info(f"===> 1st iteration for precise orbit determination")
        with gt.timeblock("Finished 1st POD"):
            self.process_1st_pod('F1', True, False)
            self.process_edtres(bad=80, jump=80, nshort=600)
        gt.copy_result_files(self.config, ['recover'], 'F1', 'gns')

        logging.info(f"===> 2nd iteration for precise orbit determination")
        with gt.timeblock("Finished 2nd POD"):
            self.process_float_pod('F2', True, False)
            self.process_edtres(bad=40, jump=40, nshort=600)
        gt.copy_result_files(self.config, ['recover'], 'F2', 'gns')

        logging.info(f"===> 3rd iteration for precise orbit determination")
        with gt.timeblock("Finished 3rd POD"):
            self.process_float_pod('F3', True, True)

        gt.copy_result_files(self.config, ['ics', 'orb', 'satclk', 'recclk', 'recover'], 'F3', 'gns')
        logging.info(f"===> Double-difference ambiguity resolution")
        self.process_ambfix()

        logging.info(f"===> 4th iteration for precise orbit determination")
        with gt.timeblock("Finished 4th POD"):
            self.process_fix_pod('AR', True, True, True)

        gt.copy_result_files(self.config, ['ics', 'orb', 'satclk', 'recclk', 'recover'], 'AR', 'gns')
        self.save_results(['F3', 'AR'])


if __name__ == '__main__':
    proc = ProcPod()
    proc.process_batch()

from funcs import gnss_tools as gt, gnss_run as gr
from proc_gen import ProcGen
import os
import shutil
import logging


class ProcPce(ProcGen):
    def __init__(self):
        super().__init__()

        self.default_args['dsc'] = "GREAT Precise Clock Estimation"
        self.default_args['intv'] = 300
        self.default_args['freq'] = 2
        self.default_args['obs_comb'] = 'IF'
        self.default_args['cen'] = 'grt'
        self.default_args['cf'] = 'cf_pce.ini'

        self.required_subdir = ['log_tb', 'clkdif', 'tmp']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'sp3', 'biabern']

        self.ref_cen = ['com', 'gbm', 'wum']

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'PCE')

    def prepare_obs(self):
        poddir = os.path.join(self.base_dir, 'POD', str(self.year()), f"{self.doy():0>3d}_GREC_2_IF")
        f_res = f"res_{self.year()}{self.doy():0>3d}"
        try:
            shutil.copy(os.path.join(poddir, f_res), f_res)
        except IOError:
            logging.warning(f"copy {f_res} failed")
    
        ambflagdir = os.path.join(poddir, 'log_tb')
        gt.copy_ambflag_from(ambflagdir)
        if self.config.basic_check(files=['ambflag']):
            logging.info("Ambflag is ok ^_^")
            return True
        else:
            logging.critical("NO ambflag files ! skip to next day")
            return False

    def evl_clkdif(self, label=None):
        cen = self.config.igs_ac()
        for c in self.ref_cen:
            self.config.update_process(cen=c)
            gr.run_great(self.grt_bin, 'great_clkdif', self.config, label='clkdif', xmldir=self.xml_dir, stop=False)
            if label:
                gt.copy_result_files(self.config, ['clkdif'], label, 'gns')
        self.config.update_process(cen=cen)
    
    def generate_products(self, label=None):
        f_clk0 = self.config.get_filename('satclk', check=True)
        f_clk1 = self.config.get_filename('clk_out', check=False)
        if f_clk0:
            shutil.copy(f_clk0, f_clk1)
        else:
            logging.warning(f"failed to find clk file {f_clk0}")
        
        if label:
            if os.path.isfile(f_clk1):
                shutil.copy(f_clk1, f"{f_clk1}_{label}")

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")

        gr.run_great(self.grt_bin, 'great_pcelsq', self.config, mode='PCE_EST', 
                     use_res_crd=True, label='pcelsq', xmldir=self.xml_dir)
        self.generate_products()
        self.evl_clkdif()


if __name__ == '__main__':
    proc = ProcPce()
    proc.process_batch()

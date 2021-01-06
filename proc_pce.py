#!/home/jqwu/anaconda3/bin/python3
from funcs import gnss_tools as gt, gnss_run as gr
from proc_gen import ProcGen
import os
import logging
import shutil


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
        ambflagdir = os.path.join(self.base_dir, 'POD', str(self.year()), f"{self.doy():0>3d}_GREC_2_IF", 'log_tb')
        if not os.path.isdir(ambflagdir):
            logging.warning(f"cannot find source ambflag dir {ambflagdir}")
            return False
        logging.info(f"ambflag files copy from {ambflagdir}")
        if not os.path.isdir('log_tb'):
            os.makedirs('log_tb')
        for file in os.listdir(ambflagdir):
            n = len(file)
            if n < 7:
                continue
            if file[n - 5: n] == "o.log" or file[n - 7: n] in ["o.log13", "o.log14", "o.log15"]:
                f0 = os.path.join(ambflagdir, file)
                f1 = os.path.join('log_tb', file)
                shutil.copy(f0, f1)
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

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")

        gr.run_great(self.grt_bin, 'great_pcelsq', self.config, mode='PCE_EST', label='pcelsq', xmldir=self.xml_dir)
        self.evl_clkdif()


if __name__ == '__main__':
    proc = ProcPce()
    proc.process_batch()

import os
import shutil
import logging
from proc_gen import ProcGen
from funcs import copy_result_files, GrtClkdif, GrtPcelsq


class ProcPce(ProcGen):
    default_args = {
        'dsc': 'GREAT GNSS Precise Clock Estimation',
        'num': 1, 'seslen': 24, 'intv': 30, 'obs_comb': 'IF', 'est': 'LSQ', 'sys': 'G',
        'freq': 2, 'cen': 'com', 'bia': 'cas', 'cf': 'cf_pce.ini'
    }

    proj_id = 'PCE'

    required_subdir = ['log_tb', 'tmp', 'xml', 'clkdif', 'figs']
    required_opt = ['estimator']
    required_file = ['rinexo', 'rinexn', 'biabern']

    ref_cen = ['com', 'gbm', 'wum']

    # def prepare_obs(self):
    #     poddir = os.path.join(self._config.base_dir, 'POD', str(self._config.beg_time.year),
    #                           f"{self._config.beg_time.doy:0>3d}_GREC_2_IF")
    #     f_res = f"res_{self._config.beg_time.year}{self._config.beg_time.doy:0>3d}"
    #     try:
    #         shutil.copy(os.path.join(poddir, f_res), f_res)
    #     except IOError:
    #         logging.warning(f"copy {f_res} failed")
    #
    #     ambflagdir = os.path.join(poddir, 'log_tb')
    #     gt.copy_ambflag_from(ambflagdir)
    #     if self._config.basic_check(files=['ambflag']):
    #         logging.info("Ambflag is ok ^_^")
    #         return True
    #     else:
    #         logging.critical("NO ambflag files ! skip to next day")
    #         return False

    def clkdif(self, label=''):
        cen = self._config.orb_ac
        for c in self.ref_cen:
            self._config.orb_ac = c
            GrtClkdif(self._config, 'clkdif').run()
            if label:
                copy_result_files(self._config, ['clkdif'], label, 'gns')
        self._config.orb_ac = cen

    def generate_products(self, label=''):
        f_clk0 = self._config.get_xml_file('satclk', check=True)
        f_clk1 = self._config.get_xml_file('clk_out', check=False)
        if f_clk0:
            shutil.copy(f_clk0[0], f_clk1[0])
        if label and os.path.isfile(f_clk1[0]):
            shutil.copy(f_clk1[0], f"{f_clk1[0]}_{label}")

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")

        GrtPcelsq(self._config, 'pcelsq').run()
        self.generate_products()
        self.clkdif()


if __name__ == '__main__':
    proc = ProcPce.from_args()
    proc.process_batch()

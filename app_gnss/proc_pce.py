import os
import sys
import shutil
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from proc_gen import ProcGen
from funcs import copy_result_files, copy_ambflag_from, GrtClkdif, GrtPcelsq, GrtAmbfixDd, GrtAmbfix


class ProcPce(ProcGen):
    default_args = {
        'dsc': 'GREAT GNSS Precise Clock Estimation',
        'num': 1, 'seslen': 24, 'intv': 30, 'obs_comb': 'IF', 'est': 'LSQ', 'sys': 'G',
        'freq': 2, 'cen': 'com', 'bia': 'cas', 'cf': 'cf_pce.ini'
    }

    proj_id = 'PCE'

    required_subdir = super().required_subdir + ['clkdif']
    required_opt = super().required_opt + ['estimator']
    required_file = super().required_file + ['rinexo', 'rinexn', 'biabern', 'sp3']

    ref_cen = ['com', 'gbm', 'wum', 'esm']

    # def prepare_obs(self):
    #     ref_dir = os.path.join(self.base_dir, 'POD', str(self.year), f'{self.doy:0>3d}_{self._gsys}_2_IF')
    #     copy_ambflag_from(os.path.join(ref_dir, 'log_tb'))
    #     if self.basic_check(files=['ambflag']):
    #         logging.info("Ambflag is ok ^_^")
    #         return True
    #     else:
    #         logging.critical("NO ambflag files ! skip to next day")
    #         return False

    def process_ambfix(self):
        self._config.intv = 30
        GrtAmbfix(self._config, "DD", 'ambfix').run()
        # GrtAmbfixDd(self._config, 'ambfix').run()
        self._config.intv = self._intv

    def clkdif(self, label=''):
        cen = self._config.orb_ac
        for c in self.ref_cen:
            self._config.orb_ac = c
            for g in self._gsys:
                self._config.gsys = g
                GrtClkdif(self._config, f'clkdif_{c}_{g}').run()
                if label:
                    copy_result_files(self._config, ['clkdif'], label, 'gns')
            self._config.gsys = self._gsys
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
        # self._config.crd_constr = 'FIX'
        GrtPcelsq(self._config, 'pcelsq').run()
        self.clkdif('F')
        self.generate_products('F')

        # if self._config.lsq_mode != "EPO":
        #     self.process_ambfix()
        #     GrtPcelsq(self._config, 'pcelsq', fix_amb=True).run()
        #     self.clkdif('AR')
        #     self.generate_products('AR')


if __name__ == '__main__':
    proc = ProcPce.from_args()
    proc.process_batch()

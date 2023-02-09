import os
import sys
import shutil
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from proc_gen import ProcGen
from funcs import GnssConfig, copy_result_files, GrtClkdif, GrtPcelsq, GrtAmbfix, read_site_list


class ProcPce(ProcGen):

    description = 'GREAT GNSS Precise Clock Estimation'
    default_config = 'cf_pce.ini'
    ref_cen = ['com', 'gbm', 'wum', 'esm']

    def __init__(self, config: GnssConfig, ndays=1, kp_dir=False):
        super().__init__(config, ndays, kp_dir)
        self.required_subdir += ['clkdif']
        self.required_opt += ['estimator']
        self.required_file += ['rinexo', 'rinexn', 'sp3', 'biabern']
        self.proj_id = 'PCE'

    def process_ambfix(self):
        self._config.intv = 30
        GrtAmbfix(self._config, "DD", 'ambfix').run()
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
        f_clk1 = self._config.get_xml_file('grtclk', sec="output_files")
        if f_clk0:
            shutil.copy(f_clk0[0], f_clk1[0])
        if label and os.path.isfile(f_clk1[0]):
            shutil.copy(f_clk1[0], f"{f_clk1[0]}_{label}")

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")

        # self._config.crd_constr = 'FIX'
        GrtPcelsq(self._config, 'pcelsq', fix_amb=False).run()
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

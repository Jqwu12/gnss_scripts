import os
import sys
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import gns_name, timeblock, merge_upd_all, copy_result_files_to_path, backup_dir, GrtUpdlsq, GrtPpplsq
from proc_gen import ProcGen


class ProcUpd(ProcGen):
    default_args = {
        'dsc': 'GREAT Uncalibrated Phase Delay Estimation',
        'num': 1, 'seslen': 24, 'intv': 30, 'obs_comb': 'UC', 'est': 'LSQ', 'sys': 'G',
        'freq': 3, 'cen': 'com', 'bia': 'cas', 'cf': 'cf_upd.ini'
    }

    proj_id = 'UPD'

    required_subdir = ['log_tb', 'xml', 'enu', 'flt', 'ppp', 'ambupd', 'res', 'tmp']
    required_opt = ['estimator']
    required_file = ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']

    def process_ifcb(self):
        if self._config.freq < 3 or 'G' not in self._config.gsys:
            return False
        # if no ifcb file in current dir, run ifcb estimation
        if not self._config.get_xml_file('ifcb', check=True):
            with timeblock('Finished IFCB estimation'):
                self._config.gsys = 'G'
                obs_comb = self._config.obs_comb
                self._config.obs_comb = "IF"
                GrtUpdlsq(self._config, mode='IFCB', label='ifcb').run()
                self._config.gsys = self._gsys
                self._config.obs_comb = obs_comb
            return True
        return False

    def process_ppp(self):
        logging.info(f"===> Calculate float ambiguities by precise point positioning")
        GrtPpplsq(self._config, 'ppplsq', nmp=self.nthread).run()
        self.basic_check(files=['recover_all', 'ambupd_in'])

    def process_upd_onesys(self, gsys):
        nfreq = self._config.freq
        mfreq = self._config.gnsfreq(gsys)
        self._config.gsys = gsys
        self._config.freq = mfreq
        upd_results = []
        logging.info(f"===> Start to process {gns_name(gsys)} UPD")
        if mfreq == 5:
            GrtUpdlsq(self._config, 'EWL25', f'upd_ewl25_{gsys}').run()
            upd_results.append('upd_ewl25')
        if mfreq >= 4:
            GrtUpdlsq(self._config, 'EWL24', f'upd_ewl24_{gsys}').run()
            upd_results.append('upd_ewl24')
        if mfreq >= 3:
            GrtUpdlsq(self._config, 'EWL', f'upd_ewl_{gsys}').run()
            upd_results.append('upd_ewl')
        GrtUpdlsq(self._config, 'WL', f'upd_wl_{gsys}').run()
        upd_results.append('upd_wl')
        GrtUpdlsq(self._config, 'NL', f'upd_nl_{gsys}').run()
        upd_results.append('upd_nl')

        self._config.gsys = self._gsys
        self._config.freq = nfreq
        return upd_results

    def process_upd(self, obs_comb=None):
        if obs_comb is not None:
            self._config.obs_comb = obs_comb
        upd_results = []
        if self.process_ifcb():
            upd_results.append('ifcb')

        freq = self._config.freq
        if self._config.obs_comb == "IF":
            self._config.freq = 2
        self.process_ppp()
        self._config.freq = freq

        for gsys in self._gsys:
            upd_results.extend(self.process_upd_onesys(gsys))

        upd_results = list(set(upd_results))
        upd_results.sort()
        # Merge multi-GNSS UPD
        if len(self._gsys) > 1:
            logging.info(f"===> Merge UPD: {' '.join(upd_results)}")
            merge_upd_all(self._config, self._gsys, upd_results)

        return upd_results

    def save_results(self, upd_results):
        if not upd_results:
            return
        if 'ifcb' in upd_results:
            upd_data = os.path.join(self._config.upd_data, "ifcb", f"{self._config.beg_time.year}")
            logging.info(f"===> Copy IFCB results to {upd_data}")

        upd_data = os.path.join(self._config.upd_data, self._config.orb_ac, f"{self._config.beg_time.year}")
        logging.info(f"===> Copy UPD results to {upd_data}")
        copy_result_files_to_path(self._config, upd_results, upd_data)

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")

        # with timeblock("Finish process IF upd"):
        #     self.save_results(self.process_upd(obs_comb='IF'))
        #     backup_dir('ambupd', 'ambupd_IF')

        results = self.process_upd()
        self.save_results(results)


if __name__ == '__main__':
    proc = ProcUpd.from_args()
    proc.process_batch()

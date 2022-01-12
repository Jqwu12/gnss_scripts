import os
import sys
import shutil
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import gns_name, gns_sat, timeblock, merge_upd_all, merge_upd_bds, copy_result_files_to_path, \
    backup_dir, check_res_sigma, GrtUpdlsq, GrtPpplsq, GrtAmbfix
from app_gnss.proc_gen import ProcGen


class ProcUpd(ProcGen):
    default_args = {
        'dsc': 'GREAT Uncalibrated Phase Delay Estimation',
        'num': 1, 'seslen': 24, 'intv': 30, 'obs_comb': 'UC', 'est': 'LSQ', 'sys': 'G',
        'freq': 3, 'cen': 'com', 'bia': 'cas', 'cf': 'cf_upd.ini'
    }

    proj_id = 'UPD'

    required_subdir = super().required_subdir + ['enu', 'flt', 'ppp', 'ambupd', 'res']
    required_opt = super().required_opt + ['estimator']
    required_file = super().required_file + ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']

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

    def process_ppp(self, fix=False):
        logging.info(f"===> Calculate float ambiguities by precise point positioning")
        if fix:
            GrtAmbfix(self._config, 'SD', 'ambfix', nmp=self.nthread, all_sites=True).run()
        GrtPpplsq(self._config, 'ppplsq', nmp=self.nthread, fix_amb=fix, stop=False).run()
        self.basic_check(files=['recover_all', 'ambupd_in'])
        check_res_sigma(self._config)

    def copy_upd(self, upd_results, old, new):
        if not old or not new or old == new:
            return
        for f_type in upd_results:
            file = self._config.file_name(f_type, check=True)
            if not file:
                continue
            idx = file.rfind(old)
            file_new = file[0: idx] + new + file[idx+len(old):]
            try:
                shutil.copy(file, file_new)
            except shutil.SameFileError:
                logging.warning(f'copy failed! files are same {file_new}')
                continue

    def process_upd_onesys(self, gsys):
        if gsys == "C2":
            self._config.sat_rm += gns_sat("C3")
        elif gsys == "C3":
            self._config.sat_rm += gns_sat("C2")
        nfreq = self._config.freq
        mfreq = self._config.gnsfreq(gsys[0])
        self._config.gsys = gsys[0]
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

        if gsys[0] == "C":
            self.copy_upd(upd_results, gsys[0], gsys)
        self._config.gsys = self._gsys
        self._config.freq = nfreq
        self._config.sat_rm = self.sat_rm
        shutil.copy('NL-res', f'NL-res_{gsys}')
        return upd_results

    def process_upd(self, obs_comb=None, fix=False):
        if obs_comb is not None:
            self._config.obs_comb = obs_comb
        upd_results = []
        if self.process_ifcb():
            upd_results.append('ifcb')

        freq = self._config.freq
        if self._config.obs_comb == "IF":
            self._config.freq = 2
        self.process_ppp(fix)
        self._config.freq = freq

        gsys_list = [s for s in self._gsys if s != "C"]
        if "C" in self._gsys:
            gsys_list += ["C2", "C3"]
        for gsys in gsys_list:
            upd_results.extend(self.process_upd_onesys(gsys))

        upd_results = list(set(upd_results))
        upd_results.sort()
        if "C" in self._gsys:
            merge_upd_bds(self._config, upd_results)
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
            copy_result_files_to_path(self._config, ['ifcb'], upd_data)

        upd_data = os.path.join(self._config.upd_data, self._config.orb_ac, f"{self._config.beg_time.year}")
        logging.info(f"===> Copy UPD results to {upd_data}")
        copy_result_files_to_path(self._config, [f for f in upd_results if f != 'ifcb'], upd_data)

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

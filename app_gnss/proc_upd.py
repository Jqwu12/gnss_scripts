import os
import sys
import shutil
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import GnssConfig, gns_name, gns_sat, timeblock, merge_upd_all, merge_upd_bds, copy_result_files_to_path, \
    backup_dir, check_res_sigma, GrtUpdlsq, GrtPpplsq, GrtAmbfix, multi_run
from app_gnss.proc_gen import ProcGen


class ProcUpd(ProcGen):

    description = 'GREAT Uncalibrated Phase Delay Estimation'
    default_config = 'cf_upd.ini'

    def __init__(self, config: GnssConfig, ndays=1, kp_dir=False):
        super().__init__(config, ndays, kp_dir)
        self.required_subdir += ['enu', 'flt', 'ppp', 'ambupd', 'res']
        self.required_opt += ['estimator']
        self.required_file += ['rinexo', 'rinexn', 'biabern']
        self.proj_id = 'UPD'
        self.upd_results = set()
        self.est_ifcb = False

    def process_ifcb(self):
        if self._config.freq < 3 or 'G' not in self._config.gsys:
            return
        # if no ifcb file in current dir, run ifcb estimation
        if not self._config.get_xml_file('ifcb', check=True):
            with timeblock('Finished IFCB estimation'):
                self._config.gsys = 'G'
                obs_comb = self._config.obs_comb
                self._config.obs_comb = "IF"
                GrtUpdlsq(self._config, mode='IFCB', label='ifcb').run()
                self._config.gsys = self._gsys
                self._config.obs_comb = obs_comb
                self.est_ifcb = True

    def process_ppp(self):
        logging.info(f"===> Calculate float ambiguities by precise point positioning")
        self.basic_check(files=['rinexc', 'sp3'])
        GrtPpplsq(self._config, 'ppplsq', nmp=self.nthread, stop=False).run()
        self.basic_check(files=['recover', 'ambupd'])
        check_res_sigma(self._config)

    def copy_upd(self, upd_results, old, new):
        if not old or not new or old == new:
            return
        for f_type in upd_results:
            file = self._config.file_name(f_type, check=True)
            if not file:
                continue
            idx = file.rfind(old)
            if idx < 0:
                continue
            file_new = file[0: idx] + new + file[idx+len(old):]
            try:
                shutil.copy(file, file_new)
            except shutil.SameFileError:
                logging.warning(f'copy failed! files are same {file_new}')
                continue
    
    def process_bds2_upd(self):
        if 'C' not in self._gsys:
            return
        self._config.sat_rm += gns_sat("C3")
        nfreq = self._config.freq
        mfreq = self._config.gnsfreq("C")
        self._config.gsys = 'C'
        self._config.freq = mfreq
        upd_results = ['upd_nl', 'upd_wl']
        logging.info(f"===> Start to process {gns_name('C2')} UPD")
        cmds = []
        if mfreq >= 3:
            cmds.append(GrtUpdlsq(self._config, 'EWL', f'upd_ewl_C2').form_cmd())
            upd_results.append('upd_ewl')
        cmds.append(GrtUpdlsq(self._config, 'WL', f'upd_wl_C2').form_cmd())
        multi_run(cmds, "upd_wl_C2", stop=True)
        GrtUpdlsq(self._config, 'NL', f'upd_nl_C2').run()
        self.copy_upd(upd_results, 'C', 'C2')
        self._config.gsys = self._gsys
        self._config.freq = nfreq
        self._config.sat_rm = self.sat_rm
        shutil.copy('NL-res', f'NL-res_C2')
        self.upd_results.update(upd_results)

    def process_wl_upd(self):
        cmds = []
        self.upd_results.add('upd_wl')
        gsys = ['C3' if s == 'C' and self._config.bds2_isb else s for s in self._gsys]
        if self._config.bds2_isb:
            self._config.sat_rm += gns_sat("C2")
        for gs in gsys:
            nfreq = self._config.freq
            mfreq = self._config.gnsfreq(gs[0])
            self._config.gsys = gs[0]
            self._config.freq = mfreq
            logging.info(f"===> Start to process {gns_name(gs)} EWL/WL UPD")
            if mfreq == 5:
                cmds.extend(GrtUpdlsq(self._config, 'EWL25', f'upd_ewl25_{gs}').form_cmd())
                self.upd_results.add('upd_ewl25')
            if mfreq >= 4:
                cmds.extend(GrtUpdlsq(self._config, 'EWL24', f'upd_ewl24_{gs}').form_cmd())
                self.upd_results.add('upd_ewl24')
            if mfreq >= 3:
                cmds.extend(GrtUpdlsq(self._config, 'EWL', f'upd_ewl_{gs}').form_cmd())
                self.upd_results.add('upd_ewl')
            cmds.extend(GrtUpdlsq(self._config, 'WL', f'upd_wl_{gs}').form_cmd())
            self._config.freq = nfreq
            self._config.gsys = self._gsys
            
        multi_run(cmds, 'upd_wl', stop=True)
        self._config.sat_rm = self.sat_rm

    def process_nl_upd(self):
        cmds = []
        self.upd_results.add('upd_nl')
        gsys = ['C3' if s == 'C' and self._config.bds2_isb else s for s in self._gsys]
        if self._config.bds2_isb:
            self._config.sat_rm += gns_sat("C2")
        for gs in gsys:
            self._config.gsys = gs[0]
            logging.info(f"===> Start to process {gns_name(gs)} NL UPD")
            cmds.extend(GrtUpdlsq(self._config, 'NL', f'upd_nl_{gs}').form_cmd())
            self._config.gsys = self._gsys
            
        multi_run(cmds, 'upd_nl', stop=True)
        for gs in self._gsys:
            if gs == 'C' and self._config.bds2_isb:
                self._config.gsys = gs
                self.copy_upd(list(self.upd_results), 'C', 'C3')
                shutil.copy('NL-res', 'NL-res_C3')
            else:
                shutil.copy('NL-res', f'NL-res_{gs}')   
        self._config.sat_rm = self.sat_rm

    def save_results(self, upd_results: set):        
        if self.est_ifcb:
            upd_data = self._config.get_xml_file_str('ifcb_dir', sec='output_files')
            if upd_data:
                logging.info(f"===> Copy IFCB results to {upd_data}")
                copy_result_files_to_path(self._config, ['ifcb'], upd_data)

        if upd_results:
            upd_data = self._config.get_xml_file_str('upd_dir', sec='output_files')
            if upd_data:
                logging.info(f"===> Copy UPD results to {upd_data}")
                copy_result_files_to_path(self._config, list(upd_results), upd_data)

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")

        self.upd_results = set()
        self.est_ifcb = False
        self.process_ifcb()

        if not self._config.ext_ambupd:
            freq = self._config.freq
            if self._config.obs_comb == "IF":
                self._config.freq = 2
            self.process_ppp()
            self._config.freq = freq
        else:
            self.basic_check(files=['ambupd'])

        self.process_wl_upd()
        self.process_nl_upd()

        upd_results = list(self.upd_results)
        if 'C' in self._gsys and self._config.bds2_isb:
            self.process_bds2_upd()
            merge_upd_bds(self._config, upd_results)
        
        # Merge multi-GNSS UPD
        if len(self._gsys) > 1:
            logging.info(f"===> Merge UPD: {' '.join(upd_results)}")
            merge_upd_all(self._config, self._gsys, upd_results)

        self.upd_results = {'upd_nl', 'upd_wl'}
        self.save_results(self.upd_results)


if __name__ == '__main__':
    proc = ProcUpd.from_args()
    proc.process_batch()

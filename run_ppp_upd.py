#!/home/jqwu/anaconda3/bin/python3
from gnss_time import hms2sod
import gnss_tools as gt
import gnss_run as gr
from run_gen import RunGen
from constants import get_gns_name
import os
import shutil
import logging
import platform


class RunUpd(RunGen):
    def __init__(self, config=None):
        super().__init__(config)
        if self.args.freq > 3 and self.args.obs_comb != "UC":
            raise SystemExit("4- and 5-frequency UPD estimation currently only supports uncombined observation model")
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'UPD')
        self.required_subdir = ['log_tb', 'enu', 'flt', 'ppp', 'ambupd', 'res', 'tmp']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']

    def get_args(self):
        return super().get_args(intv=30, freq=3, obs_comb='UC', cf='cf_upd.ini')

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'UPD')

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")
        upd_results = []

        # with gt.timeblock("Estimate IFCB"):
        #     if self.args.freq > 2 and "G" in self.args.sys:
        #         self.config.update_process(sys='G')
        #         gt.run_great(self.grt_bin, 'great_updlsq', self.config, mode='ifcb', out="ifcb")
        #         self.config.update_process(sys=self.args.sys)
        #         upd_results.append('ifcb')

        logging.info(f"===> Calculate float ambiguities by precise point positioning")
        nthread = min(len(self.config.all_receiver().split()), 10)
        with gt.timeblock("Run PPP"):
            gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', nthread=nthread, fix_mode="NO",
                         out=os.path.join("tmp", "ppplsq"))

        for gsys in self.args.sys:
            self.config.update_process(sys=gsys)
            mfreq = self.config.gnsfreq(gsys)
            logging.info(f"===> Start to process {get_gns_name(gsys)} UPD")
            if mfreq == 5:
                with gt.timeblock("EWL25 UPD"):
                    gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='EWL25',
                                 out=os.path.join("tmp", f"upd_ewl25_{gsys}"))
                if 'upd_ewl25' not in upd_results:
                    upd_results.append('upd_ewl25')

            if mfreq >= 4:
                with gt.timeblock("EWL24 UPD"):
                    gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='EWL24',
                                 out=os.path.join("tmp", f"upd_ewl24_{gsys}"))
                if 'upd_ewl24' not in upd_results:
                    upd_results.append('upd_ewl24')

            if mfreq >= 3:
                with gt.timeblock("EWL UPD"):
                    gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='EWL',
                                 out=os.path.join("tmp", f"upd_ewl_{gsys}"))
                if 'upd_ewl' not in upd_results:
                    upd_results.append('upd_ewl')

            with gt.timeblock("WL UPD"):
                gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='WL',
                             out=os.path.join("tmp", f"upd_wl_{gsys}"))
            if 'upd_wl' not in upd_results:
                upd_results.append('upd_wl')

            with gt.timeblock("WL UPD"):
                gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='NL',
                             out=os.path.join("tmp", f"upd_nl_{gsys}"))
            if 'upd_nl' not in upd_results:
                upd_results.append('upd_nl')

        # Merge multi-GNSS UPD
        if len(self.args.sys) > 1:
            logging.info(f"===> Merge UPD: {gt.list2str(upd_results)}")
            gt.merge_upd_all(self.config, self.args.sys)

        # Copy results
        upd_data = self.config.config.get("common", "upd_data")
        logging.info(f"===> Copy UPD results to {upd_data}")
        gt.copy_result_files_to_path(self.config, upd_results, os.path.join(upd_data, f"{self.config.beg_time().year}"))

    def ppp_clean(self):
        # detect outliers in carrier-range by PPP
        if not os.path.isdir("ambupd_save"):
            os.rename("ambupd", "ambupd_save")
        self.config.update_process(crd_constr='FIX')
        self.config.update_process(apply_carrier_range='true', append=True)
        nthread = min(len(self.config.all_receiver().split()), 10)
        with gt.timeblock("Run PPP"):
            gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', nthread=nthread, fix_mode="NO",
                         use_res_crd=True, out=os.path.join("tmp", "ppplsq"))
        gr.run_great(self.grt_bin, 'great_editres', self.config, nthread=nthread, jump=60, mode="L12", edt_amb=True,
                     all_sites=True)
        if self.args.freq > 2:
            gr.run_great(self.grt_bin, 'great_editres', self.config, nthread=nthread, jump=60, mode="L13", edt_amb=True,
                         all_sites=True)

    def process_carrier_range(self):
        self.process_daily()
        self.ppp_clean()
        nthread = min(len(self.config.all_receiver().split()), 10)
        gr.run_great(self.grt_bin, "great_convobs", self.config, nthread=nthread)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(filename)20s[line:%(lineno)5d] - %(levelname)8s: %(message)s')
    # ------ Path information --------
    if platform.system() == 'Windows':
        all_path = {
            'grt_bin': r"D:\GNSS_Software\GREAT\build\Bin\RelWithDebInfo",
            'base_dir': r"D:\GNSS_Project",
            'sys_data': r"D:\GNSS_Project\sys_data",
            'gns_data': r"D:\GNSS_Project\gns_data",
            'upd_data': r"D:\GNSS_Project\gns_data\upd"
        }
    else:
        all_path = {
            'grt_bin': "/home/jqwu/softwares/GREAT/branches/merge_navpod_merge_ppp/build/Bin",
            'base_dir': "/home/jqwu/projects",
            'sys_data': "/home/jqwu/projects/sys_data",
            'gns_data': "/home/jqwu/gns_data",
            'upd_data': "/home/jqwu/gns_data/upd"
        }

    # ------ Init config file --------
    proc = RunUpd()
    if not proc.sta_list:
        raise SystemExit("No site to process!")
    proc.update_path(all_path)
    # ------ Set process time --------
    step = 86400
    beg_time = proc.beg_time()
    end_time = beg_time + proc.args.num*step - proc.args.intv
    count = proc.args.num
    seslen = hms2sod(proc.args.len)

    # ------- daily loop -------------
    crt_time = beg_time
    while crt_time < end_time:
        # reset daily config
        proc.init_daily(crt_time, seslen)
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"===> Run UPD estimation for {crt_time.year}-{crt_time.doy:0>3d}")
        workdir = os.path.join(proc.proj_dir, str(crt_time.year), f"{crt_time.doy:0>3d}_{proc.args.sys}_{proc.args.freq}_{proc.args.obs_comb}")
        if not os.path.isdir(workdir):
            os.makedirs(workdir)
        else:
            if not proc.args.keep_dir:
                shutil.rmtree(workdir)
                os.makedirs(workdir)
        os.chdir(workdir)
        logging.info(f"work directory = {workdir}")

        with gt.timeblock("prepare obs"):
            if not proc.prepare_obs():
                crt_time += step
                continue

        with gt.timeblock("process daily"):
            proc.process_daily()

        # next day
        logging.info(f"Complete {crt_time.year}-{crt_time.doy:0>3d} ^_^")
        logging.info(f"------------------------------------------------------------------------\n")
        crt_time += step

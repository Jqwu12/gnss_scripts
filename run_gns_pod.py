#!/home/jqwu/anaconda3/bin/python3
from gnss_time import hms2sod
import gnss_tools as gt
import gnss_run as gr
from run_gen import RunGen
import os
import shutil
import logging
import platform


class RunGnsPod(RunGen):
    def __init__(self, config=None):
        super().__init__(config)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'POD')
        self.required_subdir = ['log_tb', 'tmp', 'orbdif', 'clkdif']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'sp3', 'biabern']

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'POD')

    def process_one_pod(self, ambfix=False, lsq=True):
        if lsq:
            if not ambfix:
                gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST',
                             out=os.path.join("tmp", "podlsq"))
            else:
                gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', str_args="-ambfix", ambcon=True,
                             use_res_crd=True, out=os.path.join("tmp", "podlsq"))
        gr.run_great(self.grt_bin, 'great_oi', self.config, sattype='gns')
        gr.run_great(self.grt_bin, 'great_orbdif', self.config, out=os.path.join("tmp", "orbdif"))
        gr.run_great(self.grt_bin, 'great_clkdif', self.config, out=os.path.join("tmp", "clkdif"))

    def detect_outliers(self):
        for i in range(4):
            if i != 0:
                logging.info(f"reprocess-{i} great_podlsq due to bad stations or satellites")
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', str_args="-brdm",
                         out=os.path.join("tmp", "podlsq"))
            bad_site, bad_sat = gt.check_pod_residuals(self.config)
            if i == 0 and not bad_site:
                break
            if (not bad_site and not bad_sat) or i == 3:
                if i != 0:
                    logging.info(f"After quality control: number of stations = {len(self.config.stalist())}, "
                                 f"number of satellites = {len(self.config.all_gnssat())}")
                break
            gt.recover_files(self.config, ['ics'])
            # first remove bad stations
            if bad_site:
                self.config.remove_sta(bad_site)
            # second remove bad satellites
            if bad_sat and i != 0:
                self.config.update_gnssinfo(sat_rm=self.config.sat_rm() + bad_sat)

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(proc.config.stalist())}, "
                     f"number of satellites = {len(proc.config.all_gnssat())}")
        logging.info(f"===> 1st iteration for precise orbit determination")
        # quality control
        with gt.timeblock("1st POD"):
            with gt.timeblock("Detect outliers"):
                self.detect_outliers()
            self.process_one_pod(lsq=False)
        gt.copy_result_files(self.config, ['orbdif', 'clkdif', 'ics'], 'F1', 'gns')
        gr.run_great(self.grt_bin, 'great_editres', self.config, nshort=600, bad=80, jump=80)

        logging.info(f"===> 2nd iteration for precise orbit determination")
        with gt.timeblock("2nd POD"):
            self.process_one_pod()
        gt.copy_result_files(self.config, ['orbdif', 'clkdif', 'ics'], 'F2', 'gns')
        gr.run_great(self.grt_bin, 'great_editres', self.config, nshort=600, bad=40, jump=40)

        logging.info(f"===> 3rd iteration for precise orbit determination")
        with gt.timeblock("3rd POD"):
            self.process_one_pod()
        gt.copy_result_files(self.config, ['orbdif', 'clkdif', 'ics', 'orb', 'satclk', 'recclk'], 'F3', 'gns')

        logging.info(f"===> Double-difference ambiguity resolution")
        self.config.update_process(intv=30)
        gr.run_great(self.grt_bin, 'great_ambfixDd', self.config, out=os.path.join("tmp", "ambfix"))
        self.config.update_process(intv=self.args.intv)

        logging.info(f"===> 4th iteration for precise orbit determination")
        self.config.update_process(crd_constr='FIX')
        with gt.timeblock("4th POD"):
            self.process_one_pod(ambfix=True)
        gt.copy_result_files(self.config, ['orbdif', 'clkdif', 'ics', 'orb', 'satclk', 'recclk'], 'AR', 'gns')


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
    proc = RunGnsPod()
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
        logging.info(f"===> Run GNSS POD for {crt_time.year}-{crt_time.doy:0>3d}")
        workdir = os.path.join(proc.proj_dir, str(crt_time.year), f"{crt_time.doy:0>3d}_{proc.args.sys}")
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

        with gt.timeblock("prepare ics"):
            if not proc.prepare_ics():
                crt_time += step
                continue

        with gt.timeblock("process daily"):
            proc.process_daily()

        # next day
        logging.info(f"Complete {crt_time.year}-{crt_time.doy:0>3d} ^_^")
        logging.info(f"------------------------------------------------------------------------\n")
        crt_time += step

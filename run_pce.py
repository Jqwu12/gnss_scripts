#!/home/jqwu/anaconda3/bin/python3
from gnss_time import hms2sod
import gnss_tools as gt
import gnss_run as gr
from run_gen import RunGen
import os
import shutil
import logging
import platform


class RunPce(RunGen):
    def __init__(self, config=None):
        super().__init__(config)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'PCE')
        self.required_subdir = ['log_tb', 'clkdif', 'tmp']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'sp3', 'biabern']

    def get_args(self):
        return super().get_args(cf='cf_pce.ini')

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'PCE')

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")

        with gt.timeblock("Precise clock estimation"):
            gr.run_great(self.grt_bin, 'great_pcelsq', self.config, mode='PCE_EST', out=os.path.join("tmp", "pcelsq"))
        gr.run_great(self.grt_bin, 'great_clkdif', self.config)


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
    proc = RunPce()
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
        logging.info(f"===> Run Precise clock estimation for {crt_time.year}-{crt_time.doy:0>3d}")
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
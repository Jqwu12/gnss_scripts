#!/home/jqwu/anaconda3/bin/python3
from gnss_time import GNSStime, hms2sod
import gnss_tools as gt
import gnss_run as gr
from run_gen import RunGen
import os
import shutil
import logging
import platform


class RunIfcb(RunGen):
    def __init__(self, config=None):
        super().__init__(config)
        self.config.update_gnssinfo(sys='G', freq=3, obs_comb="IF", est="LSQ")
        self.config.update_prodinfo(self.args.cen, 'cas')
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'UPD')
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'biabern']

    def get_args(self):
        return super().get_args(intv=30, freq=3, cf='cf_upd.ini')

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'UPD')

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")

        with gt.timeblock("Estimate IFCB"):
            gr.run_great(self.grt_bin, 'great_updlsq', self.config, mode='ifcb', out="ifcb")

        upd_data = self.config.config.get("common", "upd_data")
        logging.info(f"===> Copy UPD results to {upd_data}")
        gt.copy_result_files_to_path(self.config, ['ifcb'], os.path.join(upd_data, f"{self.config.beg_time().year}"))


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
    proc = RunIfcb()
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
        workdir = os.path.join(proc.proj_dir, str(crt_time.year), f"{crt_time.doy:0>3d}_ifcb")
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

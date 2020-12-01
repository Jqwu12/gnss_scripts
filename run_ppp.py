#!/home/jqwu/anaconda3/bin/python3
from gnss_time import hms2sod
import gnss_run as gr
import gnss_tools as gt
from run_gen import RunGen
import os
import shutil
import logging
import platform


class RunPpp(RunGen):
    def __init__(self, config=None):
        super().__init__(config)
        if self.args.freq > 3 and self.args.obs_comb != "UC":
            raise SystemExit("4- and 5-frequency UPD estimation currently only supports uncombined observation model")
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'PPP')
        self.required_subdir = ['log_tb', 'enu', 'flt', 'ppp', 'ambupd', 'res', 'tmp']
        self.required_opt = ['estimator']
        self.required_file = ['rinexo', 'rinexn', 'rinexc', 'sp3', 'biabern']

    def get_args(self):
        return super().get_args(intv=30, freq=3, est='EPO', cf='cf_ppp.ini')

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'PPP')

    def process_daily(self, freq=None, obs_comb=None, fix=True):
        if freq:
            self.config.update_gnssinfo(freq=int(freq))
        if obs_comb:
            self.config.update_gnssinfo(obs_comb=str(obs_comb))
        nthread = min(len(self.config.all_receiver().split()), 10)
        if not fix:
            gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', newxml=True, nthread=nthread,
                         fix_mode="NO",out=os.path.join('tmp', 'ppplsq'))
        else:
            gr.run_great(self.grt_bin, 'great_ppplsq', self.config, mode='PPP_EST', newxml=True, nthread=nthread,
                         fix_mode="SEARCH",out=os.path.join('tmp', 'ppplsq'))


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
    proc = RunPpp()
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
        proc.config.update_timeinfo(crt_time, crt_time + (seslen - proc.args.intv), proc.args.intv)
        proc.config.update_stalist(proc.sta_list)
        proc.config.update_gnssinfo(sat_rm=[])
        proc.config.update_process(crd_constr='EST')
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"===> Run Precise Point Positioning for {crt_time.year}-{crt_time.doy:0>3d}")
        workdir = os.path.join(proc.proj_dir, str(crt_time.year),
                               f"{crt_time.doy:0>3d}_{proc.args.sys}_{proc.args.freq}_{proc.args.obs_comb}")
        if not os.path.isdir(workdir):
            os.makedirs(workdir)
        else:
            if not proc.args.keep_dir:
                shutil.rmtree(workdir)
                os.makedirs(workdir)
        os.chdir(workdir)
        logging.info(f"work directory = {workdir}")

        proc.config.update_gnssinfo(freq=3)
        with gt.timeblock("prepare obs"):
            if not proc.prepare_obs():
                crt_time += step
                continue

        with gt.timeblock("PPP-UC-3-AR"):
            proc.process_daily(obs_comb='UC', freq=3, fix=True)

        with gt.timeblock("PPP-UC-3-F"):
            proc.process_daily(obs_comb='UC', freq=3, fix=False)

        with gt.timeblock("PPP-UC-2-AR"):
            proc.process_daily(obs_comb='UC', freq=2, fix=True)

        with gt.timeblock("PPP-UC-2-F"):
            proc.process_daily(obs_comb='UC', freq=2, fix=False)

        with gt.timeblock("PPP-IF-3-AR"):
            proc.process_daily(obs_comb='IF', freq=3, fix=True)

        with gt.timeblock("PPP-IF-3-F"):
            proc.process_daily(obs_comb='IF', freq=3, fix=False)

        with gt.timeblock("PPP-IF-2-AR"):
            proc.process_daily(obs_comb='IF', freq=2, fix=True)

        with gt.timeblock("PPP-IF-2-F"):
            proc.process_daily(obs_comb='IF', freq=2, fix=False)

        # next day
        logging.info(f"Complete {crt_time.year}-{crt_time.doy:0>3d} ^_^")
        logging.info(f"------------------------------------------------------------------------\n")
        crt_time += step

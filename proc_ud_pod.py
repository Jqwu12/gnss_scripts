from proc_pod import ProcPod
from funcs import gnss_tools as gt, gnss_run as gr, gnss_files as gf
import os
import logging


class ProcUdPod(ProcPod):
    def __init__(self):
        super().__init__()
        self.default_args['cf'] = 'cf_udpod.ini'

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'POD_UD')
        self.result_dir = os.path.join(self.proj_dir, f"results_{self.args.sys}")

    def init_daily(self, crt_time, seslen):
        super().init_daily(crt_time, seslen)
        # self.config.change_data_path('rinexo', 'obs_fix')

    def prepare_obs(self):
        ambflagdir = os.path.join(self.base_dir, 'UPD', str(self.year()), f"{self.doy():0>3d}_G_grt", 'log_tb')
        gt.copy_ambflag_from(ambflagdir)
        if self.config.basic_check(files=['ambflag']):
            logging.info("Ambflag is ok ^_^")
            return True
        else:
            logging.critical("NO ambflag files ! skip to next day")
            return False

    def prepare(self):
        with gt.timeblock("Finished prepare obs"):
            if not self.prepare_obs():
                return False

        with gt.timeblock("Finished prepare ics"):
            if not self.prepare_ics():
                return False

        return True

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")
        logging.info(f"===> 1st iteration for precise orbit determination")
        gt.recover_files(self.config, ['ics', 'orb'])
        if os.path.isfile(f"rec_{self.year()}{self.doy():0>3d}"):
            os.remove(f"rec_{self.year()}{self.doy():0>3d}")
        if os.path.isfile(f"clk_{self.year()}{self.doy():0>3d}"):
            os.remove(f"clk_{self.year()}{self.doy():0>3d}")
        # gf.switch_ambflag(self.config, old='AMB', new='DEL', mode='12')
        self.config.update_process(apply_carrier_range='true', append=True)
        with gt.timeblock("Finished 1st POD"):
            self.process_1st_pod('AR1', True, False)
            self.process_edtres(jump=40, edt_amb=True)

        logging.info(f"===> 2nd iteration for precise orbit determination")
        with gt.timeblock("Finished 2nd POD"):
            self.process_float_pod('AR2', True, False)

        # gr.run_great(self.grt_bin, 'great_editres', self.config, nshort=600, bad=80, jump=80,
        #              label='editres', xmldir=self.xml_dir)
        # gf.switch_ambflag(self.config, mode='12')


if __name__ == '__main__':
    proc = ProcUdPod()
    proc.process_batch()

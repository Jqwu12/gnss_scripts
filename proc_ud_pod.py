from proc_gns_pod import ProcGnsPod
from funcs import gnss_tools as gt, gnss_run as gr, gnss_files as gf
import os
import logging


class ProcUdPod(ProcGnsPod):
    def __init__(self):
        super().__init__()
        self.default_args['cf'] = 'cf_udpod.ini'

    def update_path(self, all_path):
        super().update_path(all_path)
        self.proj_dir = os.path.join(self.config.config['common']['base_dir'], 'POD_UD')
        self.result_dir = os.path.join(self.proj_dir, f"results_{self.args.sys}")

    def init_daily(self, crt_time, seslen):
        super().init_daily(crt_time, seslen)
        self.config.change_data_path('rinexo', 'obs_fix')

    # def prepare(self):
    #     # with gt.timeblock("Finished prepare obs"):
    #     #     if not self.prepare_obs():
    #     #         return False
    #     tb_label = 'turboedit'
    #     gt.check_turboedit_log(self.config, self.nthread(), label=tb_label, path=self.xml_dir)
    #     if self.config.basic_check(files=['ambflag']):
    #         logging.info("Ambflag is ok ^_^")
    #         return True

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------")
        logging.info(f"Everything is ready: number of stations = {len(self.config.stalist())}, "
                     f"number of satellites = {len(self.config.all_gnssat())}")
        logging.info(f"===> 1st iteration for precise orbit determination")
        # gt.recover_files(self.config, ['ics'])
        gf.switch_ambflag(self.config, mode='12')
        # quality control
        with gt.timeblock("Finished 1st POD"):
            self.detect_outliers()
            gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)

        self.evl_orbdif('AR1')
        gr.run_great(self.grt_bin, 'great_editres', self.config, nshort=600, bad=50, jump=50,
                     label='editres', xmldir=self.xml_dir)
        gf.switch_ambflag(self.config, mode='12')

        logging.info(f"===> 2nd iteration for precise orbit determination")
        with gt.timeblock("Finished 2nd POD"):
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', label='podlsq', xmldir=self.xml_dir)
            gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)

        self.evl_orbdif('AR2')
        gr.run_great(self.grt_bin, 'great_editres', self.config, jump=50, label='editamb',
                     edt_amb=True, xmldir=self.xml_dir)
        gf.switch_ambflag(self.config, mode='12')

        logging.info(f"===> 3rd iteration for precise orbit determination")
        with gt.timeblock("Finished 3rd POD"):
            gr.run_great(self.grt_bin, 'great_podlsq', self.config, mode='POD_EST', label='podlsq', xmldir=self.xml_dir)
            gr.run_great(self.grt_bin, 'great_oi', self.config, label='oi', xmldir=self.xml_dir)

        self.evl_orbdif('AR3')


if __name__ == '__main__':
    proc = ProcUdPod()
    proc.process_batch()

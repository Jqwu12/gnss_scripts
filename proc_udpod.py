import os
import shutil
import logging
from proc_pod import ProcPod
from funcs import copy_ambflag_from, recover_files, switch_ambflag, timeblock


class ProcUdPod(ProcPod):
    default_args = {
        'dsc': 'GREAT GNSS Precise Orbit Determination',
        'num': 1, 'seslen': 24, 'intv': 300, 'obs_comb': 'IF', 'est': 'LSQ', 'sys': 'G',
        'freq': 2, 'cen': 'com', 'bia': 'cas', 'cf': 'cf_udpod.ini'
    }

    def prepare_obs(self):
        ambflagdir = os.path.join(self.base_dir, 'UPD', str(self.year), f"{self.doy:0>3d}_G_com", 'log_tb')
        copy_ambflag_from(ambflagdir)
        if self.basic_check(files=['ambflag']):
            logging.info("Ambflag is ok ^_^")
            return True
        else:
            logging.critical("NO ambflag files ! skip to next day")
            return False

    def process_daily(self):
        logging.info(f"------------------------------------------------------------------------\n{' '*36}"
                     f"Everything is ready: number of stations = {len(self._config.site_list)}, "
                     f"number of satellites = {len(self._config.all_gnssat)}")
        logging.info(f"===> 1st iteration for precise orbit determination")
        # ------------- For test! reset the workdir ---------------
        recover_files(self._config, ['ics', 'orb'])
        if os.path.isfile(f"rec_{self.year}{self.doy:0>3d}"):
            os.remove(f"rec_{self.year}{self.doy:0>3d}")
        if os.path.isfile(f"clk_{self.year}{self.doy:0>3d}"):
            os.remove(f"clk_{self.year}{self.doy:0>3d}")
        if os.path.isdir('orbdif'):
            shutil.rmtree('orbdif')
            os.makedirs('orbdif')
        # ----------------------------------------------------------
        # switch_ambflag(self._config, old='AMB', new='DEL', mode='12')
        self._config.carrier_range = True
        with timeblock("Finished 1st POD"):
            self.process_1st_pod('AR1', True, False)
            self.editres(jump=40, edt_amb=True)

        logging.info(f"===> 2nd iteration for precise orbit determination")
        with timeblock("Finished 2nd POD"):
            self.process_float_pod('AR2', True, False)

        # self.editres(bad=80, jump=80, nshort=600)
        # switch_ambflag(self._config, mode='12')


if __name__ == '__main__':
    proc = ProcUdPod.from_args()
    proc.process_batch()

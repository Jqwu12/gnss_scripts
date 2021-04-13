import os
import configparser
import shutil
import logging
import platform
import xml.etree.ElementTree as ET
from typing import List

from . import gnss_files as gf
from . import gnss_tools as gt
from .gnss_time import GnssTime
from .constants import gns_name, gns_id, gns_sat, gns_band, gns_sig, leo_df

default_process = {
    'apply_carrier_range': 'false',
    "bds_code_bias_corr": "true",
    "grad_mf": "BAR_SEVER",
    "gradient": "false",
    'ion_model': 'SION',
    "minimum_elev": "7",
    "minimum_elev_leo": "1",
    "obs_weight": "PARTELE",
    "phase": "true",
    "slip_model": "turboedit",
    'tropo': 'true',
    'tropo_mf': 'gmf',
    'tropo_model': 'saastamoinen'
}

default_ambiguity = {
    'carrier_range': "NO"
}


class GnssConfig:

    def __init__(self, conf):
        self.config = conf

        if not self.__check():
            raise RuntimeError('GnssConfig check failed')

    @classmethod
    def from_file(cls, file):
        if not os.path.isfile(file):
            raise FileNotFoundError('config file not found')
        config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        if not config.read(file, encoding='UTF-8'):
            raise IOError(f"read config file failed!")
        return cls(config)

    def __check(self):
        required_sections = ["process_scheme", "ambiguity_scheme", "common", "process_files"]
        for sec in required_sections:
            if not self.config.has_section(sec):
                logging.critical(f"[{sec}] not found in config!")
                return False

        path_sections = ['xml_template', 'process_files', 'source_files']
        for sec in self.config.sections():
            if sec not in path_sections:
                continue
            for opt in self.config.options(sec):
                val = self.config.get(sec, opt, raw=True)
                if platform.system() == 'Windows':
                    val = val.replace('/', '\\')
                    self.config.set(sec, opt, val)
                else:
                    val = val.replace('\\', '/')
                    self.config.set(sec, opt, val)
        return True

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, value):
        if not isinstance(value, (configparser.ConfigParser, configparser.RawConfigParser,
                                  configparser.SafeConfigParser)):
            raise TypeError('Expected a configparser')
        self._config = value

    def write(self, file):
        """ write the new config file """
        with open(file, 'w') as f:
            self.config.write(f)

    # -----------------------------------------------------------------------------------
    # general settings
    @property
    def beg_time(self) -> GnssTime:
        return GnssTime.from_str(self.config.get('process_scheme', 'time_beg'))

    @beg_time.setter
    def beg_time(self, value):
        if isinstance(value, str):
            self.config.set('process_scheme', 'time_beg', value)
        elif isinstance(value, GnssTime):
            self.config.set('process_scheme', 'time_beg', str(value))
        else:
            raise TypeError('Expected a string or GnssTime()')

    @property
    def end_time(self) -> GnssTime:
        return GnssTime.from_str(self.config.get('process_scheme', 'time_end'))

    @end_time.setter
    def end_time(self, value):
        if isinstance(value, str):
            self.config.set('process_scheme', 'time_end', value)
        elif isinstance(value, GnssTime):
            self.config.set('process_scheme', 'time_end', str(value))
        else:
            raise TypeError('Expected a string or GnssTime()')

    @property
    def intv(self) -> int:
        return self.config.getint('process_scheme', 'intv', fallback=30)

    @intv.setter
    def intv(self, value: int):
        if not isinstance(value, int):
            raise TypeError('Expected an int')
        self.config.set('process_scheme', 'intv', str(value))

    @property
    def seslen(self) -> float:
        return self.end_time.diff(self.beg_time)

    @property
    def estimator(self) -> str:
        return self.config.get('process_scheme', 'estimator', fallback='LSQ')

    @property
    def obs_comb(self) -> str:
        return self.config.get('process_scheme', 'obs_comb', fallback='IF')

    @obs_comb.setter
    def obs_comb(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        if value == 'UC':
            self.config.set('process_scheme', 'obs_comb', "UC")
            self.config.set('process_scheme', 'obs_combination', "RAW_ALL")
            self.config.set('process_scheme', 'ion_model', "SION")
        elif value == 'IF':
            self.config.set('process_scheme', 'obs_comb', "IF")
            self.config.set('process_scheme', 'obs_combination', "IONO_FREE")
            self.config.set('process_scheme', 'ion_model', "NONE")
        else:
            raise ValueError('Expected obs_comb is UC or IF')

    @property
    def lsq_mode(self) -> str:
        return self.config.get('process_scheme', 'lsq_mode', fallback='LSQ')

    @lsq_mode.setter
    def lsq_mode(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('process_scheme', 'lsq_mode', value)

    @property
    def orb_ac(self) -> str:
        return self.config.get('process_scheme', 'cen', fallback='com')

    @orb_ac.setter
    def orb_ac(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('process_scheme', 'cen', value)

    @property
    def bia_ac(self) -> str:
        return self.config.get('process_scheme', 'bia', fallback='').upper()

    @bia_ac.setter
    def bia_ac(self, value):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('process_scheme', 'bia', value.upper())

    @property
    def crd_constr(self):
        return self.config.get('process_scheme', 'crd_constr', fallback='EST').upper()

    @crd_constr.setter
    def crd_constr(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('process_scheme', 'crd_constr', value)

    @property
    def carrier_range(self) -> bool:
        return self.config.getboolean('process_scheme', 'apply_carrier_range', fallback=False)

    @carrier_range.setter
    def carrier_range(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError('Expected a bool')
        self.config.set('process_scheme', 'apply_carrier_range', str(value))

    @property
    def leo_mode(self) -> str:
        return self.config.get('process_scheme', 'leo_mode', fallback='D').upper()

    @leo_mode.setter
    def leo_mode(self, value: str):
        if not isinstance(value, str):
            raise ValueError('Expected a string')
        if value.startswith('D') or value.startswith('d'):
            self.config.set('process_scheme', 'leo_mode', 'D')
        elif value.startswith('K') or value.startswith('k'):
            self.config.set('process_scheme', 'leo_mode', 'K')
        else:
            self.config.set('process_scheme', 'leo_mode', '')

    @property
    def atoms_drag(self) -> str:
        """ Get atmosphere density model """
        return self.config.get('process_scheme', 'atmos_drag', fallback='MSISE00').upper()

    @atoms_drag.setter
    def atoms_drag(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('process_scheme', 'atmos_drag', value)

    def set_process(self, **kwargs):
        """ Update any process item in config """
        for key, val in kwargs.items():
            self.config.set('process_scheme', key, f"{val}")

    # -----------------------------------------------------------------------------------
    # GNSS settings
    @property
    def gsys(self) -> List[str]:
        return [gns_id(s) for s in self.config.get('process_scheme', 'sys', fallback='G') if gns_id(s)]

    @gsys.setter
    def gsys(self, value: str):
        """
        input: 'GREC'
        set value to: ['G', 'R', 'E', 'C']
        """
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('process_scheme', 'sys', ''.join([gns_id(s) for s in value if gns_id(s)]))

    @property
    def gsystem(self) -> List[str]:
        return [gns_name(s) for s in self.gsys]

    @property
    def freq(self) -> int:
        return self.config.getint('process_scheme', 'frequency', fallback=2)

    @freq.setter
    def freq(self, value: int):
        if not isinstance(value, int):
            raise TypeError('Expected an int')
        self.config.set('process_scheme', 'frequency', str(value))

    @property
    def band(self) -> dict:
        bd = {}
        for gs in self.gsystem:
            if self.config.has_option('process_scheme', f"band_{gns_id(gs)}"):
                bd[gs] = [s for s in self.config.get('process_scheme', f"band_{gns_id(gs)}") if s.isdigit()]
            else:
                bd[gs] = gns_band(gs)
        return bd

    @property
    def sat_rm(self) -> list:
        return self.config.get('process_scheme', 'sat_rm', fallback='').split()

    @sat_rm.setter
    def sat_rm(self, value: list):
        if not isinstance(value, list):
            raise TypeError('Expected a list')
        self.config.set('process_scheme', 'sat_rm', ' '.join(value))

    def gnsfreq(self, gsys) -> int:
        """ freq of one system """
        return min(int(self.freq), len(self.band[gns_name(gsys)]))

    def gnssat(self, gsys) -> list:
        if gsys not in self.gsystem:
            return []
        return gns_sat(gsys, self.sat_rm)

    def code_type(self):
        if self.obs_comb == "UC":
            return [f"P{i}" for i in range(1, self.freq + 1)]
        return [f"PC1{i}" for i in range(1, self.freq + 1)]

    def phase_type(self):
        if self.obs_comb == "UC":
            return [f"L{i}" for i in range(1, self.freq + 1)]
        return [f"LC1{i}" for i in range(1, self.freq + 1)]

    @property
    def all_gnssat(self):
        """ Get all GNSS sats """
        return [s for gs in self.gsystem for s in gns_sat(gs, self.sat_rm)]

    # -----------------------------------------------------------------------------------
    # site and LEO list
    @property
    def site_list(self) -> list:
        val = self.config.get('process_scheme', 'site_list', fallback='').split()
        val.sort()
        return val

    @site_list.setter
    def site_list(self, value: list):
        if not isinstance(value, list):
            raise TypeError('Expected a list')
        self.config.set('process_scheme', 'site_list', ' '.join(value))

    @property
    def leo_list(self) -> list:
        val = self.config.get('process_scheme', 'leo_list', fallback='').split()
        val = [s for s in val if s in list(leo_df.name)]
        val = list(set(val))
        val.sort()
        return val

    @leo_list.setter
    def leo_list(self, value: list):
        if not isinstance(value, list):
            raise TypeError('Expected a list')
        self.config.set('process_scheme', 'leo_list', ' '.join(value))

    @property
    def leo_sats(self):
        idx = leo_df.name == 'xxxx'
        for leo in self.leo_list:
            idx = idx | (leo_df.name == leo)
        sats = list(leo_df[idx].svn)
        sats.sort()
        return sats

    @property
    def all_sites(self):
        return self.site_list + self.leo_list

    @property
    def site_receivers(self):
        return [{'rec': s, 'rec_u': s.upper(), 'rec_l': s, 'leo': False} for s in self.site_list]

    @property
    def leo_receivers(self):
        return [{'rec': s, 'rec_u': s.upper(), 'rec_l': leo_df[leo_df.name == s].svn.values[0], 'leo': True}
                for s in self.leo_list]

    @property
    def all_receivers(self):
        return self.site_receivers + self.leo_receivers

    def remove_leo(self, leo_rm: list):
        """ Remove LEO satellite in config """
        if not isinstance(leo_rm, list):
            return
        leo_rm = [s for s in leo_rm if s in self.leo_list]
        if not leo_rm:
            return
        self.leo_list = list(set(self.leo_list).difference(set(leo_rm)))
        logging.warning(f"LEOs {' '.join(leo_rm)} are removed")

    def remove_site(self, site_rm: list):
        """ Remove ground stations in config """
        if not isinstance(site_rm, list):
            return
        site_rm = [s for s in site_rm if s in self.site_list]
        if not site_rm:
            return
        self.site_list = list(set(self.site_list).difference(set(site_rm)))
        logging.warning(f"STATIONS {' '.join(site_rm)} are removed")

    # -----------------------------------------------------------------------------------
    # ambiguity_scheme settings
    @property
    def upd_mode(self) -> str:
        if self.orb_ac in ['grm', 'grg', 'gr2']:
            return 'IRC'
        if self.orb_ac == 'cod' and self.bia_ac in ['COD', 'WHU']:
            return 'OSB'
        return self.config.get('ambiguity_scheme', 'upd_mode', fallback='UPD')

    @upd_mode.setter
    def upd_mode(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        if self.orb_ac in ['grm', 'grg', 'gr2']:
            self.config.set('ambiguity_scheme', 'upd_mode', 'IRC')
        if self.orb_ac == 'cod' and self.bia_ac in ['COD', 'WHU']:
            self.config.set('ambiguity_scheme', 'upd_mode', 'OSB')
        self.config.set('ambiguity_scheme', 'upd_mode', value)

    @property
    def carrier_range_out(self) -> bool:
        return self.config.getboolean('ambiguity_scheme', 'carrier_range_out', fallback=False)

    @carrier_range_out.setter
    def carrier_range_out(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError('Expect a bool')
        self.config.set('ambiguity_scheme', 'carrier_range_out', str(value))

    def set_ambiguity(self, **kwargs):
        """ Update any ambiguity item in config """
        for key, val in kwargs.items():
            self.config.set('ambiguity_scheme', key, f"{val}")

    # -----------------------------------------------------------------------------------
    # paths and files
    @property
    def grt_bin(self) -> str:
        return self.config.get('common', 'grt_bin', fallback='')

    @grt_bin.setter
    def grt_bin(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('common', 'grt_bin', os.path.abspath(value))

    @property
    def base_dir(self) -> str:
        return self.config.get('common', 'base_dir', fallback='')

    @base_dir.setter
    def base_dir(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('common', 'base_dir', os.path.abspath(value))

    @property
    def sys_data(self) -> str:
        return self.config.get('common', 'sys_data', fallback='')

    @sys_data.setter
    def sys_data(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('common', 'sys_data', os.path.abspath(value))

    @property
    def gnss_data(self) -> str:
        return self.config.get('common', 'gnss_data', fallback='')

    @gnss_data.setter
    def gnss_data(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('common', 'gnss_data', os.path.abspath(value))

    @property
    def upd_data(self) -> str:
        return self.config.get('common', 'upd_data', fallback='')

    @upd_data.setter
    def upd_data(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Expected a string')
        self.config.set('common', 'upd_data', os.path.abspath(value))

    @property
    def workdir(self):
        return self._file_name("work_dir", check=False)

    def change_data_path(self, file, target):
        """
        inputs: file            original file defined in config
                target          target directory defined in config
        """
        support_files = ['rinexo', 'rinexn', 'rinexc', 'sp3', 'bia']  # can be added later
        if file not in support_files:
            logging.warning(f"change_data_path failed! supported files {' '.join(support_files)}")
            return
        if not self.config.has_option("process_files", file):
            logging.warning(f"change_data_path failed! cannot find {file} in [process_files]")
            return
        if not self.config.has_option("process_files", target):
            logging.warning(f"change_data_path failed! cannot find {target} in [process_files]")
            return
        if platform.system() == 'Windows':
            sep = '\\'
        else:
            sep = '/'
        old_path = self.config.get("process_files", file, raw=True)
        target_path = self.config.get("process_files", target, raw=True)
        ipos = old_path.rfind(sep)
        old_file = old_path[ipos + 1:]
        new_path = f"{target_path}{sep}{old_file}"
        self.config.set("process_files", file, new_path)
        logging.info(f"change {file} directory to {target_path}")

    def _file_name(self, f_type, cf_vars=None, sec='process_files', check=False, quiet=False):
        if cf_vars is None:
            cf_vars = {}
        cfv = self.beg_time.config_timedic()
        cfv.update(cf_vars)
        f = self.config.get(sec, f_type, vars=cfv, fallback='')
        if check and not os.path.isfile(f):
            if not quiet:
                logging.warning(f"file not found {f}")
            return ''
        return f

    def file_name(self, f_type, cf_vars=None, sec='process_files', check=False, quiet=False):
        return self._file_name(f_type, cf_vars, sec, check, quiet)

    def _daily_file(self, f_type, cf_vars=None, sec='process_files', check=False):
        if cf_vars is None:
            cf_vars = {}
        if f_type == 'sp3':
            t_beg = self.beg_time - 5400
            t_end = self.end_time + 5400
        else:
            t_beg = self.beg_time
            t_end = self.end_time - 1
        end_time = GnssTime(t_end.mjd, 86399.0)
        f_list = []
        while t_beg < end_time:
            cf_vars.update(t_beg.config_timedic())
            f = self._file_name(f_type, cf_vars, sec, check)
            if f:
                f_list.append(f)
            t_beg += 86400
        return f_list

    def get_xml_file(self, f_type: str, sattype='gns', sec='process_files', check=False, remove=False) -> list:
        # -------------------------------------------------------------------------------
        # files per site
        if f_type in ['rinexo', 'kin', 'ambupd_in', 'recover_all', 'ambflag'] or f_type.startswith('ambflag1'):
            rec_rm = []
            f_list = []
            if f_type == 'recover_all':
                f_type = 'recover_in'
            for rec in self.all_receivers:
                if f_type == 'rinexo':
                    fs = self._daily_file(f_type, rec, sec, check)
                    if rec['leo'] and check:
                        f_atx = self._file_name('atx')
                        fs = [f for f in fs if gf.check_rnxo_ant(f, f_atx)]
                else:
                    f = self._file_name(f_type, rec, sec, check)
                    fs = [f] if f else []
                    if f_type == 'ambflag' and check:
                        intv = min(self.intv, 30)
                        nobs = self.seslen / intv * 2
                        fs = [f for f in fs if gf.check_ambflag(f, nobs)]
                f_list.extend(fs)
                if not fs:
                    rec_rm.append(rec)
            if remove:
                self.remove_site([rec['rec'] for rec in rec_rm if not rec['leo']])
                self.remove_leo([rec['rec'] for rec in rec_rm if rec['leo']])
                self.remove_ambflag_file([rec['rec'] for rec in rec_rm])
            return f_list
        # -------------------------------------------------------------------------------
        # common files
        elif f_type == 'sp3':
            f_list = []
            if 'gns' in sattype:
                f_list.extend(self._daily_file('sp3', {}, sec, check))
            if 'leo' in sattype:
                f_list.extend(self.get_xml_file('kin', 'leo', sec, check))
            return f_list
        elif f_type in ['rinexn', 'rinexc']:
            return self._daily_file(f_type, {}, sec, check)
        elif f_type == 'rinexc_all':
            fl = self._daily_file('rinexc', {}, sec, check)
            fs = self._file_name('recclk', {}, sec, check)
            if fs:
                fl.append(fs)
            return fl
        elif f_type == 'clk':
            fs = [self._file_name('satclk', {}, sec, check), self._file_name('recclk', {}, sec, check)]
            return [f for f in fs if f]
        elif f_type == 'biabern':
            if not self.bia_ac:
                return [f for f in [self._file_name('dcb_p1c1', {}, sec, check),
                                    self._file_name('dcb_p2c2', {}, sec, check)] if f]
            return self._daily_file('bia', {}, sec, check)
        elif f_type == 'upd':
            f_list = []
            if self.upd_mode == 'OSB':
                return []
            if self.upd_mode == 'UPD':
                f_list.extend(self._daily_file('upd_nl', {}, sec, check))
            f_list.append(self._file_name('upd_wl', {}, sec, check))
            if self.freq > 2:
                f_list.append(self._file_name('upd_ewl', {}, sec, check))
            if self.freq > 3:
                f_list.append(self._file_name('upd_ewl24', {}, sec, check))
            if self.freq > 4:
                f_list.append(self._file_name('upd_ewl25', {}, sec, check))
            return [f for f in f_list if f]
        # -------------------------------------------------------------------------------
        # files for POD
        elif f_type in ['attitude', 'pso']:
            f_list = []
            for rec in self.leo_receivers:
                fs = self._daily_file(f_type, rec, sec, check)
                if f_type == 'attitude' and check:
                    fs = [f for f in fs if gf.check_att_file(f)]
                f_list.extend(fs)
            return f_list
        elif f_type in ['orb', 'ics', 'orbdif']:
            f_list = []
            if 'leo' in sattype:
                f_list.append(self._file_name(f_type, {'sattype': 'leo'}, sec, check))
            if 'gns' in sattype:
                f_list.append(self._file_name(f_type, {'sattype': 'gns'}, sec, check))
            return f_list
        elif f_type == 'solar':
            fs = [self._file_name('solar_flux', {}, sec, check), self._file_name('geomag_kp', {}, sec, check)]
            return [f for f in fs if f]
        elif f_type == 'solar_MSISE':
            fs = [self._file_name('solar_flux_MSISE', {}, sec, check), self._file_name('geomag_ap', {}, sec, check)]
            return [f for f in fs if f]
        else:
            f = self._file_name(f_type, {}, sec, check)
            return [f] if f else []

    def remove_ambflag_file(self, sites: List[str]):
        for f_type in ['ambflag', 'ambflag13', 'ambflag14', 'ambflag15']:
            for site in sites:
                try:
                    os.remove(self._file_name(f_type, {'rec': site, 'rec_u': site.upper()}, quiet=True))
                except FileNotFoundError:
                    continue

    def basic_check(self, opts=None, files=None):
        """ check the necessary settings and existence of files """
        if files is None:
            files = []
        if opts is None:
            opts = []
        # check process schemes
        opts_base = ['time_beg', 'time_end', 'intv', 'frequency']
        opts = opts_base + opts
        for opt in opts:
            if not self.config.has_option('process_scheme', opt):
                logging.error(f"basic check failed! cannot find {opt} in process_scheme")
                return False
        # check necessary files
        for file in files:
            if not self.get_xml_file(file, check=True, remove=True):
                logging.error(f"basic check failed! cannot find {file} files")
                return False
        return True

    def copy_sys_data(self):
        """ copy source_files to process_files """
        f_rst = []
        for f_type in self.config.options('source_files'):
            if f_type in ['upd_ewl25', 'upd_ewl24', 'upd_ewl', 'upd_wl', 'upd_nl'] and self.upd_mode != 'UPD':
                continue
            if f_type == 'ifcb' and (self.freq < 3 or 'G' not in self.gsys):
                continue
            if f_type == 'attitude' and not self.leo_list:
                continue
            fs_src = self.get_xml_file(f_type, sec='source_files', check=False)
            fs_dst = self.get_xml_file(f_type, sec='process_files', check=False)
            if len(fs_src) != len(fs_src):
                logging.warning(f"Number of source files ({f_type}, {len(fs_src)}) is not equal to target "
                                f"files ({len(fs_dst)})")

            for f1, f2 in zip(fs_src, fs_dst):
                try:
                    shutil.copy(f1, f2)
                except FileNotFoundError:
                    logging.warning(f'copy failed! file not found {f1}')
                    continue
                except shutil.SameFileError:
                    logging.warning(f'copy failed! files are same {f1}')
                    continue
                f_rst.append(os.path.basename(f1))
        if f_rst:
            logging.info(f"files copied to work directory: {', '.join(f_rst)}")

    def set_ref_clk(self, mode='sat', sats=None):
        ref_sats = ['G08', 'G05', 'E01', 'E02', 'C08', 'R01']
        ref_sites = ['hob2', 'gop6', 'ptbb', 'algo']
        if sats is None:
            sats = []
        sat_list = [s for s in self.all_gnssat if s in sats]
        if mode == 'sat':
            for sat in ref_sats:
                if sat in sat_list:
                    return sat
            sat = self.all_gnssat[0]
            logging.warning(f"Cannot find ref sat in {' '.join(ref_sats)}, use the first sat {sat}")
            return sat
        else:
            for site in ref_sites:
                if site in self.site_list:
                    return site.upper()
            site = self.site_list[0]
            logging.warning(f"Cannot find ref site in {' '.join(ref_sites)}, use the first site {site}")
            return site

    # -----------------------------------------------------------------------------------
    # get xml nodes
    def get_xml_gen(self, opts: List[str]) -> ET.Element:
        gen = ET.Element('gen')
        beg, end = ET.SubElement(gen, 'beg'), ET.SubElement(gen, 'end')
        beg.text, end.text = str(self.beg_time), str(self.end_time)
        if 'intv' in opts:
            elem = ET.SubElement(gen, 'int')
            elem.text = str(self.intv)
        if 'sys' in opts:
            elem = ET.SubElement(gen, 'sys')
            elem.text = ' '.join(self.gsystem)
        if 'rec' in opts:
            if self.leo_list:
                elem = ET.SubElement(gen, 'rec', attrib={'type': 'leo', 'mode': self.leo_mode})
                elem.text = ' '.join([s.upper() for s in self.leo_list])
            if self.site_list:
                elem = ET.SubElement(gen, 'rec')
                elem.text = ' '.join([s.upper() for s in self.site_list])
        if 'est' in opts:
            elem = ET.SubElement(gen, 'est')
            elem.text = self.estimator
        return gen

    def get_xml_gns(self) -> List[ET.Element]:
        elems = []
        for gs in self.gsystem:
            elem = ET.Element(gs.lower(), attrib={'sigma_C': str(gns_sig(gs)['code']),
                                                  'sigma_L': str(gns_sig(gs)['phase']),
                                                  'sigma_C_LEO': str(gns_sig(gs)['code_leo']),
                                                  'sigma_L_LEO': str(gns_sig(gs)['phase_leo'])})
            esat = ET.SubElement(elem, 'sat')
            esat.text = ' '.join(gns_sat(gs, self.sat_rm))
            eband = ET.SubElement(elem, 'band')
            eband.text = ' '.join([str(b) for b in self.band[gs]])
            eband.text = ' '.join([str(self.band[gs][i]) for i in range(self.gnsfreq(gs))])
            efreq = ET.SubElement(elem, 'freq')
            efreq.text = ' '.join([str(f) for f in range(1, self.gnsfreq(gs) + 1)])
            elems.append(elem)
        return elems

    def get_xml_ambiguity(self) -> ET.Element:
        amb_dict = default_ambiguity.copy()
        for opt in self.config.options('ambiguity_scheme'):
            amb_dict[opt] = self.config.get('ambiguity_scheme', opt).upper()
        amb_dict['dd_mode'] = "RAW_CB_WN" if self.obs_comb == "UC" else "IF_CB_WN"
        amb_dict['upd_mode'] = self.upd_mode
        amb_dict['carrier_range_out'] = 'YES' if self.carrier_range_out else 'NO'
        if self.lsq_mode == "EPO":
            amb_dict['min_common_time'] = '0'

        amb = ET.Element('ambiguity')
        for key, val in amb_dict.items():
            if key == 'fix_mode':
                continue
            if key.endswith('_decision'):
                maxdev, maxsig, alpha, *_ = val.split() + ['', '', '']
                ET.SubElement(amb, key, attrib={'maxdev': maxdev, 'maxsig': maxsig, 'alpha': alpha})
            else:
                elem = ET.SubElement(amb, key)
                elem.text = val
        return amb

    def get_xml_process(self) -> ET.Element:
        opt_list = ['obs_combination', 'ion_model', 'frequency', 'crd_constr', 'sig_init_crd', 'lsq_mode',
                    'sysbias_model', 'ztd_model', 'apply_carrier_range', 'ambfix']
        proc_dict = default_process.copy()
        for opt in opt_list:
            if self.config.has_option('process_scheme', opt):
                proc_dict[opt] = self.config.get('process_scheme', opt)

        proc = ET.Element('process', attrib=proc_dict)
        return proc

    def get_xml_inputs(self, fs: List[str], check=True, sattype='gns') -> ET.Element:
        inps = ET.Element('inputs')
        for f in fs:
            elem = ET.SubElement(inps, f)
            elem.text = ' '.join(self.get_xml_file(f, sattype=sattype, check=check))
        return inps

    @staticmethod
    def get_xml_turboedit(isleo=False) -> ET.Element:
        tb = ET.Element('turboedit', attrib={'lite_mode': 'false'})
        ET.SubElement(tb, 'amb_output', attrib={'valid': 'true'})
        ET.SubElement(tb, 'ephemeris', attrib={'valid': 'true'})
        ET.SubElement(tb, 'check_pc', attrib={'pc_limit': '250', 'valid': 'false' if isleo else 'true'})
        ET.SubElement(tb, 'check_mw', attrib={'mw_limit': '4', 'valid': 'true'})
        ET.SubElement(tb, 'check_gf', attrib={'gf_limit': '1', 'gf_rms_limit': '2', 'valid': 'true'})
        ET.SubElement(tb, 'check_sf', attrib={'sf_limit': '1', 'valid': 'false'})
        ET.SubElement(tb, 'check_gap', attrib={'gap_limit': '20', 'valid': 'true'})
        ET.SubElement(tb, 'check_short', attrib={'short_limit': '10', 'valid': 'true'})
        ET.SubElement(tb, 'check_statistics', attrib={'min_percent': '60', 'min_mean_nprn': '4',
                                                      'max_mean_namb': '50' if isleo else '3', 'valid': 'true'})
        return tb

    def get_xml_force(self, sattype='gns') -> ET.Element:
        fm = ET.Element('force_model')
        xml_temp = self.config.get('xml_template', 'oi', fallback='')
        if not os.path.isfile(xml_temp):
            logging.warning(f"xml template for oi {xml_temp} not found!")
            return fm
        ref_tree = ET.parse(xml_temp)
        ref_root = ref_tree.getroot()
        ref_fm = ref_root.find('force_model')
        for child in ref_fm:
            if 'leo' in sattype:
                if child.get("ID").lower() in self.leo_sats or child.get("ID") == "LEO":
                    atmosphere = child.find("atmosphere")
                    atmosphere.set("model", self.atoms_drag)
                    fm.append(child)
            if 'gns' in sattype:
                if child.get("ID").upper() in self.gsystem or child.get("ID") == "GNS":
                    fm.append(child)
        return fm

    def get_xml_receiver(self, use_res_crd=False) -> ET.Element:
        receiver = ET.Element('receiver')
        # get coordinates from IGS snx file
        crd_data = gt.get_crd_snx(' '.join(self.get_xml_file('sinex', check=True)), self.site_list)
        # get coordinates from GREAT residuals file
        if use_res_crd:
            f_res = self.get_xml_file('recover_in', check=True)
            if f_res:
                crd_res = gt.get_crd_res(f_res[0], self.site_list)
                crd_data = crd_data.append(crd_res)
        if crd_data.empty:
            return receiver
        # get receiver elements
        for site in self.site_list:
            df = crd_data[crd_data.site == site]
            df_x = df[df.type == 'crd_x'].sort_values(by=['obj'], ascending=False)
            df_y = df[df.type == 'crd_y'].sort_values(by=['obj'], ascending=False)
            df_z = df[df.type == 'crd_z'].sort_values(by=['obj'], ascending=False)
            if df_x.empty or df_y.empty or df_z.empty:
                continue
            ET.SubElement(receiver, 'rec', attrib={
                'X': f'{df_x.val.values[0]:20.8f}',
                'Y': f'{df_y.val.values[0]:20.8f}',
                'Z': f'{df_z.val.values[0]:20.8f}',
                'dX': f'{df_x.sig.values[0]:8.4f}',
                'dY': f'{df_y.sig.values[0]:8.4f}',
                'dZ': f'{df_z.sig.values[0]:8.4f}',
                'id': site.upper(), 'obj': df_x.obj.values[0]
            })

        return receiver


__all__ = ['GnssConfig']

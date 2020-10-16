import os
import configparser
import shutil
import logging
import platform
import copy
import gnss_files as gf
from gnss_time import GNSStime
from constants import _GNS_INFO, _GNS_NAME, _LEO_INFO


def _raise_error(msg):
    logging.critical(msg)
    raise SystemExit(msg)


class GNSSconfig:

    def __init__(self, f_config):
        self.config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        if os.path.isfile(f_config):
            self.config.read(f_config, encoding='UTF-8')
        else:
            _raise_error(f"config file {f_config} not exist!")
        if not self.config.has_section('process_scheme'):
            self.config.add_section('process_scheme')
        if not self.config.has_section('common'):
            self.config.add_section('common')
        if not self.config.has_option('common', 'sys_data'):
            sys_data = '/home/yuanyongqiang/data_new/WJQ/projects/sys_data'
            self.config.set('common', 'sys_data', sys_data)
        if not self.config.has_option('common', 'gns_data'):
            gns_data = '/home/yuanyongqiang/data_new/WJQ/data'
            self.config.set('common', 'gns_data', gns_data)

    def copy(self):
        return copy.deepcopy(self)

    def update_timeinfo(self, time_beg, time_end, intv):
        """ update the time information in config file """
        self.config.set('process_scheme', 'time_beg', time_beg.datetime())
        self.config.set('process_scheme', 'time_end', time_end.datetime())
        self.config.set('process_scheme', 'intv', f"{intv:d}")

    def update_gnssinfo(self, sys=None, freq=None, obs_model=None, est=None, sat_rm=None):
        """ update the gnss settings in config file """
        if sys:
            self.config.set('process_scheme', 'sys', sys)
        if freq:
            self.config.set('process_scheme', 'frequency', f"{freq:d}")
        if est:
            self.config.set('process_scheme', 'lsq_mode', est)
        if obs_model == 'IF':
            self.config.set('process_scheme', 'obs_comb', "IF")
            self.config.set('process_scheme', 'obs_combination', "IONO_FREE")
            self.config.set('process_scheme', 'ion_model', "NONE")
        else:
            self.config.set('process_scheme', 'obs_comb', "UDUC")
            self.config.set('process_scheme', 'obs_combination', "RAW_ALL")
            self.config.set('process_scheme', 'ion_model', "SION")
        if sat_rm:
            self.config.set('process_scheme', 'sat_rm', sat_rm)  # currently not used

    def update_prodinfo(self, cen='grm', bia=''):
        """ update the IGS product settings in config file """
        self.config.set('process_scheme', 'cen', cen)
        if bia:
            self.config.set('process_scheme', 'bia', bia.upper())
        else:
            self.config.set('process_scheme', 'bia', '')

    def update_leolist(self, leo_list):
        """ update the LEO satellite list in config file """
        info = ''
        if isinstance(leo_list, list):
            for leo in leo_list:
                if leo in _LEO_INFO.keys():
                    info = info + ' ' + leo
                else:
                    logging.warning(f"Unknown LEO satellite (long name) {leo}")
        else:
            info = leo_list
        self.config.set('process_scheme', 'leo_list', info)

    def update_stalist(self, sta_list):
        """ update the ground station list in config file """
        info = ''
        if isinstance(sta_list, list):
            for leo in sta_list:
                info = info + ' ' + leo
        else:
            info = sta_list
        self.config.set('process_scheme', 'sta_list', info)
    
    def update_pathinfo(self, sys_data, gns_data, upd_data=""):
        """ update the path information in config according to different OS """
        if os.path.isdir(sys_data):
            self.config.set('common', 'sys_data', os.path.abspath(sys_data))
        else:
            _raise_error(f"sys_data dir {sys_data} not exist!")

        if os.path.isdir(gns_data):
            self.config.set('common', 'gns_data', os.path.abspath(gns_data))
        else:
            _raise_error(f"gns_data dir {gns_data} not exist!")

        if upd_data:
            if os.path.isdir(upd_data):
                self.config.set('common', 'upd_data', os.path.abspath(upd_data))
            else:
                os.makedirs(upd_data)
                # _raise_error(f"upd_data dir {upd_data} not exist!")

        path_sections = ['xml_template', 'process_files', 'source_files']
        if platform.system() == 'Windows':
            for path_sec in path_sections:
                if self.config.has_section(path_sec):
                    for key in self.config[path_sec]:
                        val = self.config.get(path_sec, key, raw=True)
                        if '/' in val:
                            val = val.replace('/', '\\')
                            self.config.set(path_sec, key, val)
        else:
            for path_sec in path_sections:
                if self.config.has_section(path_sec):
                    for key in self.config[path_sec]:
                        val = self.config.get(path_sec, key, raw=True)
                        if '\\' in val:
                            val = val.replace('\\', '/')
                            self.config.set(path_sec, key, val)

    def update_process(self, append=False, **kwargs):
        """ Update any process item in config """
        for key, val in kwargs.items():
            if not append:
                if self.config.has_option('process_scheme', key):
                    self.config.set('process_scheme', key, val)
            else:
                self.config.set('process_scheme', key, val)

    def update_ambiguity(self, append=False, **kwargs):
        """ Update any process item in config """
        for key, val in kwargs.items():
            if not append:
                if self.config.has_option('ambiguity_scheme', key):
                    self.config.set('ambiguity_scheme', key, val)
            else:
                self.config.set('ambiguity_scheme', key, val)

    def write_config(self, f_config_new):
        """ write the new config file """
        with open(f_config_new, 'w') as configfile:
            self.config.write(configfile)

    def timeinfo(self):
        """ begin and end time in config file"""
        if self.config.has_option('process_scheme', 'time_beg') and self.config.has_option('process_scheme',
                                                                                           'time_end'):
            beg = self.config.get('process_scheme', 'time_beg')
            end = self.config.get('process_scheme', 'time_end')
            if beg == 'NONE' or end == 'NONE':
                _raise_error("Cannot find time_beg/time_end in [process_scheme]")
            t_beg = GNSStime()
            t_end = GNSStime()
            t_beg.set_datetime(beg)
            t_end.set_datetime(end)
            return t_beg, t_end
        else:
            _raise_error("Cannot find time_beg/time_end in [process_scheme]")

    def xml_process(self):
        """ return a dict for xml <process> """
        proc_dict = {
            "grad_mf": "BAR_SEVER", "gradient": "false", "minimum_elev": "7", "minimum_elev_leo": "1",
            "obs_weight": "PARTELE", "phase": "true", "slip_model": "turboedit"
        }
        opt_list = ['obs_combination', 'ion_model', 'frequency', 'crd_constr', 'sig_init_crd', 'lsq_mode', 'sysbias_model', 'ztd_model']
        for opt in opt_list:
            if self.config.has_option('process_scheme', opt):
                proc_dict[opt] = self.config.get('process_scheme', opt).upper()
        if len(self.config.get('process_scheme', 'tropo').split()) == 3:
            proc_dict['tropo'] = self.config.get('process_scheme', 'tropo').split()[0]
            proc_dict['tropo_mf'] = self.config.get('process_scheme', 'tropo').split()[1]
            proc_dict['tropo_model'] = self.config.get('process_scheme', 'tropo').split()[2]
        if proc_dict['obs_combination'] == "RAW_ALL":
            proc_dict['ion_model'] = "SION"
        if "BDS" in self.gnssys():
           proc_dict["bds_code_bias_corr"] = "true"
        return proc_dict

    def xml_ambiguity(self):
        """ return a dict for xml <ambiguity> """
        if not self.config.has_section('ambiguity_scheme'):
            logging.error("No [ambiguity_scheme] in config file")
            return {}
        opt_list = ['dd_mode', 'is_ppprtk', 'fix_mode', 'ratio', 'part_fix', 'carrier_range', 'add_leo', 'all_baselines',
                    'min_common_time', 'baseline_length_limit', 'widelane_interval']
        amb_dict = {'carrier_range': "NO"}
        for opt in opt_list:
            if self.config.has_option('ambiguity_scheme', opt):
                amb_dict[opt] = self.config.get('ambiguity_scheme', opt).upper()
        if self.is_integer_clock():
            if self.is_integer_clock_osb():
                amb_dict['upd_mode'] = 'OSB'
            else:
                amb_dict['upd_mode'] = 'IRC'
        else:
            amb_dict['upd_mode'] = 'UPD'
        if self.config['process_scheme']['lsq_mode'] == "EPO":
            amb_dict['min_common_time'] = '0'
        if self.config.has_option('ambiguity_scheme', 'extra_widelane_decision'):
            if len(self.config.get('ambiguity_scheme', 'extra_widelane_decision').split()) == 3:
                amb_dict['extra_widelane_decision'] = self.config.get('ambiguity_scheme', 'extra_widelane_decision').split()
        if self.config.has_option('ambiguity_scheme', 'widelane_decision'):
            if len(self.config.get('ambiguity_scheme', 'widelane_decision').split()) == 3:
                amb_dict['widelane_decision'] = self.config.get('ambiguity_scheme', 'widelane_decision').split()
        if self.config.has_option('ambiguity_scheme', 'narrowlane_decision'):
            if len(self.config.get('ambiguity_scheme', 'narrowlane_decision').split()) == 3:
                amb_dict['narrowlane_decision'] = self.config.get('ambiguity_scheme', 'narrowlane_decision').split()
        return amb_dict

    def gnssys(self):
        """ GNS system information """
        if self.config.has_option('process_scheme', 'sys'):
            str_sys = self.config.get('process_scheme', 'sys')
            if str_sys == 'NONE':
                logging.warning("Cannot find sys in [process_scheme]")
                return ''
            str_sys = str_sys.replace('+', '')
            str_sys = str_sys.replace(' ', '')
            sys_out = ""
            for i in range(len(str_sys)):
                sys = str_sys[i]
                if sys in _GNS_NAME.keys():
                    sys_out = sys_out + " " + _GNS_NAME[sys]
            return sys_out.strip()
        else:
            logging.warning("Cannot find sys in [process_scheme]")

    def all_receiver(self):
        """ Get all receiver names """
        leo_list = self.leo_recs()
        sta_list = self.stalist()
        all_list = leo_list + sta_list
        out = " ".join(all_list)
        return out

    def leolist(self):
        """ LEO satellite list in config file """
        if self.config.has_option('process_scheme', 'leo_list'):
            info = self.config.get('process_scheme', 'leo_list')
            if info.strip() == 'NONE':
                return []
            else:
                return info.split()
        else:
            # logging.warning("Cannot find leo_list in [process_scheme]")
            return []

    def leo_recs(self):
        """ LEO satellite receivers in config file """
        recs = []
        for leo in self.leolist():
            leo_abbr = _LEO_INFO[leo]['abbr']
            recs.append(leo_abbr)
        return recs

    def stalist(self):
        """ ground station list in config file """
        if self.config.has_option('process_scheme', 'sta_list'):
            info = self.config.get('process_scheme', 'sta_list')
            if info.strip() == 'NONE':
                return []
            else:
                return info.split()
        else:
            logging.warning("Cannot find sta_list in [process_scheme]")
            return []

    def remove_leo(self, leo_rm):
        """ Remove LEO satellite in config """
        if leo_rm:
            leo_list = self.leolist()
            leo_list_new = list(set(leo_list).difference(set(leo_rm)))
            self.update_leolist(leo_list_new)
            leo_rm_str = " ".join(leo_rm)
            logging.warning(f"LEOs {leo_rm_str} are removed")

    def remove_sta(self, sta_rm):
        """ Remove ground stations in config """
        if sta_rm:
            sta_list = self.stalist()
            sta_list_new = list(set(sta_list).difference(set(sta_rm)))
            self.update_stalist(sta_list_new)
            sta_rm_str = " ".join(sta_rm)
            logging.warning(f"STATIONs {sta_rm_str} are removed")

    def grtbin(self):
        """ GREAT bin path in config file """
        if self.config.has_option('process_scheme', 'grt_bin'):
            grt_bin = self.config.get('process_scheme', 'grt_bin')
            if grt_bin != 'NONE':
                return grt_bin
        else:
            logging.warning("Cannot find grt_bin in [process_scheme]")

    def get_atoms_drag(self):
        """ Get atmosphere density model """
        if self.config.has_option('process_scheme', 'atmos_drag'):
            atmos_drag = self.config.get('process_scheme', 'atmos_drag').upper()
            if atmos_drag not in ["DTM94", "MSISE00"]:
                logging.warning(f"unknown atmosphere density model {atmos_drag}, set to MSISE00")
                atmos_drag = "MSISE00"
        else:
            atmos_drag = "MSISE00"
            logging.warning("no atmos_drag in config file, set to MSISE00")
        return atmos_drag

    def _get_sinexfile(self, check=False, conf_opt='process_files'):
        t_beg, t_end = self.timeinfo()
        t_use = t_beg.time_increase(-86400*30)
        cf_vars = t_use.config_timedic()
        f_name = self.config.get(conf_opt, 'sinex', vars=cf_vars)
        if check:
            if not os.path.isfile(f_name):
                f_name = ''
        return f_name

    def _get_dailyfile(self, f_type, config_vars=None, check=False, conf_opt='process_files'):
        if config_vars is None:
            config_vars = {}
        if not self.config.has_option(conf_opt, f_type):
            logging.error(f"Cannot find {f_type} in [{conf_opt}]")
            return ''
        t_beg, t_end = self.timeinfo()
        if f_type == 'sp3':
            t_beg = t_beg.time_increase(-5400.0)
            t_end = t_end.time_increase(5400.0)
        else:
            t_end = t_end.time_increase(-1)
        time = t_beg
        end = GNSStime()
        end.set_mjd(t_end.mjd, 86399.0)
        f_out = ""
        while time.time_difference(end) > 0.0:
            cf_vars = config_vars
            cf_vars.update(time.config_timedic())
            f_name = self.config.get(conf_opt, f_type, vars=cf_vars)
            if check:
                if not os.path.isfile(f_name):
                    logging.warning(f"file not found {f_name}")
                    f_name = ''
            if len(f_name) != 0:
                f_out = f_out + " " + f_name
            time = time.time_increase(86400.1)
        return f_out

    def _get_file(self, f_type, config_vars=None, check=False, conf_opt='process_files'):
        if config_vars is None:
            config_vars = {}
        if not self.config.has_option(conf_opt, f_type):
            logging.error(f"Cannot find {f_type} in [{conf_opt}]")
            return ''
        time = self.timeinfo()
        cf_vars = config_vars
        cf_vars.update(time[0].config_timedic())
        f_name = self.config.get(conf_opt, f_type, vars=cf_vars)
        if check:
            if not os.path.isfile(f_name):
                logging.warning(f"file not found {f_name}")
                f_name = ''
        return f_name

    def is_integer_clock(self):
        if self.config.has_option('ambiguity_scheme', 'apply_irc'):
            is_irc = self.config.get('ambiguity_scheme', 'apply_irc')
            if is_irc.upper() == 'TRUE' or is_irc.upper() == 'YES':
                return True
        if not self.config.has_option('process_scheme', 'cen'):
            self.update_prodinfo()
            return True
        else:
            cen = self.config.get('process_scheme', 'cen')
            bia = self.config.get('process_scheme', 'bia')
            if cen in ['grg', 'grm']:
                return True
            elif cen == 'cod' and bia.lower() in ['cod', 'whu']:  # OSB + integer clock
                return True
            else:
                return False

    def is_integer_clock_osb(self):
        if not self.is_integer_clock():
            return False
        else:
            cen = self.config.get('process_scheme', 'cen')
            bia = self.config.get('process_scheme', 'bia')
            if cen == 'cod' and bia.lower() in ['cod', 'whu']:
                return True
            else:
                return False

    def get_filename(self, f_type, sattype='gns', check=False, conf_opt='process_files'):
        """ get the name of process files according to config file """
        file_all = ""
        if f_type in ['rinexo', 'ambflag', 'ambflag13', 'ambupd_in']:
            leo_rm = []
            for leo in self.leolist():
                leo_abbr = _LEO_INFO[leo]['abbr']
                if f_type == 'ambupd_in':
                    config_vars = {'leonam': leo, 'recnam': leo_abbr.upper()}
                else:
                    config_vars = {'leonam': leo, 'recnam': leo_abbr}
                if f_type == 'rinexo':
                    f_out = self._get_dailyfile(f_type, config_vars, check=check, conf_opt=conf_opt)
                else:
                    f_out = self._get_file(f_type, config_vars, check=check, conf_opt=conf_opt)
                if len(f_out.strip()) == 0:
                    leo_rm.append(leo)
                else:
                    file_all = file_all + " " + f_out
            sta_rm = []
            for sta in self.stalist():
                if f_type == 'ambupd_in':
                    config_vars = {'recnam': sta.upper()}
                else:
                    config_vars = {'recnam': sta}
                if f_type == 'rinexo':
                    f_out = self._get_dailyfile(f_type, config_vars, check=check, conf_opt=conf_opt)
                else:
                    f_out = self._get_file(f_type, config_vars, check=check, conf_opt=conf_opt)
                if len(f_out.strip()) == 0:
                    sta_rm.append(sta)
                else:
                    file_all = file_all + " " + f_out
            if check:
                self.remove_leo(leo_rm)
                self.remove_sta(sta_rm)
            return file_all.strip()
        elif f_type == 'kin':
            for leo in self.leolist():
                config_vars = {'recnam': leo}
                f_out = self._get_file(f_type, config_vars, check=check, conf_opt=conf_opt)
                file_all = file_all + " " + f_out
            return file_all.strip()
        elif f_type in ['attitude', 'pso']:  # LEO files
            for leo in self.leolist():
                leo_abbr = _LEO_INFO[leo]['abbr']
                config_vars = {'leonam': leo, 'recnam': leo_abbr}
                f_out = self._get_dailyfile(f_type, config_vars, check=check, conf_opt=conf_opt)
                file_all = file_all + " " + f_out
            return file_all.strip()
        elif f_type == 'sp3':
            f_out = ""
            if 'gns' in sattype:
                f_out = f_out + " " + self._get_dailyfile(f_type, check=check, conf_opt=conf_opt)
            if 'leo' in sattype:
                f_out = f_out + " " + self.get_filename('kin', check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type in ['rinexn', 'pso']:  # other daily files
            f_out = self._get_dailyfile(f_type, check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type == 'rinexc':
            f_out = self._get_dailyfile(f_type, check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type == 'rinexc_all':
            f_out = self._get_dailyfile(f_type, check=check, conf_opt=conf_opt)
            f_out = f_out + " " + self._get_file('recclk', check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type == 'biabern':
            bia = self.config.get('process_scheme', 'bia')
            if bia:
                f_bia = self._get_dailyfile('bia', check=check, conf_opt=conf_opt)
                return f_bia.strip()
            else:
                f_dcb_p1c1 = self._get_file('dcb_p1c1', check=check, conf_opt=conf_opt)
                f_dcb_p2c2 = self._get_file('dcb_p2c2', check=check, conf_opt=conf_opt)
                f_out = f_dcb_p1c1 + " " + f_dcb_p2c2
                return f_out.strip()
        elif f_type == 'upd':
            f_out = ""
            if not self.is_integer_clock_osb():
                f_out = self._get_file('upd_wl', check=check, conf_opt=conf_opt)
                f_out = f_out + " " + self._get_file('upd_ewl', check=check, conf_opt=conf_opt)
                if not self.is_integer_clock():
                    f_nlupd = self._get_file('upd_nl', check=check, conf_opt=conf_opt)
                    f_out = f_out + " " + f_nlupd
            return f_out.strip()
        elif f_type in ['orb', 'ics', 'orbdif']:
            f_out = ""
            if 'leo' in sattype:
                f_out = f_out + " " + self._get_file(f_type, {'sattype': 'leo'}, check=check, conf_opt=conf_opt)
            if 'gns' in sattype:
                f_out = f_out + " " + self._get_file(f_type, {'sattype': 'gns'}, check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type == 'solar':
            f_solar_flux = self._get_file('solar_flux', check=check, conf_opt=conf_opt)
            f_geomag_kp = self._get_file('geomag_kp', check=check, conf_opt=conf_opt)
            f_out = f"{f_solar_flux} {f_geomag_kp}"
            return f_out.strip()
        elif f_type == 'solar_MSISE':
            f_solar_flux = self._get_file('solar_flux_MSISE', check=check, conf_opt=conf_opt)
            f_geomag_ap = self._get_file('geomag_ap', check=check, conf_opt=conf_opt)
            f_out = f"{f_solar_flux} {f_geomag_ap}"
            return f_out.strip()
        elif f_type == 'sinex':
            return self._get_sinexfile(check=check, conf_opt=conf_opt)
        else:
            f_out = self._get_file(f_type, check=check, conf_opt=conf_opt)
            return f_out.strip()

    def basic_check(self, opts=None, files=None):
        """ check the necessary settings and existence of files """
        # check process schemes
        if files is None:
            files = []
        if opts is None:
            opts = []
        if not self.config.has_section('process_scheme'):
            _raise_error("No [process_scheme] in config file")
        opts_base = ['time_beg', 'time_end', 'intv', 'frequency']
        opts = opts_base + opts
        for opt in opts:
            if not self.config.has_option('process_scheme', opt):
                _raise_error(f"No [process_scheme][{opt}] in config file")
        # check necessary files
        if files:
            for file in files:
                f_name = self.get_filename(file, check=True)
                if len(f_name) == 0:
                    _raise_error(f"{file} file missing")
                f_check = ""
                if file == 'rinexo' and len(self.leolist()) > 0:
                    f_atx = self.get_filename('atx')
                    for f_sub in f_name.split():
                        if gf.check_rnxo_ant(f_sub, f_atx):
                            f_check = f_check + " " + f_sub
                elif file == 'attitude':
                    for f_sub in f_name.split():
                        if gf.check_att_file(f_sub):
                            f_check = f_check + " " + f_sub
                else:
                    f_check = f_name
                if f_check.isspace():
                    _raise_error(f"No usable {file}")
        return True

    def copy_sys_data(self):
        """ copy source_files to process_files """
        if self.config.has_section('source_files') and self.config.has_section('process_files'):
            for f_type in self.config['source_files']:
                f_source = self.get_filename(f_type, check=False, conf_opt='source_files').split()
                f_dest = self.get_filename(f_type, check=False, conf_opt='process_files').split()
                if len(f_source) == len(f_dest):
                    for i in range(len(f_source)):
                        if f_source[i].strip() == f_dest[i].strip():
                            logging.warning(f"The source file is the same as target file {f_source[i]}")
                            continue
                        if os.path.isfile(f_source[i]):
                            shutil.copy(f_source[i], f_dest[i])
                            logging.info(os.path.basename(f_dest[i]) + " is copied to work directory")
                        else:
                            logging.warning(f"source file not found {f_source[i]}")
                else:
                    logging.warning(f"Number of source files ({f_type}, {len(f_source)}) is not equal to target "
                                    f"files ({len(f_dest)})")

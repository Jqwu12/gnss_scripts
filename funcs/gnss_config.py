import os
import configparser
import shutil
import logging
import platform
import copy
from funcs import gnss_files as gf, gnss_tools as gt
from funcs.gnss_time import GnssTime
from funcs.constants import get_gns_name, get_gns_sat, get_gns_info, _GNS_NAME, _LEO_INFO


def _raise_error(msg):
    logging.critical(msg)
    raise SystemExit(msg)


class GnssConfig:

    def __init__(self, f_config, conf=None):
        if conf:
            self.config = conf
        else:
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
        conf = copy.deepcopy(self.config)  # need python3.8 or higher!
        return GnssConfig("", conf)

    def update_timeinfo(self, time_beg=None, time_end=None, intv=None):
        """ update the time information in config file """
        if time_beg:
            self.config.set('process_scheme', 'time_beg', time_beg.datetime())
        if time_end:
            self.config.set('process_scheme', 'time_end', time_end.datetime())
        if intv:
            self.config.set('process_scheme', 'intv', f"{intv:d}")

    def update_gnssinfo(self, sys=None, freq=None, obs_comb=None, est=None, sat_rm=None):
        """ update the gnss settings in config file """
        if sys:
            self.config.set('process_scheme', 'sys', sys)
        if freq:
            self.config.set('process_scheme', 'frequency', f"{freq:d}")
        if est:
            self.config.set('process_scheme', 'lsq_mode', est)
        if obs_comb:
            if obs_comb == 'UC':
                self.config.set('process_scheme', 'obs_comb', "UC")
                self.config.set('process_scheme', 'obs_combination', "RAW_ALL")
                self.config.set('process_scheme', 'ion_model', "SION")
            else:
                self.config.set('process_scheme', 'obs_comb', "IF")
                self.config.set('process_scheme', 'obs_combination', "IONO_FREE")
                self.config.set('process_scheme', 'ion_model', "NONE")
        if sat_rm is not None:
            if sat_rm:
                self.config.set('process_scheme', 'sat_rm', gt.list2str(sat_rm))
            else:
                self.config.set('process_scheme', 'sat_rm', '')

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
            for sta in sta_list:
                info = info + ' ' + sta
        else:
            info = sta_list
        self.config.set('process_scheme', 'sta_list', info)

    def update_pathinfo(self, all_path=None, check=True):
        """ update the path information in config according to different OS """
        if all_path is None:
            all_path = {}
        required_path = ['grt_bin', 'base_dir', 'sys_data', 'gns_data']
        option_path = ['upd_data']
        if all_path:
            logging.info("set path information from outside...")
        else:
            logging.info("find path information in config...")
        for name in required_path:
            if name in all_path.keys():
                path = all_path[name]
                if os.path.isdir(path):
                    self.config.set('common', name, os.path.abspath(path))
                else:
                    logging.error(f"set {name} failed! {path} not exists, use old")
            if not self.config.has_option('common', name):
                _raise_error(f"no {name} in config [common]!")
            else:
                path = self.config.get('common', name)
                if check:
                    if os.path.isdir(path):
                        logging.info(f"{name} = {path}")
                    else:
                        _raise_error(f"PATH NOT EXIST ({name}): {path}")

        for name in option_path:
            if name in all_path.keys():
                path = all_path[name]
                self.config.set('common', name, os.path.abspath(path))
            if check:
                if not self.config.has_option('common', name):
                    logging.error(f"no {name} in config [common]!")
                else:
                    path = self.config.get('common', name)
                    if not os.path.isdir(path):
                        os.makedirs(path)

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
                    self.config.set('process_scheme', key, f"{val}")
            else:
                self.config.set('process_scheme', key, f"{val}")

    def update_ambiguity(self, append=False, **kwargs):
        """ Update any ambiguity item in config """
        for key, val in kwargs.items():
            if not append:
                if self.config.has_option('ambiguity_scheme', key):
                    self.config.set('ambiguity_scheme', key, f"{val}")
            else:
                self.config.set('ambiguity_scheme', key, f"{val}")

    def change_data_path(self, file, target):
        """
        inputs: file            original file defined in config
                target          target directory defined in config
        """
        support_files = ['rinexo', 'rinexn', 'rinexc', 'sp3', 'bia']  # can be added later
        if file not in support_files:
            logging.warning(f"change_data_path failed! file type not supported {file}")
            logging.warning(f"supported files {gt.list2str(support_files)}")
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
            t_beg = GnssTime()
            t_end = GnssTime()
            t_beg.from_datetime(beg)
            t_end.from_datetime(end)
            return t_beg, t_end
        else:
            _raise_error("Cannot find time_beg/time_end in [process_scheme]")

    def intv(self):
        """ interval """
        if self.config.has_option('process_scheme', 'intv'):
            val = self.config.getint('process_scheme', 'intv')
            return val
        else:
            _raise_error("Cannot find intv in [process_scheme]")

    def band(self, gsys):
        """ Get the GNSS Band """
        gsys = get_gns_name(gsys)
        if not gsys:
            return
        word = 'band_X'
        if gsys == "GPS":
            word = 'band_G'
        elif gsys == "BDS":
            word = 'band_C'
        elif gsys == "GAL":
            word = 'band_E'
        elif gsys == "GLO":
            word = 'band_R'
        elif gsys == "QZS":
            word = 'band_J'
        if self.config.has_option('process_scheme', word):
            band = self.config.get('process_scheme', word)
            bands = []
            for x in band:
                if x.isdigit():
                    bands.append(int(x))
            return bands

    def sat_rm(self):
        if self.config.has_option('process_scheme', 'sat_rm'):
            sats = self.config.get('process_scheme', 'sat_rm')
            return sats.split()

    def apply_carrier_range(self):
        if self.config.has_option('process_scheme', 'apply_carrier_range'):
            return self.config.getboolean('process_scheme', 'apply_carrier_range')
        else:
            return False

    def xml_process(self):
        """ return a dict for xml <process> """
        proc_dict = {
            "grad_mf": "BAR_SEVER", "gradient": "false", "minimum_elev": "9", "minimum_elev_leo": "1",
            "obs_weight": "PARTELE", "phase": "true", "slip_model": "turboedit"
        }
        opt_list = ['obs_combination', 'ion_model', 'frequency', 'crd_constr', 'sig_init_crd', 'lsq_mode',
                    'sysbias_model', 'ztd_model', 'apply_carrier_range']
        proc_dict['apply_carrier_range'] = "false"
        for opt in opt_list:
            if self.config.has_option('process_scheme', opt):
                proc_dict[opt] = self.config.get('process_scheme', opt)
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
        opt_list = ['dd_mode', 'is_ppprtk', 'fix_mode', 'ratio', 'part_fix', 'carrier_range', 'add_leo',
                    'all_baselines', 'min_common_time', 'baseline_length_limit', 'widelane_interval']
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
                amb_dict['extra_widelane_decision'] = self.config.get('ambiguity_scheme',
                                                                      'extra_widelane_decision').split()
        if self.config.has_option('ambiguity_scheme', 'widelane_decision'):
            if len(self.config.get('ambiguity_scheme', 'widelane_decision').split()) == 3:
                amb_dict['widelane_decision'] = self.config.get('ambiguity_scheme', 'widelane_decision').split()
        if self.config.has_option('ambiguity_scheme', 'narrowlane_decision'):
            if len(self.config.get('ambiguity_scheme', 'narrowlane_decision').split()) == 3:
                amb_dict['narrowlane_decision'] = self.config.get('ambiguity_scheme', 'narrowlane_decision').split()
        return amb_dict

    def beg_time(self):
        time = GnssTime()
        time.from_datetime(self.config['process_scheme']['time_beg'])
        return time

    def end_time(self):
        time = GnssTime()
        time.from_datetime(self.config['process_scheme']['time_end'])
        return time

    def seslen(self):
        return self.end_time().diff(self.beg_time())

    def work_dir(self):
        ss = self.get_file("work_dir", check=False)
        return ss

    def igs_ac(self):
        if self.config.has_option('process_scheme', 'cen'):
            return self.config.get('process_scheme', 'cen')

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

    def gnsfreq(self, gsys):
        """ freq of one system """
        gns_info = get_gns_info(gsys, self.sat_rm(), self.band(gsys))
        nfreq = self.config.get('process_scheme', 'frequency')
        mfreq = min(int(nfreq), len(gns_info['band']))
        return mfreq

    def freq(self):
        return int(self.config['process_scheme']['frequency'])

    def update_band(self, gsys, bands):
        gsys = get_gns_name(gsys)
        if gsys == 'GPS':
            self.config['process_scheme']['band_G'] = str(bands)
        elif gsys == 'BDS':
            self.config['process_scheme']['band_C'] = str(bands)
        elif gsys == 'GAL':
            self.config['process_scheme']['band_E'] = str(bands)
        elif gsys == 'GLO':
            self.config['process_scheme']['band_R'] = str(bands)
        elif gsys == 'QZS':
            self.config['process_scheme']['band_J'] = str(bands)

    def all_gnssat(self):
        """ Get all GNSS sats """
        sats = []
        for sys in self.gnssys().split():
            sats.extend(get_gns_sat(sys, self.sat_rm()))
        return sats

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
            out = []
            for sta in info.split():
                if len(sta) == 4:
                    out.append(sta.lower())
            if out:
                out = list(set(out))
                out.sort()
            return out
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
            logging.warning(f"STATIONS {sta_rm_str} are removed")

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
        # t_use = t_beg.time_increase(-86400*30) # use the current snx, change for preedit
        t_use = t_beg
        cf_vars = t_use.config_timedic()
        f_name = self.config.get(conf_opt, 'sinex', vars=cf_vars)
        if check:
            if not os.path.isfile(f_name):
                f_name = ''
        return f_name

    def get_dailyfile(self, f_type, config_vars=None, check=False, conf_opt='process_files'):
        if config_vars is None:
            config_vars = {}
        if not self.config.has_option(conf_opt, f_type):
            logging.error(f"Cannot find {f_type} in [{conf_opt}]")
            return ''
        t_beg, t_end = self.timeinfo()
        if f_type == 'sp3':
            t_beg -= 5400
            t_end += 5400
        else:
            t_end -= 1
        crt_time = t_beg
        end_time = GnssTime()
        end_time.from_mjd(t_end.mjd, 86399.0)
        f_out = ""
        while crt_time < end_time:
            cf_vars = config_vars
            cf_vars.update(crt_time.config_timedic())
            f_name = self.config.get(conf_opt, f_type, vars=cf_vars)
            if check:
                if not os.path.isfile(f_name):
                    logging.warning(f"file not found {f_name}")
                    f_name = ''
            if len(f_name) != 0:
                f_out = f_out + " " + f_name
            crt_time += 86400
        return f_out

    def get_file(self, f_type, config_vars=None, check=False, conf_opt='process_files'):
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

    def get_filename_site(self, f_type, site, check=False, conf_opt='process_files'):
        if f_type == 'ambupd_in' or f_type == 'recover_all':
            config_vars = {'recnam': site.upper()}
        else:
            config_vars = {'recnam': site}
        if f_type == 'rinexo':
            f_out = self.get_dailyfile(f_type, config_vars, check=check, conf_opt=conf_opt)
        elif f_type == 'recover_all':
            f_out = self.get_file('recover_in', config_vars, check=check, conf_opt=conf_opt)
        else:
            f_out = self.get_file(f_type, config_vars, check=check, conf_opt=conf_opt)

        return f_out

    def get_filename(self, f_type, sattype='gns', check=False, conf_opt='process_files'):
        """ get the name of process files according to config file """
        file_all = ""
        if f_type in ['rinexo', 'ambflag', 'ambflag13', 'ambflag14', 'ambflag15', 'ambupd_in', 'recover_all']:
            # LEO receivers
            leo_rm = []
            for leo in self.leolist():
                leo_abbr = _LEO_INFO[leo]['abbr']
                if f_type == 'ambupd_in' or f_type == 'recover_all':
                    config_vars = {'leonam': leo, 'recnam': leo_abbr.upper()}
                else:
                    config_vars = {'leonam': leo, 'recnam': leo_abbr}
                if f_type == 'rinexo':
                    f_out = self.get_dailyfile(f_type, config_vars, check=check, conf_opt=conf_opt)
                elif f_type == 'recover_all':
                    f_out = self.get_file('recover_in', config_vars, check=check, conf_opt=conf_opt)
                else:
                    f_out = self.get_file(f_type, config_vars, check=check, conf_opt=conf_opt)
                # check ambflag
                if f_out.strip() != '' and 'ambflag' in f_type and check:
                    nobs = self.seslen() / 30 * 2
                    if not gf.check_ambflag(f_out.strip(), nobs):
                        f_out = ''
                if len(f_out.strip()) == 0 and f_type not in ['ambflag13', 'ambflag14', 'ambflag15']:
                    leo_rm.append(leo)
                else:
                    file_all = file_all + " " + f_out
            # Ground receivers
            sta_rm = []
            for sta in self.stalist():
                if f_type == 'ambupd_in' or f_type == 'recover_all':
                    config_vars = {'recnam': sta.upper()}
                else:
                    config_vars = {'recnam': sta}
                if f_type == 'rinexo':
                    f_out = self.get_dailyfile(f_type, config_vars, check=check, conf_opt=conf_opt)
                elif f_type == 'recover_all':
                    f_out = self.get_dailyfile('recover_in', config_vars, check=check, conf_opt=conf_opt)
                else:
                    f_out = self.get_file(f_type, config_vars, check=check, conf_opt=conf_opt)
                # check ambflag
                if f_out.strip() != '' and 'ambflag' in f_type and check:
                    nobs = self.seslen() / 30 * 2
                    if not gf.check_ambflag(f_out.strip(), nobs):
                        f_out = ''
                if len(f_out.strip()) == 0 and f_type not in ['ambflag13', 'ambflag14', 'ambflag15']:
                    sta_rm.append(sta)
                else:
                    file_all = file_all + " " + f_out
            if check:
                self.remove_leo(leo_rm)
                self.remove_sta(sta_rm)
                if 'ambflag' in f_type:
                    self.remove_ambflag_file(sta_rm)
            return file_all.strip()
        elif f_type == 'kin':
            for leo in self.leolist():
                config_vars = {'recnam': leo}
                f_out = self.get_file(f_type, config_vars, check=check, conf_opt=conf_opt)
                file_all = file_all + " " + f_out
            return file_all.strip()
        elif f_type in ['attitude', 'pso']:  # LEO files
            for leo in self.leolist():
                leo_abbr = _LEO_INFO[leo]['abbr']
                config_vars = {'leonam': leo, 'recnam': leo_abbr}
                f_out = self.get_dailyfile(f_type, config_vars, check=check, conf_opt=conf_opt)
                file_all = file_all + " " + f_out
            return file_all.strip()
        elif f_type == 'sp3':
            f_out = ""
            if 'gns' in sattype:
                f_out = f_out + " " + self.get_dailyfile(f_type, check=check, conf_opt=conf_opt)
            if 'leo' in sattype:
                f_out = f_out + " " + self.get_filename('kin', check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type in ['rinexn', 'pso']:  # other daily files
            f_out = self.get_dailyfile(f_type, check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type == 'rinexc':
            f_out = self.get_dailyfile(f_type, check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type == 'rinexc_all':
            f_out = self.get_dailyfile('rinexc', check=check, conf_opt=conf_opt)
            f_out = f_out + " " + self.get_file('recclk', check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type == 'biabern':
            bia = self.config.get('process_scheme', 'bia')
            if bia:
                f_bia = self.get_dailyfile('bia', check=check, conf_opt=conf_opt)
                return f_bia.strip()
            else:
                f_dcb_p1c1 = self.get_file('dcb_p1c1', check=check, conf_opt=conf_opt)
                f_dcb_p2c2 = self.get_file('dcb_p2c2', check=check, conf_opt=conf_opt)
                f_out = f_dcb_p1c1 + " " + f_dcb_p2c2
                return f_out.strip()
        elif f_type == 'upd':
            f_out = ""
            if not self.is_integer_clock_osb():
                f_out = self.get_file('upd_wl', check=check, conf_opt=conf_opt)
                if self.freq() > 2:
                    f_out = f_out + " " + self.get_file('upd_ewl', check=check, conf_opt=conf_opt)
                if self.freq() > 3:
                    f_out = f_out + " " + self.get_file('upd_ewl24', check=check, conf_opt=conf_opt)
                if self.freq() > 4:
                    f_out = f_out + " " + self.get_file('upd_ewl25', check=check, conf_opt=conf_opt)
                if not self.is_integer_clock():
                    f_nlupd = self.get_file('upd_nl', check=check, conf_opt=conf_opt)
                    f_out = f_out + " " + f_nlupd
            return f_out.strip()
        elif f_type in ['orb', 'ics', 'orbdif']:
            f_out = ""
            if 'leo' in sattype:
                f_out = f_out + " " + self.get_file(f_type, {'sattype': 'leo'}, check=check, conf_opt=conf_opt)
            if 'gns' in sattype:
                f_out = f_out + " " + self.get_file(f_type, {'sattype': 'gns'}, check=check, conf_opt=conf_opt)
            return f_out.strip()
        elif f_type == 'solar':
            f_solar_flux = self.get_file('solar_flux', check=check, conf_opt=conf_opt)
            f_geomag_kp = self.get_file('geomag_kp', check=check, conf_opt=conf_opt)
            f_out = f"{f_solar_flux} {f_geomag_kp}"
            return f_out.strip()
        elif f_type == 'solar_MSISE':
            f_solar_flux = self.get_file('solar_flux_MSISE', check=check, conf_opt=conf_opt)
            f_geomag_ap = self.get_file('geomag_ap', check=check, conf_opt=conf_opt)
            f_out = f"{f_solar_flux} {f_geomag_ap}"
            return f_out.strip()
        elif f_type == 'sinex':
            return self._get_sinexfile(check=check, conf_opt=conf_opt)
        else:
            f_out = self.get_file(f_type, check=check, conf_opt=conf_opt)
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
                    logging.error(f"{file} file missing")
                    return False
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
                f_check = f_check.strip()
                if not f_check:
                    logging.error(f"no usable {file}")
                    return False
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
                            logging.info(f"source file is copied to work directory: {os.path.basename(f_dest[i])}")
                        else:
                            logging.warning(f"source file not found {f_source[i]}")
                else:
                    logging.warning(f"Number of source files ({f_type}, {len(f_source)}) is not equal to target "
                                    f"files ({len(f_dest)})")

    def remove_ambflag_file(self, sites):
        if not sites:
            return
        for site in sites:
            f_log12 = self.get_filename_site('ambflag', site, check=False)
            if os.path.isfile(f_log12):
                os.remove(f_log12)
            if self.freq() > 2:
                f_log13 = self.get_filename_site('ambflag13', site, check=False)
                if os.path.isfile(f_log13):
                    os.remove(f_log13)
            if self.freq() > 3:
                f_log14 = self.get_filename_site('ambflag14', site, check=False)
                if os.path.isfile(f_log14):
                    os.remove(f_log14)
            if self.freq() > 4:
                f_log15 = self.get_filename_site('ambflag15', site, check=False)
                if os.path.isfile(f_log15):
                    os.remove(f_log15)

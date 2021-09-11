import os
import math
import logging
import shutil
import pandas as pd
import time
import xml.etree.ElementTree as ET
from functools import wraps
from contextlib import contextmanager
from . import gnss_files as gf


def timethis(label):
    if label is None:
        label = 'Normal end'

    def decorate(func):
        """ Decorator that reports the execution time. """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            logging.info(f"#### {label:30s}, duration {end - start:15.5f} sec")
            return result

        return wrapper

    return decorate


@contextmanager
def timeblock(label):
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        logging.info(f"#### {label:30s}, duration {end - start:15.5f} sec")


def split_receivers(config, num):
    if not config.all_sites:
        logging.error("No receiver in config")
        return []
    num = min(num, len(config.all_sites))
    nleo = len(config.leo_list)
    nsta = len(config.site_list)
    leo_num = round(num * nleo / (nleo + nsta))
    sta_num = num - leo_num
    leo_subs = _split_list(config.leo_list, leo_num)
    sta_subs = _split_list(config.site_list, sta_num)
    return sta_subs, leo_subs


def _split_list(list_in, num):
    """
    Divide a list to several parts, each part has similiar length
    e.g. [1,2,3,4,5] => [[1,2],[3,4],[5]]
    """
    if num >= len(list_in):
        return [[l] for l in list_in]
    step0 = int(len(list_in) / num)
    n_left = len(list_in) % num
    list_out = []
    for i in range(n_left):
        ibeg = i * (step0 + 1)
        iend = (i + 1) * (step0 + 1)
        sub_list = list_in[ibeg: iend]
        list_out.append(sub_list)
    for i in range(num - n_left):
        ibeg = n_left * (step0 + 1) + i * step0
        iend = n_left * (step0 + 1) + (i + 1) * step0
        sub_list = list_in[ibeg: iend]
        list_out.append(sub_list)
    return list_out


def _auto_wrap(line, intent, linelen=60):
    if isinstance(line, list):
        parts = line
    else:
        parts = line.split()
    info = ''
    newline = 1
    for part in parts:
        info = info + ' ' + part
        if len(info) >= newline * linelen + (1 + len(intent)) * (newline - 1):
            if newline == 1:
                linelen = len(info)
            info = info + '\n' + intent
            newline += 1
    info = info.rstrip()
    return info


def pretty_xml(element, indent='\t', newline='\n', level=0):
    """
    element:  xml node
    indent:   '\t'
    newline:  '\n'
    """
    if element:
        if (element.text is None) or element.text.isspace():
            element.text = newline + indent * (level + 1)
        else:
            element.text = newline + indent * (level + 1) + element.text.strip() + newline + indent * (level + 1)
    else:
        if element.text is not None:
            if len(element.text) > 60:
                element.text = newline + indent * (level + 1) + _auto_wrap(element.text, indent * (
                        level + 1)) + newline + indent * level
                element.tail = newline + indent * level
            else:
                element.text = ' ' + element.text + ' '
    temp = list(element)
    for subelement in temp:
        if temp.index(subelement) < (len(temp) - 1):
            subelement.tail = newline + indent * (level + 1)
        else:
            subelement.tail = newline + indent * level
        pretty_xml(subelement, indent, newline, level=level + 1)


def check_pod_sigma(config, maxsig=8):
    f_res = config.get_xml_file('recover_in')[0]
    if not os.path.isfile(f_res):
        logging.warning(f"file not found {f_res}")
        return False
    sig = -1
    with open(f_res) as f:
        for line in f:
            if line[0:2] != '##':
                break
            if line[0:7] == '##Sigma':
                sig = float(line[10:23])
    if sig < 0:
        logging.warning(f"sigma0 not find in {f_res}")
        return False
    elif sig > maxsig:
        logging.warning(f"sigma too large {sig}")
        return False
    else:
        return True


def check_pod_residuals(config, max_res_L=10, max_res_P=100, max_count=50, max_freq=0.3):
    """
    Purpose : find the possible BAD station or satellite by post-fit residuals
              only for network LSQ
    Inputs : config         config
             max_res_L      phase residual threshold
             max_res_P      code residual threshold
             max_freq       threshold of outlier numbers
             max_per        threshold of outlier percentage
    """
    f_res = config.get_xml_file('recover_in')[0]
    if not os.path.isfile(f_res):
        logging.warning(f"file not found {f_res}")
        return [], []
    data = gf.read_res_file(f_res)
    type_P = config.code_type()
    type_L = config.phase_type()
    idx_P = (data.ot == type_P[0])
    for i in range(1, len(type_P)):
        idx_P = idx_P | (data.ot == type_P[i])
    idx_L = (data.ot == type_L[0])
    for i in range(1, len(type_L)):
        idx_L = idx_L | (data.ot == type_L[i])
    # find satellite with too less observations
    sat_rm = []
    sats = list(set(data.sat))
    sats.sort()
    ntot = len(data)
    nmin = ntot / len(sats) / 4
    for sat in sats:
        num = len(data[data.sat == sat])
        if num < nmin:
            logging.warning(f"satellite {sat} observation too less: {num}")
            sat_rm.append(sat)
    # find code and phase possible outliers
    data_out_P = data[idx_P & ((data.res > max_res_P) | (data.res < -1 * max_res_P))]
    data_out_L = data[idx_L & ((data.res > max_res_L) | (data.res < -1 * max_res_L))]
    site_P = pd.DataFrame({'counts': data_out_P['site'].value_counts(),
                           'freq': data_out_P['site'].value_counts(normalize=True)})
    site_L = pd.DataFrame({'counts': data_out_L['site'].value_counts(),
                           'freq': data_out_L['site'].value_counts(normalize=True)})
    sat_P = pd.DataFrame({'counts': data_out_P['sat'].value_counts(),
                          'freq': data_out_P['sat'].value_counts(normalize=True)})
    sat_L = pd.DataFrame({'counts': data_out_L['sat'].value_counts(),
                          'freq': data_out_L['sat'].value_counts(normalize=True)})
    # remove sites
    site_rm_P = list(site_P[(site_P.counts > max_count) & (site_P.freq > max_freq)].index)
    if site_rm_P:
        logging.warning(f"too many bad code residuals for station: {' '.join(site_rm_P)}")
    site_rm_L = list(site_L[(site_L.counts > max_count) & (site_L.freq > max_freq)].index)
    if site_rm_L:
        logging.warning(f"too many bad phase residuals for station: {' '.join(site_rm_L)}")
    site_rm = site_rm_P + site_rm_L
    site_rm = list(set(site_rm))
    # remove sats
    sat_rm_P = list(sat_P[(sat_P.counts > max_count) & (sat_P.freq > max_freq)].index)
    if sat_rm_P:
        logging.warning(f"too many bad code residuals for satellite: {' '.join(sat_rm_P)}")
    sat_rm_L = list(sat_L[(sat_L.counts > max_count) & (sat_L.freq > max_freq)].index)
    if sat_rm_L:
        logging.warning(f"too many bad phase residuals for satellite: {' '.join(sat_rm_L)}")
    sat_rm += sat_rm_P + sat_rm_L
    sat_rm = list(set(sat_rm))
    return site_rm, sat_rm


def good_tb_site(file):
    site_good = []
    try:
        with open(file) as f:
            lines = f.readlines()
    except FileNotFoundError:
        logging.warning(f"Cannot open turboedit log file {file}")
        return []
    for line in lines:
        if line.find("Site and Evaluation") > 0:
            if line[65:69] == "GOOD":
                site = line[58:62].lower()
                if site not in site_good:
                    site_good.append(site)
    return site_good


def check_turboedit_log(config, nthread, label="turboedit", path="xml"):
    # Todo: LEO satellites need to be considered
    site_good = []
    if nthread == 1:
        sites = good_tb_site(os.path.join(path, f"{label}.log"))
        site_good.extend(sites)
    else:
        for i in range(1, nthread + 1):
            sites = good_tb_site(os.path.join(path, f"{label}{i:0>2d}.log"))
            site_good.extend(sites)
    site_rm_final = list(set(config.all_sites).difference(set(site_good)))
    if not site_rm_final:
        return
    msg = f"BAD Turboedit results: {' '.join(site_rm_final)}"
    logging.warning(msg)
    config.remove_ambflag_file(site_rm_final)
    config.remove_leo(site_rm_final)
    config.remove_site(site_rm_final)


def check_brd_orbfit(f_name):
    val = {}
    num = {}
    try:
        with open(f_name) as f:
            for line in f:
                if line[0:4] != "APRI":
                    continue
                if line[0:3] == "ACR" or line[0:3] == "RMS":
                    break
                prn = line[6:9]
                rms_a = float(line[39:54])
                rms_c = float(line[54:69])
                rms_r = float(line[69:84])
                rms_3d = math.sqrt(rms_a * rms_a + rms_c * rms_c + rms_r * rms_r)
                if prn not in val.keys():
                    val[prn] = rms_3d * rms_3d
                    num[prn] = 1
                else:
                    val[prn] = val[prn] + rms_3d * rms_3d
                    num[prn] += 1
    except FileNotFoundError:
        logging.warning(f"orbfit file not found {f_name}")
        return

    sat_rm = []
    for prn in val.keys():
        # if num[prn] < 287:
        #     sat_rm.append(prn)
        #     logging.warning(f"Incomplete satellite BRD: {prn}")
        #     continue
        result = math.sqrt(val[prn] / num[prn])
        if result > 100:
            sat_rm.append(prn)
            logging.warning(f"Bad satellite BRD: {prn}")
    if sat_rm:
        logging.warning(f"SATELLITES {' '.join(sat_rm)} are removed")
    return sat_rm


def check_res_sigma(config, max_sig=8):
    site_rm = []
    for rec in config.all_receivers:
        file = config.file_name('recover_in', rec, check=True, quiet=True)
        if not file:
            logging.warning(f"cannot find resfile for {rec['rec']}")
            site_rm.append(rec['rec'])
            continue
        sig = -1
        with open(file) as f:
            for line in f:
                if line[0:2] != '##':
                    break
                if line[0:7] == '##Sigma':
                    sig = float(line[10:23])
                    if sig > max_sig:
                        logging.warning(f"sigma0 too large in {file}: {sig:8.3f}")
                        site_rm.append(rec['rec'])
                    break
        if sig < 0:
            logging.warning(f"sigma0 not find in {file}")
            site_rm.append(rec['rec'])

    if site_rm:
        config.remove_site(site_rm)
        config.remove_ambflag_file(site_rm)


def backup_dir(dir1, dir2):
    if not os.path.isdir(dir1):
        logging.error(f"directory not exists {dir1}")
        return
    if not os.path.isdir(dir2):
        os.makedirs(dir2)

    f2 = [file for file in os.listdir(dir2)]
    for file in os.listdir(dir1):
        if file not in f2:
            f_org = os.path.join(dir1, file)
            f_est = os.path.join(dir2, file)
            shutil.copy(f_org, f_est)


def copy_dir(dir1, dir2):
    if not os.path.isdir(dir1):
        logging.error(f"directory not exists {dir1}")
        return
    if not os.path.isdir(dir2):
        os.makedirs(dir2)

    for file in os.listdir(dir1):
        f_org = os.path.join(dir1, file)
        f_est = os.path.join(dir2, file)
        shutil.copy(f_org, f_est)


def backup_files(config, files, sattype='gns', suffix="bak"):
    for file in files:
        file_olds = config.get_xml_file(file.lower(), check=True, sattype=sattype)
        for f_name in file_olds:
            f_new = f"{f_name}.{suffix}"
            try:
                shutil.copy(f_name, f_new)
            except IOError:
                logging.warning(f"unable to backup file {file}")


def recover_files(config, files, sattype='gns', suffix="bak"):
    for file in files:
        file_olds = config.get_xml_file(file.lower(), check=False, sattype=sattype)
        for f_name in file_olds:
            f_new = f"{f_name}.{suffix}"
            try:
                shutil.copy(f_new, f_name)
            except IOError:
                logging.warning(f"unable to recover file {file}.{suffix}")


def get_rnxc_satlist(f_name):
    sats = []
    try:
        with open(f_name) as f:
            for line in f:
                if line.find("END OF HEADER") > 0:
                    break
                pos = line.find('PRN LIST') 
                if pos > 0:
                    info = line[0: pos]
                    sats.extend(info.split())
            return sats
    except FileNotFoundError:
        logging.error(f"file not found {f_name}")
        return sats


def copy_ambflag_from(ambflagdir):
    if not os.path.isdir(ambflagdir):
        logging.warning(f"cannot find source ambflag dir {ambflagdir}")
        return False
    logging.info(f"ambflag files are copied from {ambflagdir}")
    if os.path.isdir('log_tb'):
        shutil.rmtree('log_tb')
    if not os.path.isdir('log_tb'):
        os.makedirs('log_tb')
    for file in os.listdir(ambflagdir):
        n = len(file)
        if n < 7:
            continue
        if file[n - 5: n] == "o.log" or file[n - 7: n] in ["o.log13", "o.log14", "o.log15"]:
            f0 = os.path.join(ambflagdir, file)
            f1 = os.path.join('log_tb', file)
            shutil.copy(f0, f1)


def copy_result_files(config, files, scheme, sattype='gns'):
    """
    Purpose: Copy result files
    e.g. cp orbdif_2020001 orbdif_2020001_flt
    """
    for file in files:
        file_olds = config.get_xml_file(file, check=True, sattype=sattype)
        for f_name in file_olds:
            f_new = f"{f_name}_{scheme}"
            try:
                shutil.copy(f_name, f_new)
            except IOError:
                logging.warning(f"unable to copy file {file}")


def copy_result_files_to_path(config, files, path, schemes=None, sattype='gns'):
    """
    Purpose: Copy result files to another path
    e,g, cp upd_nl_2019100_G ${upd_dir}
    """
    if not os.path.isdir(path):
        # logging.warning(f"Input path {path} not exists, creating...")
        os.makedirs(path)
    for file in files:
        file_olds = config.get_xml_file(file.lower(), check=False, sattype=sattype)
        for f_name in file_olds:
            if not schemes:
                if os.path.isfile(f_name):
                    try:
                        shutil.copy(f_name, path)
                    except IOError as dummy_e:
                        logging.warning(f"unable to copy file {f_name}")
                else:
                    logging.warning(f"file not found {f_name}")
            else:
                for sch in schemes:
                    f_new = f"{f_name}_{sch}"
                    if os.path.isfile(f_new):
                        try:
                            shutil.copy(f_new, path)
                        except IOError as dummy_e:
                            logging.warning(f"unable to copy file {f_new}")
                    else:
                        logging.warning(f"file not found {f_new}")


def get_grg_wsb(config):
    """
    purpose: grep WL UPD from CNES/CLS integer clock products
    """
    f_wsb = config.get_xml_file('upd_wl')[0]
    f_clks = config.get_xml_file('rinexc', check=True)
    f_clks_select = []
    for f_clk in f_clks:
        clk_file = os.path.basename(f_clk)
        if not clk_file[0:3] in ['grg', 'grm', 'gr2']:
            continue
        f_clks_select.append(f_clk)
    if f_clks_select:
        idx = int(len(f_clks_select) / 2)  # choose the WSB of the middle day
        f_clk = f_clks_select[idx]
        wlupd = []
        with open(f_clk) as file_object:
            for line in file_object:
                if line.find('WL') == 0:
                    info = line.split()
                    sat = info[1]
                    upd = -1.0 * float(info[9])
                    wlupd.append({'sat': sat, 'wsb': upd})
                if line.find('END OF HEADER') > 0:
                    break
    else:
        logging.error("integer clock product not found")
        return
    with open(f_wsb, 'w') as file_object:
        line = "% UPD generated from CNES/CLS clock using upd_wl\n"
        file_object.write(line)
        for rec in wlupd:
            line = f" {rec['sat']:>3s}{rec['wsb']:>18.3f}{0.01:>10.3f}{50:>5d}\n"
            file_object.write(line)


def merge_upd_all(config, gsys, files):
    """
    merge ewl, wl and nl UPD files
    inputs : config    config
             gsys      "GREC"
    """
    for f in files:
        config.gsys = gsys
        f_out = config.get_xml_file(f)[0]
        f_ins = []
        for s in gsys:
            config.gsys = s
            f_in = config.get_xml_file(f, check=True)
            if f_in:
                f_ins.append(f_in[0])
        if f == "upd_ewl25":
            merge_upd(f_ins, f_out, "EWL25")
            logging.info(f"merge upd_ewl25 complete, file is {f_out}")
        elif f == "upd_ewl24":
            merge_upd(f_ins, f_out, "EWL24")
            logging.info(f"merge upd_ewl24 complete, file is {f_out}")
        elif f == "upd_ewl":
            merge_upd(f_ins, f_out, "EWL")
            logging.info(f"merge upd_ewl complete, file is {f_out}")
        elif f == "upd_wl":
            merge_upd(f_ins, f_out, "WL")
            logging.info(f"merge upd_wl  complete, file is {f_out}")
        elif f == "upd_nl":
            merge_upd(f_ins, f_out, "NL", config.intv)
            logging.info(f"merge upd_nl  complete, file is {f_out}")
        else:
            logging.warning(f"unknown UPD type {f}")

    config.gsys = gsys


def merge_upd(f_ins, f_out, mode, intv=30):
    if mode == "NL":
        lines_in = []
        nlines = []
        nsats = []
        idx_sys = []
        for isys in range(0, len(f_ins)):
            idxHeads = []
            with open(f_ins[isys]) as file_object:
                lines = file_object.readlines()
            nline = len(lines)
            nlines.append(nline)
            for i in range(0, nline):
                lines_in.append(lines[i])
                if len(idxHeads) < 3:
                    if "EPOCH-TIME" in lines[i]:
                        idxHeads.append(i)
            recLen = idxHeads[1] - idxHeads[0] - 1
            nsats.append(recLen)

        idx_sys.append(0)
        idx = nlines[0]
        for isys in range(1, len(f_ins)):
            idx_sys.append(idx)
            idx += nlines[isys]

        nepo = int(86400 / intv) + 1
        with open(f_out, 'w') as file_object:
            file_object.write('% UPD generated using upd_NL\n')
            for i in range(1, nepo):
                idx1 = 2 + (i - 1) * (nsats[0] + 1) - 1
                idx2 = 1 + i * (nsats[0] + 1) - 1
                for j in range(idx1, idx2 + 1):
                    file_object.write(lines_in[j])

                for isys in range(1, len(f_ins)):
                    idx1 = idx_sys[isys] + 3 + (i - 1) * (nsats[isys] + 1) - 1
                    idx2 = idx_sys[isys] + 1 + i * (nsats[isys] + 1) - 1
                    for j in range(idx1, idx2 + 1):
                        file_object.write(lines_in[j])
            file_object.write("EOF\n")
    elif mode in ["EWL25", "EWL24", "EWL", "WL"]:
        with open(f_out, 'w') as f1:
            f1.write(f"% UPD generated using upd_{mode}\n")
            for file in f_ins:
                with open(file) as f2:
                    for line in f2:
                        if line[0] != "%" and line.find("EOF") < 0:
                            f1.write(line)
            f1.write("EOF\n")


def get_crd_snx(f_snx, site_list):
    data = []
    try:
        with open(f_snx, 'r', encoding='UTF-8') as f:
            block = ''
            for line in f:
                if line.startswith('-SOLUTION/ESTIMATE'):
                    break
                if line.startswith('+'):
                    block = line[1:].rstrip()
                    continue
                if line.startswith('-'):
                    block = ''
                    continue
                if line[0] != ' ':
                    continue
                if block == 'SITE/RECEIVER':
                    site = line[1:5].lower()
                    if site not in site_list:
                        continue
                    data.append({'site': site, 'type': 'rec', 'val': line[42:62], 'obj': 'SNX'})
                elif block == 'SITE/ANTENNA':
                    site = line[1:5].lower()
                    if site not in site_list:
                        continue
                    data.append({'site': site, 'type': 'ant', 'val': line[42:62], 'obj': 'SNX'})
                elif block == 'SOLUTION/ESTIMATE':
                    site = line[14:18].lower()
                    if site not in site_list:
                        continue
                    if line[7:11] == 'STAX':
                        data.append({'site': site, 'type': 'crd_x', 'val': float(line[47:68]),
                                     'sig': float(line[69:80]), 'obj': 'SNX'})
                    elif line[7:11] == 'STAY':
                        data.append({'site': site, 'type': 'crd_y', 'val': float(line[47:68]),
                                     'sig': float(line[69:80]), 'obj': 'SNX'})
                    elif line[7:11] == 'STAZ':
                        data.append({'site': site, 'type': 'crd_z', 'val': float(line[47:68]),
                                     'sig': float(line[69:80]), 'obj': 'SNX'})

    except FileNotFoundError:
        logging.warning(f'file not found {f_snx}')
    return pd.DataFrame(data)


def get_crd_res(f_res, site_list, max_sig=8):
    try:
        with open(f_res) as f:
            lines = f.readlines()
    except FileNotFoundError:
        logging.warning(f'file not found {f_res}')
        return pd.DataFrame()
    
    data = []
    sig = -1
    for line in lines:
        if line[0:2] != '##':
            break
        if line[0:7] == '##Sigma':
            sig = float(line[10:23])
    
    if sig < 0:
        logging.warning(f"sigma0 not find in {f_res}")
        return pd.DataFrame()
    elif sig > max_sig:
        logging.warning(f"sigma too large {sig}")
        return pd.DataFrame()

    for line in lines:
        if line.startswith('RES:='):
            break
        if line.startswith('PAR:='):
            if len(line) < 155:
                continue
            tp = line[24:29]
            if tp == 'CRD_X' or tp == 'CRD_Y' or tp == 'CRD_Z':
                site = line[19:23].lower()
                if site in site_list:
                    data.append({'site': site, 'type': tp.lower(), 'val': float(line[131:156]),
                                    'sig': 0.001, 'obj': 'RES'})
    return pd.DataFrame(data)


def xml_receiver_snx(sites: list, f_snxs: list, f_xml):

    receiver = ET.Element('receiver')
    data = pd.DataFrame()
    for file in f_snxs:
        if not os.path.isfile(file):
            continue
        data = data.append(get_crd_snx(file, sites))

    sites_used = []
    for site in sites:
        df = data[data.site == site]
        df_x = df[df.type == 'crd_x'].sort_values(by=['obj'], ascending=False)
        df_y = df[df.type == 'crd_y'].sort_values(by=['obj'], ascending=False)
        df_z = df[df.type == 'crd_z'].sort_values(by=['obj'], ascending=False)
        if df_x.empty or df_y.empty or df_z.empty:
            logging.warning(f'site info not found: {site}')
            continue

        sites_used.append(site)
        info = {
            'X': f'{df_x.val.values[0]:20.8f}',
            'Y': f'{df_y.val.values[0]:20.8f}',
            'Z': f'{df_z.val.values[0]:20.8f}',
            'dX': f'{df_x.sig.values[0]:8.4f}',
            'dY': f'{df_y.sig.values[0]:8.4f}',
            'dZ': f'{df_z.sig.values[0]:8.4f}',
            'id': site.upper(), 'obj': df_x.obj.values[0]
        }
        if not df[df.type == 'rec'].empty:
            info['rec'] = df[df.type == 'rec']['val'].values[0]
        if not df[df.type == 'ant'].empty:
            info['ant'] = df[df.type == 'ant']['val'].values[0]

        ET.SubElement(receiver, 'rec', attrib=info)

    root = ET.Element('config')
    gen = ET.SubElement(root, 'gen')
    rec = ET.SubElement(gen, 'rec')
    rec.text = ' '.join([s.upper() for s in sites_used])
    root.append(receiver)

    tree = ET.ElementTree(root)
    pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml, encoding='utf-8', xml_declaration=True)


def mkdir(dir_list):
    for d in dir_list:
        if not os.path.isdir(d):
            os.makedirs(d)


def _raise_error(msg):
    logging.critical(msg)
    raise SystemExit(msg)

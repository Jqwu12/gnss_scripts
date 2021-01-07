import os
import math
import logging
import shutil
from funcs import gnss_files as gf
import pandas as pd
import time
from contextlib import contextmanager


@contextmanager
def timeblock(label):
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        logging.info(f"#### {label:30s}, duration {end - start:15.5f} sec")


def list2str(x, isupper=False):
    if not isinstance(x, list):
        return ''
    else:
        info = ''
        if isupper:
            for i in x:
                info = info + " " + str(i).upper()
        else:
            for i in x:
                info = info + " " + str(i)
        info = info.strip()
        return info


def split_config_by_receivers(config, num):
    """ 
    Divide condif to several child configs, each one has part of the receivers.
    This method is particularly useful for multi-thread process
    IN  : number of parts
    OUT : list of child config objects
    Attention: the 'a = b' in python presents a is the reference of b
    """
    all_receivers = config.all_receiver().split()
    if not all_receivers:
        logging.error("No receiver in config")
        return []
    num = min(num, len(all_receivers))
    nleo = len(config.leolist())
    nsta = len(config.stalist())
    leo_num = round(num * nleo / (nleo + nsta))
    sta_num = num - leo_num
    leo_subs = _split_list(config.leolist(), leo_num)
    sta_subs = _split_list(config.stalist(), sta_num)
    child_configs = []
    for leo_sub in leo_subs:
        #child_config = copy.deepcopy(config)
        child_config = config.copy()
        child_config.update_leolist(leo_sub)
        child_config.update_stalist('NONE')
        child_configs.append(child_config)
    for sta_sub in sta_subs:
        #child_config = copy.deepcopy(config)
        child_config = config.copy()
        child_config.update_stalist(sta_sub)
        child_config.update_leolist('NONE')
        child_configs.append(child_config)
    return child_configs


def _split_list(list_in, num):
    """
    Divide a list to several parts, each part has similiar length
    e.g. [1,2,3,4,5] => [[1,2],[3,4],[5]]
    """
    if num >= len(list_in):
        return list_in
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
    f_res = config.get_filename("recover_in", check=True)
    if not os.path.isfile(f_res):
        logging.warning(f"file not found {f_res}")
        return [],[]
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
        logging.warning(f"too many bad code residuals for station: {list2str(site_rm_P)}")
    site_rm_L = list(site_L[(site_L.counts > max_count) & (site_L.freq > max_freq)].index)
    if site_rm_L:
        logging.warning(f"too many bad phase residuals for station: {list2str(site_rm_L)}")
    site_rm = site_rm_P + site_rm_L
    site_rm = list(set(site_rm))
    # remove sats
    sat_rm_P = list(sat_P[(sat_P.counts > max_count) & (sat_P.freq > max_freq)].index)
    if sat_rm_P:
        logging.warning(f"too many bad code residuals for satellite: {list2str(sat_rm_P)}")
    sat_rm_L = list(sat_L[(sat_L.counts > max_count) & (sat_L.freq > max_freq)].index)
    if sat_rm_L:
        logging.warning(f"too many bad phase residuals for satellite: {list2str(sat_rm_L)}")
    sat_rm += sat_rm_P + sat_rm_L
    sat_rm = list(set(sat_rm))
    return site_rm, sat_rm


def check_turboedit_log(config, nthread, label="turboedit", path="xml"):
    # LEO satellites need to be considered
    site_good = []
    # site_rm = []
    if nthread == 1:
        f_name = os.path.join(path, f"{label}.log")
        try:
            with open(f_name) as f:
                for line in f:
                    if line.find("Site and Evaluation") > 0:
                        if line[65:69] == "GOOD":
                            site = line[58:62].lower()
                            if site not in site_good:
                                site_good.append(site)
                        # if line[65:68] == 'BAD':
                        #     site = line[58:62].lower()
                        #     site_rm.append(site)
        except FileNotFoundError:
            logging.warning(f"Cannot open turboedit log file {f_name}")
    else:
        for i in range(1, nthread + 1):
            f_name = os.path.join(path, f"{label}{i:0>2d}.log")
            try:
                with open(f_name) as f:
                    for line in f:
                        if line.find("Site and Evaluation") > 0:
                            if line[65:69] == "GOOD":
                                site = line[58:62].lower()
                                if site not in site_good:
                                    site_good.append(site)
                            # if line[65:68] == 'BAD':
                            #     site = line[58:62].lower()
                            #     site_rm.append(site)
            except FileNotFoundError:
                logging.warning(f"Cannot open turboedit log file {f_name}")
                continue
    site_rm_final = list(set(config.stalist()).difference(set(site_good)))
    # site_rm_final = []
    # for site in set(site_rm):
    #     if site_rm.count(site) > 3:
    #         site_rm_final.append(site)
    if site_rm_final:
        msg = f"STATIONS {list2str(site_rm_final)} are removed due to BAD Turboedit results"
        logging.warning(msg)
        config.remove_ambflag_file(site_rm_final)
    config.update_stalist(site_good)
    # config.remove_sta(site_rm_final)


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
        logging.warning(f"SATELLITES {list2str(sat_rm)} are removed")
    return sat_rm


def check_res_sigma(config, max_sig=8):
    site_rm = []
    for site in config.stalist():
        file = config.get_file('recover_in', {'recnam': site.upper()}, check=True)
        if not file:
            logging.warning(f"cannot find resfile for {site}")
            site_rm.append(site)
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
                        site_rm.append(site)
                    break
        if sig < 0:
            logging.warning(f"sigma0 not find in {file}")
            site_rm.append(site)

    if site_rm:
        config.remove_sta(site_rm)
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


def backup_files(config, files, sattype='gns', suffix="bak"):
    for file in files:
        file_olds = config.get_filename(file.lower(), check=True, sattype=sattype)
        for f_name in file_olds.split():
            f_new = f"{f_name}.{suffix}"
            try:
                shutil.copy(f_name, f_new)
            except IOError as e:
                logging.warning(f"unable to backup file {file}")


def recover_files(config, files, sattype='gns', suffix="bak"):
    for file in files:
        file_olds = config.get_filename(file.lower(), check=False, sattype=sattype)
        for f_name in file_olds.split():
            f_new = f"{f_name}.{suffix}"
            try:
                shutil.copy(f_new, f_name)
            except IOError as e:
                logging.warning(f"unable to recover file {file}.{suffix}")


def get_rnxc_satlist(f_name):
    sats = []
    try:
        with open(f_name) as f:
            for line in f:
                if line.find("END OF HEADER") > 0:
                    break
                if line[60:68] == "PRN LIST":
                    info = line[0:60]
                    sats.extend(info.split())
            return sats
    except FileNotFoundError:
        logging.error(f"file not found {f_name}")
        return


def copy_ambflag_from(ambflagdir):
    if not os.path.isdir(ambflagdir):
        logging.warning(f"cannot find source ambflag dir {ambflagdir}")
        return False
    logging.info(f"ambflag files are copied from {ambflagdir}")
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
        file_olds = config.get_filename(file.lower(), check=True, sattype=sattype)
        for f_name in file_olds.split():
            f_new = f"{f_name}_{scheme}"
            try:
                shutil.copy(f_name, f_new)
            except IOError as e:
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
        file_olds = config.get_filename(file.lower(), check=False, sattype=sattype)
        for f_name in file_olds.split():
            if not schemes:
                if os.path.isfile(f_name):
                    try:
                        shutil.copy(f_name, path)
                    except IOError as e:
                        logging.warning(f"unable to copy file {f_name}")
                else:
                    logging.warning(f"file not found {f_name}")
            else:
                for sch in schemes:
                    f_new = f"{f_name}_{sch}"
                    if os.path.isfile(f_new):
                        try:
                            shutil.copy(f_new, path)
                        except IOError as e:
                            logging.warning(f"unable to copy file {f_new}")
                    else:
                        logging.warning(f"file not found {f_new}")


def get_grg_wsb(config):
    """
    purpose: grep WL UPD from CNES/CLS integer clock products
    """
    f_wsb = config.get_filename('upd_wl')
    f_clks = config.get_filename('rinexc', check=True).split()
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
                    upd = -1.0*float(info[9])
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
        config.update_process(sys=gsys)
        f_out = config.get_filename(f)
        if not f_out:
            logging.error("Cannot get merged upd name")
        f_ins = []
        for s in gsys:
            config.update_process(sys=s)
            f_in = config.get_filename(f, check=True)
            if f_in:
                f_ins.append(f_in)
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
            intv = config.config['process_scheme']['intv']
            merge_upd(f_ins, f_out, "NL", int(intv))
            logging.info(f"merge upd_nl  complete, file is {f_out}")
        else:
            logging.warning(f"unknown UPD type {f}")

    config.update_process(sys=gsys)


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


def read_snxfile(snxfile, site_list):
    """
    snxfile: sinex file name
    site_list: [list] sites
    get sites crd from snx file
    return : [map] site_name:crd
    """
    crd = {}
    snx_crd = {}
    # logging.info(f"read snxfile:{snxfile}")
    if os.path.isfile(snxfile):
        with open(snxfile, "r", errors="ignore") as myfile:
            flag = False
            for line in myfile:
                if line.find("+SOLUTION/ESTIMATE") != -1:
                    flag = True
                    myfile.readline()
                    continue

                elif line.find("-SOLUTION/ESTIMATE") != -1:
                    break

                if flag:
                    temp = line.split()
                    idx = temp[1]
                    site = temp[2]
                    value = float(temp[8])
                    std = float(temp[9])
                    if idx.find("STA") == -1:
                        continue
                    if idx == "STAX":
                        snx_crd[site.lower()] = [value, std]
                    else:
                        snx_crd[site.lower()].extend([value, std])
    for site in site_list:
        if snx_crd.get(site.lower()):
            crd[site.lower()] = snx_crd[site.lower()]
    return crd


def get_crd_res(config):
    crds = {}
    for site in config.stalist():
        f_res = config.get_dailyfile('recover_in', {'recnam': site.upper()}, check=True).strip()
        if not f_res:
            continue
        x = 0; y = 0; z = 0
        with open(f_res) as f:
            for line in f:
                if line[0] == '#':
                    continue
                if line[0:3] == 'PAR':
                    if line.find(f"{site.upper()}_CRD_X_") == 19 and len(line) >= 155:
                        x = float(line[131:156])
                    if line.find(f"{site.upper()}_CRD_Y_") == 19 and len(line) >= 155:
                        y = float(line[131:156])
                    if line.find(f"{site.upper()}_CRD_Z_") == 19 and len(line) >= 155:
                        z = float(line[131:156])
                if line[0:3] == 'RES':
                    break
                if x != 0 and y != 0 and z != 0:
                    break
        if x != 0 and y != 0 and z != 0:
            crds[site] = [x, y, z]
    return crds


def mkdir(dir_list):
    for d in dir_list:
        if not os.path.isdir(d):
            os.makedirs(d)


def _raise_error(msg):
    logging.critical(msg)
    raise SystemExit(msg)

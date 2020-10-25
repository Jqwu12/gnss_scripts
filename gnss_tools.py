import os
import platform
import gnss_xml
import gnss_config
import logging
import subprocess
import copy
import shutil
from threading import Thread


def run_great(bindir, app, config, str_args="", newxml=True, nthread=1, stop=True, out=None, **kwargs):
    """ Run GREAT APP """
    if app == 'great_ambfixD' and config.is_integer_clock() and not config.is_integer_clock_osb():
        _get_grg_wsb(config)
    if nthread > 1:
        _run_great_app_multithreading(bindir, app, config, str_args, nthread, stop=stop, out=out, **kwargs)
    else:
        _run_great_app(bindir, app, config, str_args, newxml, stop=stop, out=out, **kwargs)


def _run_great_app(bindir, app, config, str_args="", newxml=True, stop=True, out=None, **kwargs):
    """ Run GREAT APP Default"""
    grt_app = _executable_app(bindir, app)
    f_xml = app + ".xml"
    if newxml:
        if os.path.isfile(f_xml):
            os.remove(f_xml)
        gnss_xml.generate_great_xml(config, app, f_xml, **kwargs)
    else:
        if not os.path.isfile(f_xml):
            gnss_xml.generate_great_xml(config, app, f_xml, **kwargs)
    grt_cmd = f"{grt_app} -x {f_xml} {str_args}"
    if out:
        grt_cmd = f"{grt_cmd} > {out}.log 2>&1"
    _run_cmd(grt_cmd, stop)


def _run_great_app_multithreading(bindir, app, config, str_args="", nthread=8, stop=True, out=None, **kwargs):
    """ Run GRAET App with multi-threading (by dividing receivers list) """
    if nthread <= 0 or nthread > 99:
        _raise_error(f"Number of threads = {nthread}")
    grt_app = _executable_app(bindir, app)
    child_configs = split_config_by_receivers(config, nthread)
    nthread = min(nthread, len(child_configs))
    thread_list = []
    for i in range(nthread):
        f_xml = f"{app}{i + 1:0>2d}.xml"
        gnss_xml.generate_great_xml(child_configs[i], app, f_xml, ithread=i + 1, **kwargs)
        grt_cmd = f"{grt_app} -x {f_xml} {str_args}"
        if out:
            grt_cmd = f"{grt_cmd} > {out}{i + 1:0>2d}.log 2>&1"
        new_thread = Thread(target=_run_cmd, args=(grt_cmd, stop))
        thread_list.append(new_thread)
        new_thread.start()
    for i in range(len(thread_list)):
        thread_list[i].join()


def _run_cmd(cmd, stop=True):
    logging.debug(cmd)
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        if stop:
            _raise_error(f"Run {cmd.split()[0]} error, check log")
        else:
            logging.error(f"Run {cmd.split()[0]} error, check log")


def _executable_app(bindir, app):
    if not os.path.isdir(bindir):
        _raise_error(f"GREAT Bin {bindir} not exist")
    app = app.strip()
    if platform.system() == 'Windows':
        grt_app = os.path.join(bindir, f"{app}.exe")
    else:
        grt_app = os.path.join(bindir, app)
    if not os.path.isfile(grt_app):
        _raise_error(f"GREAT App {grt_app} not exist")
    return grt_app


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


def copy_result_files_to_path(config, files, path, sattype='gns'):
    """
    Purpose: Copy result files to another path
    e,g, cp upd_nl_2019100_G ${upd_dir}
    """
    if not os.path.isdir(path):
        logging.warning(f"Input path {path} not exists, creating...")
        os.makedirs(path)
    for file in files:
        file_olds = config.get_filename(file.lower(), check=True, sattype=sattype)
        for f_name in file_olds.split():
            try:
                shutil.copy(f_name, path)
            except IOError as e:
                logging.warning(f"unable to copy file {file}")


def _get_grg_wsb(config):
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


def merge_upd_all(config, gsys):
    """
    merge ewl, wl and nl UPD files
    inputs : config    config
             gsys      "GREC"
    """
    for f in ["upd_ewl", "upd_wl", "upd_nl"]:
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
        if f == "upd_ewl":
            merge_upd(f_ins, f_out, "EWL")
            logging.info(f"merge upd_ewl complete, file is {f_out}")
        elif f == "upd_wl":
            merge_upd(f_ins, f_out, "WL")
            logging.info(f"merge upd_wl  complete, file is {f_out}")
        else:
            intv = config.config['process_scheme']['intv']
            merge_upd(f_ins, f_out, "NL", int(intv))
            logging.info(f"merge upd_nl  complete, file is {f_out}")

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
    elif mode == "EWL" or mode == "WL":
        with open(f_out, 'w') as f1:
            f1.write(f"% UPD generated using upd_{mode}\n")
            for file in f_ins:
                with open(file) as f2:
                    for line in f2:
                        if line[0] != "%" and line.find("EOF") < 0:
                            f1.write(line)
            f1.write("EOF\n")


def mkdir(dir_list):
    for d in dir_list:
        if not os.path.isdir(d):
            os.makedirs(d)


def _raise_error(msg):
    logging.critical(msg)
    raise SystemExit(msg)

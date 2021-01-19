import os
import platform
from funcs import gnss_xml, gnss_tools as gt
import logging
import subprocess
from threading import Thread


def run_great(bindir, app, config, label="", str_args="", xmldir=None,
              newxml=True, nthread=1, stop=True, **kwargs):
    """ Run GREAT APP """
    if not label:
        label = app
    if nthread > 1:
        with gt.timeblock(f"Normal End [{nthread:0>2d}] {label}"):
            return _run_great_app_multithreading(bindir, app, config, label, str_args, xmldir, nthread, stop=stop, **kwargs)
    else:
        with gt.timeblock(f"Normal End [{nthread:0>2d}] {label}"):
            return _run_great_app(bindir, app, config, label, str_args, xmldir, newxml, stop=stop, **kwargs)


def _run_great_app(bindir, app, config, label, str_args="", xmldir=None, newxml=True, stop=True, **kwargs):
    """ Run GREAT APP Default"""
    grt_app = _executable_app(bindir, app)
    if xmldir:
        if not os.path.isdir(xmldir):
            os.makedirs(xmldir)
        f_xml = os.path.join(xmldir, f"{label}.xml")
    else:
        f_xml = label + ".xml"
    f_out = os.path.join('tmp', f"{label}.log")
    if newxml:
        if os.path.isfile(f_xml):
            os.remove(f_xml)
        gnss_xml.generate_great_xml(config, app, f_xml, **kwargs)
    else:
        if not os.path.isfile(f_xml):
            gnss_xml.generate_great_xml(config, app, f_xml, **kwargs)
    grt_cmd = f"{grt_app} -x {f_xml} {str_args} > {f_out} 2>&1"
    return _run_cmd(grt_cmd, stop)


def _run_great_app_multithreading(bindir, app, config, label, str_args="", xmldir=None, nthread=8, stop=True, **kwargs):
    """ Run GRAET App with multi-threading (by dividing receivers list) """
    if nthread <= 0 or nthread > 99:
        _raise_error(f"Number of threads = {nthread}")
    grt_app = _executable_app(bindir, app)
    child_configs = gt.split_config_by_receivers(config, nthread)
    nthread = min(nthread, len(child_configs))
    thread_list = []
    if xmldir:
        if not os.path.isdir(xmldir):
            os.makedirs(xmldir)
    for i in range(nthread):
        if xmldir:
            f_xml = os.path.join(xmldir, f"{label}{i + 1:0>2d}.xml")
        else:
            f_xml = f"{label}{i + 1:0>2d}.xml"
        f_out = os.path.join('tmp', f"{label}{i + 1:0>2d}.log")
        gnss_xml.generate_great_xml(child_configs[i], app, f_xml, ithread=i + 1, **kwargs)
        grt_cmd = f"{grt_app} -x {f_xml} {str_args} > {f_out} 2>&1"
        new_thread = Thread(target=_run_cmd, args=(grt_cmd, stop))
        thread_list.append(new_thread)
        new_thread.start()
    for i in range(len(thread_list)):
        thread_list[i].join()
    return True


def _run_cmd(cmd, stop=True):
    logging.debug(cmd)
    try:
        subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        if stop:
            _raise_error(f"Run [{cmd}] error, check log")
        else:
            logging.error(f"Run [{cmd}] error, check log")
            return False


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


def _raise_error(msg):
    logging.critical(msg)
    raise SystemExit(msg)
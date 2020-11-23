import os
import platform
import gnss_xml
import gnss_config
import gnss_tools as gt
import logging
import subprocess
from threading import Thread

def run_great(bindir, app, config, str_args="", newxml=True, nthread=1, stop=True, out=None, **kwargs):
    """ Run GREAT APP """
    if app == 'great_ambfixD' and config.is_integer_clock() and not config.is_integer_clock_osb():
        gt.get_grg_wsb(config)
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
    child_configs = gt.split_config_by_receivers(config, nthread)
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


def _raise_error(msg):
    logging.critical(msg)
    raise SystemExit(msg)
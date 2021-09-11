from genericpath import exists
import os
import math
import shutil
import sys
import logging
import time
from datetime import datetime
import argparse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import matplotlib as mpl
import seaborn as sns
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import GnssTime, sod2hms, gns_sat, gns_name, gns_id, GnssConfig, GrtClkdif, GrtOrbdif, GrtSp3orb, timeblock
from gnss_plot import draw_orbdif, draw_orbdif_series, read_clkdif, read_orbdif


def read_time_info(file):
    try:
        with open(file) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        logging.warning(f"file not found {file}")
        return pd.DataFrame()

    data = []
    for line in lines:
        if len(line) >= 148 and line.startswith('Time for Processing epoch'):
            str_time = line[27:46]
            dd = str_time.strip().split()
            year, mon, day = dd[0].split('-')
            hh, mm, ss = dd[1].split(':')
            crt_date = datetime(int(year), int(mon), int(day), int(hh), int(mm), int(ss))
            temp_dict = {
                'date': crt_date, 't2': float(line[55:65]), 
                'niter': int(line[80:82]), 'nrec': int(line[92:95]), 'nobs': int(line[115:123])
            }
            if len(line) > 148:
                temp_dict['sig'] = float(line[159:])
            data.append(temp_dict)
        elif len(line) >= 139 and line.startswith('Finish epoch'):
            str_time = line[13:32]
            dd = str_time.strip().split()
            year, mon, day = dd[0].split('-')
            hh, mm, ss = dd[1].split(':')
            crt_date = datetime(int(year), int(mon), int(day), int(hh), int(mm), int(ss))
            temp_dict = {
                'date': crt_date, 't0': float(line[39:47]), 't1': float(line[48:55]),
                't2': float(line[56:63]), 'niter': int(line[76:79]), 'nrec': int(line[87:91]), 'nobs': int(line[99:105]), 'sig': float(line[131:])
            }
            data.append(temp_dict)

    return pd.DataFrame(data)


def draw_time_info(data, figname, title=''):
    fig, ax = plt.subplots(3, 1, figsize=(8, 8), sharex='col', constrained_layout=True)

    ax[0].plot(data.date, data.nobs, '.', color='darkblue', alpha=0.5)
    ax[0].set(ylim=(0, 6000))
    ax[0].set_ylabel('Num of obs', color='darkblue')
    ax[0].tick_params(axis='y', labelcolor='darkblue')
    ax1 = ax[0].twinx()
    ax1.plot(data.date, data.nrec, '.', color='red', alpha=0.5)
    ax1.grid()
    ax1.set(ylim=(0, 100))
    ax1.set_ylabel('Num of rec', color='red')
    ax1.tick_params(axis='y', labelcolor='red')

    ax[1].plot(data.date, data.niter, '-', color='darkblue', alpha=0.5)
    ax[1].set(ylim=(0, 10))
    ax[1].set_ylabel('Num of iter', color='darkblue')
    ax[1].tick_params(axis='y', labelcolor='darkblue')
    ax2 = ax[1].twinx()
    if 'sig' in data:
        ax2.plot(data.date, data.sig, '.', color='red', alpha=0.5)
    ax2.grid()
    ax2.set(ylim=(0, 5))
    ax2.set_ylabel('Sigma0', color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    ax[2].plot(data.date, data.t1, '.', color='darkblue', alpha=0.5)
    ax[2].hlines(5, data.date.min(), data.date.max(), colors='grey', linestyles='dashed', linewidth=4)
    ax[2].set(ylim=(0, 10))
    ax[2].set_ylabel('Compute time [s]', color='darkblue')
    ax[2].tick_params(axis='y', labelcolor='darkblue')
    ax3 = ax[2].twinx()
    ax3.plot(data.date, data.t2, '.', color='red', alpha=0.5)
    ax3.grid()
    ax3.set(ylim=(0, 10))
    ax3.set_ylabel('Total time [s]', color='red')
    ax3.tick_params(axis='y', labelcolor='red')

    for tick in ax[2].get_xticklabels():
        tick.set_rotation(30)
    if title:
        ax[0].set(title=title)

    fig.savefig(figname, dpi=1200)
    plt.close()


def read_memory(file):
    try:
        with open(file) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        logging.warning(f"file not found {file}")
        return pd.DataFrame()

    data = []
    for line in lines:
        if len(line) < 23:
            continue
        tt = GnssTime.from_str(line[0:19])
        tt += time.timezone
        val = int(line.split()[2]) / 1024 / 1024
        data.append({'date': tt.datetime(), 'mem': val})
    return pd.DataFrame(data)


def draw_memory(data, figname, title=''):
    fig, ax = plt.subplots(figsize=(8, 8))

    ax.plot(data.date, data['mem'], '-.')
    ax.set(ylabel='RAM usage [GB]', title=title)
    for tick in ax.get_xticklabels():
        tick.set_rotation(30)
    fig.savefig(figname, dpi=1200)
    plt.close()


def get_clkdif_statistic(data, beg: datetime, end: datetime):
    data1 = data[(data.date >= beg) & (data.date < end)]
    if data1.empty:
        return pd.DataFrame(), pd.DataFrame()
    sats = list(set(data.sat))
    sats.sort()
    sat_sum = []
    sat_data = pd.DataFrame()
    for sat in sats:
        data2 = data1[data1.sat == sat]
        data_fnl = data2
        for _ in range(20):
            mval = data_fnl.val.median()
            std = data_fnl.val.std()
            idx = (data_fnl.val < mval + 3 * std) & (data_fnl.val > mval - 3 * std)
            if len(idx) == 0:
                break
            data_fnl = data_fnl[idx]
        
        if len(data_fnl) < 100:
            continue
        std_val = data_fnl.val.std()
        if std_val > 1:
            logging.warning(f'STD of {sat} too large: {std_val:10.5f}')
            continue
        sat_sum.append({
            'sat': sat, 'mean': data_fnl.val.mean(), 'std': data_fnl.val.std(),
            'rms': math.sqrt(data_fnl.val.dot(data_fnl.val) / len(data_fnl)), 'gsys': gns_name(sat[0])
        })
        sat_data = sat_data.append(data_fnl)

    return sat_data, pd.DataFrame(sat_sum)


def draw_clkdif(data, figname: str, title=''):
    sats = list(set(data['sat']))
    setgns = set([s[0] for s in sats])
    gns = [s for s in 'GECR' if s in setgns]
    nf = len(gns)
    fig, ax = plt.subplots(nf, 1, figsize=(8, 2 * nf + 2), sharex='col', constrained_layout=True)
    sats = set(data.sat)
    ymax = 10

    markers = ['.', '1', '2', '+']
    if nf > 1:
        for i in range(nf):
            gsys = gns[i]
            j = 0
            for sat in gns_sat(gsys):
                if sat not in sats:
                    continue
                dd = data[data.sat == sat]
                ax[i].plot(dd.date, dd.val, markers[int(j/8)], label=sat)
                j += 1
            mid_val = int(data.val.median() / 5) * 5
            ax[i].set(ylim=(mid_val - ymax, mid_val + ymax), ylabel='Clock Diff [ns]')
            ax[i].text(0.1, 0.1, gns_name(gsys), size='large', weight='bold', transform=ax[i].transAxes)
            ax[i].legend(loc='upper left', ncol=12, fontsize=9, columnspacing=0.3, handletextpad=0.05)
        ax[0].set(title=title)
        for tick in ax[nf - 1].get_xticklabels():
            tick.set_rotation(30)
    else:
        gsys = gns[0]
        j = 0
        for sat in gns_sat(gsys):
            if sat not in sats:
                continue
            dd = data[data.sat == sat]
            ax.plot(dd.date, dd.val, markers[int(j/8)], label=sat)
            j += 1
        mid_val = int(data.val.median() / 5) * 5
        ax.set(ylim=(mid_val - ymax, mid_val + ymax), ylabel='Clock Diff [ns]', title=title)
        ax.text(0.1, 0.1, gns_name(gsys), size='large', weight='bold', transform=ax.transAxes)
        ax.legend(loc='upper left', ncol=12, fontsize=9, columnspacing=0.3, handletextpad=0.05)
        for tick in ax.get_xticklabels():
            tick.set_rotation(30)

    fig.savefig(figname, dpi=1200)
    logging.info(f'save figure {figname}')
    plt.close()


def draw_clkdif_std(data, figname, title=''):
    setgns = set(data.gsys)
    gns = [s for s in ['GPS', 'GAL', 'BDS', 'GLO'] if s in setgns]
    nf = len(gns)
    fig, ax = plt.subplots(nf, 1, figsize=(8, 2 * nf + 2), constrained_layout=True)

    bar_width = 0.4
    ymax = 1.0

    if nf > 1:
        for i in range(nf):
            gsys = gns[i]
            dd1 = data[data.gsys == gsys]
            ax[i].bar(np.arange(len(dd1)), dd1['std'], width=bar_width)
            ax[i].grid(axis='x')
            ax[i].set(xticks=np.arange(len(dd1)), ylim=(0, ymax))
            ax[i].set_xticklabels(list(dd1.sat), rotation=90)
            val1 = dd1['std'].mean()
            ax[i].text(0.1, 0.85, f'{val1:5.3f} ns', transform=ax[i].transAxes)
            ax[i].set(ylabel='STD [ns]')
        ax[0].set(title=title)
    else:
        ax.bar(np.arange(len(data)), data['std'], width=bar_width)
        ax.grid(axis='x')
        ax.set(xticks=np.arange(len(data)), ylim=(0, ymax), title=title)
        ax.set_xticklabels(list(data.sat), rotation=90)
        val1 = data['std'].mean()
        ax.text(0.1, 0.85, f'{val1:5.3f} ns', transform=ax.transAxes)
        ax.set(ylabel='STD [ns]')

    fig.savefig(figname, dpi=1200)
    logging.info(f'save figure {figname}')
    plt.close()


def draw_boxplot(data, figname, title=''):
    sats = list(set(data['sat']))
    setgns = set([s[0] for s in sats])
    gns = [s for s in 'GECR' if s in setgns]
    nf = len(gns)
    fig, ax = plt.subplots(nf, 1, figsize=(8, 2.5 * nf + 2), constrained_layout=False)
    plt.subplots_adjust(hspace=0.35)
    ymax = 4

    if nf > 1:
        for i in range(nf):
            dd = pd.DataFrame()
            for sat in gns_sat(gns[i]):
                dd = dd.append(data[data.sat == sat])
            mid_val = int(dd.val.median() / 2) * 2
            sns.boxplot(x="sat", y="val", data=dd, ax=ax[i])
            ax[i].set(ylabel='Clock diff [ns]', xlabel='', ylim=(mid_val-ymax, mid_val+ymax))
            for tick in ax[i].get_xticklabels():
                tick.set_rotation(90)
        ax[0].set(title=title)
    else:
        sns.boxplot(x="sat", y="val", data=data, ax=ax)
        mid_val = int(data.val.median() / 2) * 2
        ax.set(ylabel='Clock diff [ns]', xlabel='', ylim=(mid_val-ymax, mid_val+ymax), title=title)
        for tick in ax.get_xticklabels():
            tick.set_rotation(90)

    fig.savefig(figname, dpi=1200)
    logging.info(f'save figure {figname}')
    plt.close()


def monitor_clkdif(cen, gns: str):
    # run clkdif
    f_pce_xml = os.path.join('xml', 'pcelsq.xml')
    ref_tree = ET.parse(f_pce_xml)
    beg = ref_tree.getroot().find('gen').find('beg')
    t_beg = GnssTime.from_str(beg.text)
    end = ref_tree.getroot().find('gen').find('end')
    t_end = GnssTime.from_str(end.text)
    intv = int(ref_tree.getroot().find('gen').find('int').text)

    dend_time = GnssTime.from_datetime(datetime.utcnow())
    if dend_time > t_end:
        dend_time = t_end
    config = GnssConfig.from_file('cf_clk.ini')
    config.orb_ac = cen
    
    # get clkdif data
    crt_time = GnssTime(t_beg.mjd, 0)
    while crt_time < dend_time:
        end_time = GnssTime(crt_time.mjd, 86400 - intv)
        config.beg_time = crt_time
        config.end_time = end_time

        figdir = os.path.join('figs', f'{crt_time.year}{crt_time.doy:0>3d}')
        if not os.path.isdir(figdir):
            os.makedirs(figdir)
        
        figfile1 = os.path.join(figdir, f'clkdif_{crt_time.year}{crt_time.doy:0>3d}_{cen}.png')
        figfile2 = os.path.join(figdir, f'clkstd_{crt_time.year}{crt_time.doy:0>3d}_{cen}.png')
        figfile3 = os.path.join(figdir, f'boxplot_{crt_time.year}{crt_time.doy:0>3d}_{cen}.png')
        fig_exist = os.path.isfile(figfile1) and os.path.isfile(figfile2) and os.path.isfile(figfile3)
        if crt_time.mjd != t_beg.mjd and crt_time.mjd != dend_time.mjd and fig_exist:
            crt_time += 86400
            continue

        data = pd.DataFrame()
        for gs in gns:
            file = os.path.join('clkdif', f'clkdif_{crt_time.year}{crt_time.doy:0>3d}_{cen}_{gs}')
            if crt_time.mjd == t_beg.mjd or crt_time.mjd == dend_time.mjd or not os.path.isfile(file):
                config.gsys = gs
                GrtClkdif(config, f'clkdif_{cen}_{gs}').run()
            
            if not os.path.isfile(file):
                continue
            f_dif_xml = os.path.join(wkdir, 'xml', f'clkdif_{cen}_{gs}.xml')
            ref_tree = ET.parse(f_dif_xml)
            refsat = ref_tree.getroot().find('gen').find('refsat').text.strip()
            data_tmp = read_clkdif(file, crt_time, refsat)
            if not data_tmp.empty and len(data_tmp) > 1000 and len(set(data_tmp.sat)) > 4:
                data = data.append(data_tmp)
        
        if not data.empty:
            draw_clkdif(data, figfile1, f'{str(crt_time)}~{str(end_time)} ({cen.upper()})')
            data0, data1 = get_clkdif_statistic(data, crt_time.datetime(), end_time.datetime())
            if not data1.empty:
                draw_clkdif_std(data1, figfile2, f'{str(crt_time)}~{str(end_time)} ({cen.upper()})')
            if not data0.empty:
                draw_boxplot(data0, figfile3, f'{str(crt_time)}~{str(end_time)} ({cen.upper()})')
        else:
            logging.warning(f'no data for {str(crt_time)}~{str(end_time)}, reference: {cen}')

        crt_time += 86400
        
    # figname = os.path.join(figdir, f'clkdif_{t_beg.year}{t_beg.doy:0>3d}_{cen}_all.png')
    # if data.empty or len(data) < 1000 or len(set(data.sat)) < 4:
    #     return
    # draw_clkdif(data, figname, f'{str(t_beg)}~{str(dend_time)} ({cen.upper()})')

    # # draw clkdif statistics
    # crt_time = GnssTime(t_beg.mjd, 0)
    # while crt_time < dend_time:
    #     end_time = GnssTime(crt_time.mjd, 86400 - intv)
    #     data0, data1 = get_clkdif_statistic(data, crt_time.datetime(),end_time.datetime())
    #     figname1 = os.path.join(figdir, f'clkstd_{crt_time.year}{crt_time.doy:0>3d}_{cen}.png')
    #     figname2 = os.path.join(figdir, f'boxplot_{crt_time.year}{crt_time.doy:0>3d}_{cen}.png')
    #     if not data1.empty:
    #         draw_clkdif_std(data1, figname1, f'{str(crt_time)}~{str(end_time)} ({cen.upper()})')
    #     if not data0.empty:
    #         draw_boxplot(data0, figname2, f'{str(crt_time)}~{str(end_time)} ({cen.upper()})')
    #     crt_time += 86400

def monitor_orbdif(cen, gns: str):
    f_pce_xml = os.path.join('xml', 'pcelsq.xml')
    ref_tree = ET.parse(f_pce_xml)
    beg = ref_tree.getroot().find('gen').find('beg')
    t_beg = GnssTime.from_str(beg.text)
    end = ref_tree.getroot().find('gen').find('end')
    t_end = GnssTime.from_str(end.text)
    intv = 300
    
    dend_time = GnssTime.from_datetime(datetime.utcnow())
    if dend_time > t_end:
        dend_time = t_end
    dend_time -= 86400
    config = GnssConfig.from_file('cf_clk.ini')
    config.orb_ac = cen
    config.intv = intv
    
    if not os.path.isdir('orbdif'):
        os.makedirs('orbdif')

    crt_time = GnssTime(t_beg.mjd, 0)
    while crt_time < dend_time:
        end_time = GnssTime(crt_time.mjd, 86400 - intv)
        if crt_time.mjd == t_beg.mjd:
            config.beg_time = t_beg + intv*5
        else:
            config.beg_time = crt_time
        config.end_time = end_time
        
        figdir = os.path.join('figs', f'{crt_time.year}{crt_time.doy:0>3d}')
        if not os.path.isdir(figdir):
            os.makedirs(figdir)
        
        fig_exist = True
        for gs in gns:
            figfile = os.path.join(figdir, f'orbdif_{crt_time.year}{crt_time.doy:0>3d}_{cen}_{gns_id(gs)}.png')
            if not os.path.isfile(figfile):
                fig_exist = False
                break
        if fig_exist:
            crt_time += 86400
            continue

        f_dif = os.path.join('orbdif', f'orbdif_{crt_time.year}{crt_time.doy:0>3d}_{cen}')
        if not os.path.isfile(f_dif):
            f_orb = f'orb_{crt_time.year}{crt_time.doy:0>3d}_{cen}'
            GrtSp3orb(config, f'sp3orb_{cen}').run()
            if not os.path.isfile(f_orb):
                crt_time += 86400
                continue
            GrtOrbdif(config, f'orbdif_{cen}', trans='NONE').run()

        data = read_orbdif(f_dif)
        if not data.empty:
            sats = list(set(data['sat']))
            setgns = set([s[0] for s in sats])
            gnss = [gns_name(s) for s in 'GECR' if s in setgns]
            for gs in gnss:
                data_temp = data[data.gns == gs]
                figfile1 = os.path.join(figdir, f'orbdif_{crt_time.year}{crt_time.doy:0>3d}_{cen}_{gns_id(gs)}.png')
                draw_orbdif(data_temp, figfile1, f'{gs} {str(crt_time)}~{str(end_time)} ({cen.upper()})')
        else:
            logging.warning(f'no data for {str(crt_time)}~{str(end_time)}, reference: {cen}')

        crt_time += 86400


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='monitor real-time precise clock flow')
    parser.add_argument('-cf', dest='cf', required=True, help='config file')
    parser.add_argument('-r', dest='use_rapid', action='store_true', help='use rapid products')
    args = parser.parse_args()
    cf_file = args.cf
    if not os.path.isfile(cf_file):
        logging.critical(f'config file not found {cf_file}')

    config = GnssConfig.from_file(cf_file)
    wkdir = config.workdir
    if not os.path.isdir(wkdir):
        logging.critical(f'workdir not found {wkdir}')
        raise SystemExit(1)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)8s: %(message)s')
    sns.set_context("paper", font_scale=1.7, rc={"lines.linewidth": 1.5})
    sns.set_style("whitegrid")
    sns.set_palette("deep")

    config.write(os.path.join(wkdir, 'cf_clk.ini'))
    os.chdir(wkdir)
    figdir = os.path.join(wkdir, 'figs')
    if not os.path.isdir(figdir):
        os.makedirs(figdir)

    # ----------------------- monitor memory usage ------------------------
    mpl.rcParams['agg.path.chunksize'] = 10000
    if os.path.isfile('pid'):
        pid = 0
        with open('pid') as f:
            for line in f:
                pid = int(line)
        file = f'{pid}_mem.log'
        with timeblock('Finished draw RAM usage'):
            data = read_memory(file)
            if not data.empty:
                figname = os.path.join(figdir, f'{pid}_mem.png')
                draw_memory(data, figname, f'PID {pid}')

    # ----------------------- monitor compute time ------------------------
    with timeblock('Finished draw compute time'):
        data = read_time_info('pcelsq.log')
        if not data.empty:
            figname = os.path.join(figdir, 'info_time.png')
            draw_time_info(data, figname)

    # ----------------------- monitor clock difference --------------------
    # cmd1 = ['clk01', 'clk93']
    # cmd2 = ['GE', 'GE']
    # if args.use_rapid:
    #     cmd1.extend(['gbm', 'cor', 'igc', 'cnt'])
    #     cmd2.extend(['GREC', 'GER', 'G', 'GREC'])
    cmd1 = ['gbm', 'cor']
    cmd2 = ['GREC', 'GER']
    gsys = config.gsys
    for i in range(len(cmd2)):
        cmd2[i] = ''.join([s for s in cmd2[i] if s in gsys])

    with timeblock('Finished draw clock difference'):
        with ThreadPoolExecutor(8) as pool:
            results = pool.map(monitor_clkdif, cmd1, cmd2)
    
    with timeblock('Finished draw orbit difference'):
        with ThreadPoolExecutor(8) as pool:
            results = pool.map(monitor_orbdif, cmd1, cmd2)

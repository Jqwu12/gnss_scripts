import os
import math
import shutil
import sys
import logging
from datetime import datetime
import argparse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import seaborn as sns
from funcs import GnssTime, sod2hms, gns_sat, gns_name, GnssConfig, GrtClkdif
from gnss_plot import read_clkdif


def read_time_info(file):
    try:
        with open(file) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        logging.warning(f"file not found {file}")
        return pd.DataFrame()

    data = []
    for line in lines:
        if len(line) != 148 or not line.startswith('Time for Processing epoch'):
            continue
        tt = GnssTime.from_str(line[27:46])
        hh, mm, ss = sod2hms(tt.sod)
        mss = int((tt.sod - int(tt.sod)) * 1000)
        crt_date = datetime(tt.year, tt.month, tt.day, hh, mm, ss, mss)
        data.append({
            'mjd': tt.fmjd, 'sod': tt.sod, 'date': crt_date, 'time': float(line[55:65]), 'nrec': int(line[92:95]),
            'nobs': int(line[115:123])
        })

    return pd.DataFrame(data)


def draw_time_info(data, figname, title=''):
    fig, ax = plt.subplots(3, 1, figsize=(8, 8), sharex='col', constrained_layout=True)

    ax[0].plot(data.date, data.nobs, '+', color='darkgreen')
    ax[0].set(ylim=(0, 6000), ylabel='Num of obs')
    if title:
        ax[0].set(title=title)

    ax[1].plot(data.date, data.nrec, '^', color='deeppink', alpha=0.5)
    ax[1].set(ylim=(0, 100), ylabel='Num of rec')

    ax[2].plot(data.date, data.time, 'v', color='darkblue', alpha=0.5)
    ax[2].hlines(5, data.date.min(), data.date.max(), colors='grey', linestyles='dashed', linewidth=4)
    ax[2].set(ylim=(0, 10), ylabel='Compute time [s]')

    plt.xticks(rotation=30)
    fig.savefig(figname, dpi=1200)


def read_memory(file):
    try:
        with open(file) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        logging.warning(f"file not found {file}")
        return

    data = []
    for line in lines:
        tt = GnssTime.from_str(line[0:19])
        val = int(line.split()[2]) / 1024
        data.append({'date': tt.datetime(), 'mem': val})

    return pd.DataFrame(data)


def draw_memory(data, figname, title=''):
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(data.date, data['mem'], 'o-')
    ax.set(ylabel='RAM usage [MB]', title=title)
    for tick in ax.get_xticklabels():
        tick.set_rotation(30)
    fig.savefig(figname, dpi=1200)


def get_clkdif_statistic(data, beg: datetime, end: datetime):
    data1 = data[(data.date >= beg) & (data.date < end)]
    if data1.empty:
        return pd.DataFrame()
    sats = list(set(data.sat))
    sat_sum = []
    sat_data = pd.DataFrame()
    for sat in sats:
        data2 = data1[data1.sat == sat]
        mval = data2.val.median()
        std = data2.val.std()
        data3 = data2[(data2.val < mval + 3 * std) & (data2.val > mval - 3 * std)]
        mval = data3.val.median()
        std = data3.val.std()
        data4 = data3[(data3.val < mval + 3 * std) & (data3.val > mval - 3 * std)]
        sat_sum.append({
            'sat': sat, 'mean': data4.val.mean(), 'std': data4.val.std(),
            'rms': math.sqrt(data4.val.dot(data4.val) / len(data4)), 'gsys': gns_name(sat[0])
        })
        sat_data = sat_data.append(data4)

    return sat_data, pd.DataFrame(sat_sum)


def draw_clkdif(data, gns: str, figname: str, title=''):
    nf = len(gns)
    fig, ax = plt.subplots(nf, 1, figsize=(8, 2 * nf + 2), sharex='col', constrained_layout=True)
    sats = set(data.sat)
    ymax = 10

    if nf > 1:
        for i in range(nf):
            gsys = gns[i]
            mid_val = 0
            for sat in gns_sat(gsys):
                if sat not in sats:
                    continue
                dd = data[data.sat == sat]
                mid_val = int(dd.val.median() / 5) * 5
                ax[i].plot(dd.date, dd.val, '+', label=sat)
            ax[i].set(ylim=(mid_val - ymax, mid_val + ymax), ylabel='Clock Diff [ns]')
            ax[i].text(0.1, 0.1, gns_name(gsys), size='large', weight='bold', transform=ax[i].transAxes)
        ax[0].set(title=title)
        for tick in ax[nf - 1].get_xticklabels():
            tick.set_rotation(30)
    else:
        gsys = gns[0]
        mid_val = 0
        for sat in gns_sat(gsys):
            if sat not in sats:
                continue
            dd = data[data.sat == sat]
            mid_val = int(dd.val.median() / 5) * 5
            ax.plot(dd.date, dd.val, '+', label=sat)
        ax.set(ylim=(mid_val - ymax, mid_val + ymax), ylabel='Clock Diff [ns]', title=title)
        ax.text(0.1, 0.1, gns_name(gsys), size='large', weight='bold', transform=ax.transAxes)
        for tick in ax.get_xticklabels():
            tick.set_rotation(30)

    fig.savefig(figname, dpi=1200)


def draw_clkdif_std(data, figname, title=''):
    gns = list(set(data.gsys))
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


def draw_boxplot(data, figname, title=''):
    sats = list(set(data['sat']))
    gns = list(set([gns_name(s[0]) for s in sats]))
    nf = len(gns)
    fig, ax = plt.subplots(nf, 1, figsize=(8, 2 * nf + 2), constrained_layout=False)
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


def monitor_clkdif(cen, gns: str):
    # run clkdif
    f_pce_xml = os.path.join(wkdir, 'xml', 'pcelsq.xml')
    ref_tree = ET.parse(f_pce_xml)
    beg = ref_tree.getroot().find('gen').find('beg')
    t_beg = GnssTime.from_str(beg.text)
    intv = int(ref_tree.getroot().find('gen').find('int').text)

    dend_time = datetime.utcnow()
    config = GnssConfig.from_file('cf_clk.ini')
    config.gsys = gns
    config.beg_time = t_beg
    config.end_time = GnssTime.from_datetime(dend_time)
    config.orb_ac = cen
    label = f'clkdif_{cen}'
    # GrtClkdif(config, label).run()

    # draw clkdif from the begining
    file = os.path.join('clkdif', f'clkdif_{t_beg.year}{t_beg.doy:0>3d}_{cen}')
    figname = os.path.join(figdir, f'clkdif_{t_beg.year}{t_beg.doy:0>3d}_{cen}_all.png')
    data = read_clkdif(file, t_beg)
    # if not data.empty:
    #     draw_clkdif(data, gns, figname, f'{str(t_beg)}~{str(config.end_time)}')

    # draw clkdif statistics
    crt_time = GnssTime(t_beg.mjd + 1, 0)
    while crt_time < config.end_time:
        end_time = GnssTime(crt_time.mjd, 86400 - intv)
        data0, data1 = get_clkdif_statistic(data, crt_time.datetime(), end_time.datetime())
        figname1 = os.path.join(figdir, f'clkstd_{crt_time.year}{crt_time.doy:0>3d}_{cen}.png')
        figname2 = os.path.join(figdir, f'boxplot_{crt_time.year}{crt_time.doy:0>3d}_{cen}.png')
        if not data1.empty and not os.path.isfile(figname1):
            draw_clkdif_std(data1, figname1, f'{str(crt_time)}~{str(end_time)}')
        if not data0.empty and not os.path.isfile(figname2):
            draw_boxplot(data0, figname2, f'{str(crt_time)}~{str(end_time)}')
        crt_time += 86400


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='monitor real-time precise clock flow')
    parser.add_argument('-cf', dest='cf', required=True, help='config file')
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
    if os.path.isfile('pid'):
        pid = 0
        with open('pid') as f:
            for line in f:
                pid = int(line)
        file = f'{pid}_mem.log'
        data = read_memory(file)
        if not data.empty:
            figname = os.path.join(figdir, f'{pid}_mem.png')
            draw_memory(data, figname, f'PID {pid}')

    # ----------------------- monitor compute time ------------------------
    data = read_time_info('info_time.log')
    if not data.empty:
        figname = os.path.join(figdir, 'info_time.png')
        draw_time_info(data, figname)

    # run clkdif, multi-thread
    cmd1 = ['clk01', 'clk93', 'gbm']
    cmd2 = ['GE', 'GE', 'GREC']
    with ThreadPoolExecutor(8) as pool:
        results = pool.map(monitor_clkdif, cmd1, cmd2)

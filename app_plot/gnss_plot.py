import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
import logging
from datetime import datetime
import matplotlib.dates as mdates
from typing import List
from funcs.gnss_files import read_sp3_file
from funcs.gnss_time import GnssTime, sod2hms, mjd2ymd
from funcs.coordinate import ell2cart, cart2ell
from funcs.constants import gns_name, gns_sat


def isfloat(value):
    """ To check if any variable can be converted to float or not """
    try:
        float(value)
        return True
    except ValueError:
        return False


def isint(value):
    """ To check if any variable can be converted to integer """
    try:
        int(value)
        return True
    except ValueError:
        return False


def read_atxpcv(catx, f_atx):
    with open(f_atx) as file_object:
        lines = file_object.readlines()

    isfound = False
    ibeg = 0;
    iend = 0;
    j = 0
    for i in range(len(lines)):
        if lines[i].find('START OF ANTENNA') == 60:
            ibeg = i
            for j in range(i + 1, len(lines)):
                if lines[j].find('TYPE / SERIAL NO') == 60:
                    anttype = lines[j][0:13]
                    if anttype.strip() == catx:
                        isfound = True
                if lines[j].find('END OF ANTENNA') == 60:
                    break
            iend = j
            if isfound:
                break

    if not isfound:
        msg = f"ATX {catx} not found in {f_atx.rstrip()}!"
        print(msg)
        return

    dazi = 0;
    dzen = 0;
    zen1 = 0;
    zen2 = 0
    for i in range(ibeg, iend):
        if lines[i][0] == '#':
            continue
        if lines[i].find('DAZI') == 60:
            dazi = float(lines[i][0:8])
        if lines[i].find('ZEN1 / ZEN2 / DZEN') == 60:
            zen1 = float(lines[i][0:8])
            zen2 = float(lines[i][8:14])
            dzen = float(lines[i][14:20])

    if dazi == 0 or dzen == 0:
        return

    nazi = int(360 / dazi) + 1
    nzen = int((zen2 - zen1) / dzen) + 1
    dpcv = np.zeros((nazi, nzen), dtype=float)

    isfound = False
    for i in range(ibeg, iend):
        if lines[i].find('NOAZI') == 3:
            isfound = True
            continue
        if not isfound:
            continue
        if lines[i].find('END OF FREQUENCY') == 60:
            break
        azi = float(lines[i][0:8])
        azi = 90 - azi
        if azi < 0:
            azi = azi + 360
        row = int(azi / dazi)
        if row >= nazi:
            continue
        for j in range(nzen):  # 天顶角 -> 高度角
            dpcv[row][nzen - j - 1] = float(lines[i][8 + j * 8:16 + j * 8])

    return dpcv


def read_enu(f_enu):
    try:
        with open(f_enu) as f:
            lines = f.readlines()
    except FileNotFoundError:
        logging.error(f"file not found {f_enu}")
        return

    data = []
    for line in lines:
        info = line.split()
        if len(info) == 4:
            if info[0] == "RMS":
                break
            sod = float(info[0])
            de = float(info[1])
            dn = float(info[2])
            du = float(info[3])
            data.append({"sod": sod, "de": de, "dn": dn, "du": du})

    return pd.DataFrame(data)


def dxyz2enu(ell: List[float], dxyz: List[float]):
    sinPhi = math.sin(ell[0])
    cosPhi = math.cos(ell[0])
    sinLam = math.sin(ell[1])
    cosLam = math.cos(ell[1])

    n = -sinPhi * cosLam * dxyz[0] - sinPhi * sinLam * dxyz[1] + cosPhi * dxyz[2]
    e = -sinLam * dxyz[0] + cosLam * dxyz[1]
    u = cosPhi * cosLam * dxyz[0] + cosPhi * sinLam * dxyz[1] + sinPhi * dxyz[2]

    return e, n, u


def read_enu_kin(f_enu, xyz: List[float]):
    try:
        with open(f_enu) as f:
            lines = f.readlines()
    except FileNotFoundError:
        logging.error(f"{f_enu} not found")
        return

    if not xyz or len(xyz) < 3:
        return

    b, l, h = cart2ell(xyz[0], xyz[1], xyz[2], 'WGS84')
    ell = [math.radians(b), math.radians(l), h]

    data = []
    for line in lines:
        info = line.split()
        if len(info) == 7:
            mjd = float(info[1])
            sod = float(info[2])
            x = float(info[3])
            y = float(info[4])
            z = float(info[5])
            dxyz = [x - xyz[0], y - xyz[1], z - xyz[2]]
            de, dn, du = dxyz2enu(ell, dxyz)
            data.append({"mjd": mjd, "sod": sod, "de": de, "dn": dn, "du": du})

    return pd.DataFrame(data)


def read_orbdif_old(sats_in, f_name):
    """read the panda orbdif file"""
    sats = []
    str_rms = ''
    try:
        with open(f_name) as file_object:
            for line in file_object:
                if line.find('SAT') >= 0:
                    sats = line[27:].replace('\n', '').split('               ')
                if line.find('FITRMS') == 0:
                    str_rms = line[19:].replace('\n', '')

        nsats = len(sats)
    except FileNotFoundError:
        msg = "Error, the file " + f_name + " does not exist"
        print(msg)
        return pd.DataFrame()

    orbdif = []
    for i in range(nsats):
        str_a = str_rms[i * 18:i * 18 + 6].strip()
        str_c = str_rms[i * 18 + 7:i * 18 + 12].strip()
        str_r = str_rms[i * 18 + 13:i * 18 + 18].strip()
        if str_a.isnumeric() and str_c.isnumeric() and str_r.isnumeric():
            rms_a_value = int(str_a) / 10  # unit: cm
            rms_c_value = int(str_c) / 10
            rms_r_value = int(str_r) / 10
            rms_3d_value = np.sqrt(rms_a_value ** 2 + rms_c_value ** 2 + rms_r_value ** 2)
            rms_1d_value = rms_3d_value / np.sqrt(3)
            if not sats[i] in sats_in:
                continue
            new_rec = {'sat': sats[i], 'rms_a': rms_a_value, 'rms_c': rms_c_value,
                       'rms_r': rms_r_value, 'rms_3d': rms_3d_value, 'rms_1d': rms_1d_value}
            orbdif.append(new_rec)

    orbdif_pd = pd.DataFrame(orbdif)

    return orbdif_pd


def read_orbdif_series(sats_in, f_name, beg_fmjd, seslen=86400):
    """read the orbdif series from panda orbdif file"""
    orbdif = {}
    try:
        with open(f_name) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        msg = "Error, the file " + f_name + " does not exist"
        print(msg)
        return orbdif

    sats = []
    for line in lines:
        if line.find('SAT') >= 0:
            sats = line[27:].replace('\n', '').split('               ')
            break

    if len(sats_in) == 0:
        msg = 'The input satellite list is empty!'
        print(msg)
    if len(sats) == 0:
        msg = 'No satellite in file!'
        print(msg)

    for sat in sats_in:
        if sat in sats:
            isat = sats.index(sat)
        else:
            msg = 'Cannot find the records for ' + sat
            print(msg)
            continue

        orbdif_sat = []
        for line in lines:
            if line.find('ACR') != 0:
                continue
            mjd = int(line[4:9])
            sod = float(line[10:19])
            sec = (mjd + sod / 86400.0 - beg_fmjd) * 86400
            if sec < 0:
                continue
            elif sec > seslen:
                break
            str_rms = line[19:].replace('\n', '')
            if '*' in str_rms:
                continue
            rms_a_value = int(str_rms[isat * 18:isat * 18 + 6].lstrip()) / 10  # unit: cm
            rms_c_value = int(str_rms[isat * 18 + 7:isat * 18 + 12].lstrip()) / 10
            rms_r_value = int(str_rms[isat * 18 + 13:isat * 18 + 18].lstrip()) / 10
            rms_3d_value = math.sqrt(rms_a_value ** 2 + rms_c_value ** 2 + rms_r_value ** 2)
            rms_1d_value = rms_3d_value / math.sqrt(3)
            if rms_1d_value > 30:
                continue

            new_rec = {'sec': sec, 'rms_a': rms_a_value, 'rms_c': rms_c_value,
                       'rms_r': rms_r_value, 'rms_3d': rms_3d_value, 'rms_1d': rms_1d_value}
            orbdif_sat.append(new_rec)
        orbdif_sat_pd = pd.DataFrame(orbdif_sat)
        orbdif[sat] = orbdif_sat_pd

    return orbdif


def read_orbdif(file):
    try:
        with open(file) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        logging.warning(f"file not found {file}")
        return pd.DataFrame()

    sats = []
    data = []
    for line in lines:
        if line[16:19] == "SAT":
            sats = line[20:].split()
            continue
        if line[0:3] == "ACR" and sats:
            mjd = int(line[4:9])
            sod = float(line[10:19])
            tt = GnssTime(mjd, sod)
            td = tt.datetime()

            for isat in range(len(sats)):
                str_rms = line[20 + isat * 18: 37 + isat * 18]
                vals = str_rms.split()  # unit: mm
                if len(str_rms) != 17 or '*' in str_rms or len(vals) != 3:
                    continue
                da, dc, dr = [int(s) for s in vals]
                d_3d = math.sqrt(da ** 2 + dc ** 2 + dr ** 2)
                d_1d = d_3d / math.sqrt(3)
                data.append({
                    'date': td, 'sat': sats[isat], 'gns': gns_name(sats[isat][0]), 'da': da, 'dc': dc, 'dr': dr,
                    '3d': d_3d, '1d': d_1d
                })

    return pd.DataFrame(data)


def draw_orbdif(data, figname: str, title=''):
    sats = list(set(data['sat']))
    sats.sort()
    subs = ['da', 'dc', 'dr', '3d']
    ylabels = ['Along [cm]', 'Cross [cm]', 'Radial [cm]', '3D [cm]']
    nf = len(subs)
    fig, ax = plt.subplots(nf, 1, figsize=(8, 2 * nf + 2), sharex='col', constrained_layout=True)
    ymax = 50

    markers = ['.', '1', '2', '+']
    for i in range(nf):
        j = 0
        for sat in sats:
            dd = data[data.sat == sat]
            ax[i].plot(dd.date, dd[subs[i]] / 10, markers[int(j / 8)], label=sat)
            j += 1
        if subs[i] == '3d' or subs[i] == '1d':
            ax[i].set(ylim=(0, 2 * ymax), ylabel=ylabels[i])
        else:
            ax[i].set(ylim=(-1 * ymax, ymax), ylabel=ylabels[i])
    ax[nf - 1].legend(loc='upper left', ncol=12, fontsize=9, columnspacing=0.3, handletextpad=0.05)
    ax[0].set(title=title)
    for tick in ax[nf - 1].get_xticklabels():
        tick.set_rotation(30)

    fig.savefig(figname, dpi=1200)
    logging.info(f'save figure {figname}')
    plt.close()


def read_clkdif(f_name, beg_time=None, ref_sat=None):
    if ref_sat is None:
        ref_sat = ""
    try:
        with open(f_name) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        logging.warning(f"file not found {f_name}")
        return pd.DataFrame()

    sats = []
    data = []
    isfirst = True
    for line in lines:
        if line.startswith('---') or line.startswith('MEAN'):
            break
        if line.startswith('  MJD       SOD'):
            sats = line[15:].replace('\n', '').split()
            continue
        if not sats or len(line) < len(sats) * 9 + 15:
            continue
        mjd = int(line[0:5])
        sod = int(line[5:15].replace('*', ''))
        if isfirst and beg_time is None:
            beg_time = GnssTime(mjd, sod)
            isfirst = False

        crt_time = GnssTime(mjd, sod)
        if crt_time < beg_time:
            continue
        hh, mm, ss = sod2hms(crt_time.sod)
        mss = int((crt_time.sod - int(crt_time.sod)) * 1000)
        crt_date = datetime(crt_time.year, crt_time.month, crt_time.day, hh, mm, ss, mss)
        info = line[15:].split()
        for i in range(len(sats)):
            if i > len(info) or '*' in info[i] or sats[i] == ref_sat:
                continue
            difval = float(info[i])
            if abs(difval) > 100:
                continue
            data.append(
                {'mjd': mjd, 'sod': sod, 'sec': (mjd - beg_time.mjd) * 86400 + sod - beg_time.sod, 'date': crt_date,
                 'sat': sats[i], 'val': float(info[i])})

    return pd.DataFrame(data)


def get_orbdif_days(sats_in, f_list, doys):
    """get the RMS values orbit difference for each day"""
    orbdif_days = []
    for i in range(len(doys)):
        doy = doys[i]
        f_name = f_list[i]
        orbdif = read_orbdif(sats_in, f_name)
        if orbdif.empty:
            continue

        orbdif_day = {'doy': doy,
                      'rms_a': orbdif.rms_a.mean(),
                      'rms_c': orbdif.rms_c.mean(),
                      'rms_r': orbdif.rms_r.mean(),
                      'rms_3d': orbdif.rms_3d.mean(),
                      'rms_1d': orbdif.rms_1d.mean()}
        orbdif_days.append(orbdif_day)

    orbdif_days_pd = pd.DataFrame(orbdif_days)
    return orbdif_days_pd


def draw_clkdif_sats(dif1, dif2, lab1, lab2, ymax=0.5, save_file='',
                     fig_title='Clock Difference', fig_type='bar'):
    """draw the STD value of clock difference for each satellite"""
    if dif1.empty or dif2.empty:
        msg = "Error, the imput DataFrame is empty!"
        print(msg)
        return

    step = math.ceil(len(dif1.index) / 15)
    sat_idx = range(0, len(dif1.index), step)
    sat_lab = dif1['sat'][::step]

    fig, ax = plt.subplots(figsize=(7.2, 3.0))

    bar_width = 0.3
    if fig_type == 'plot':
        ax.plot(dif1['s'], 'o', label=lab1)
        ax.plot(dif2['s'], 'o', label=lab2)
    elif fig_type == 'bar':
        ax.bar(np.arange(len(dif1)) - bar_width / 2, dif1['s'],
               width=bar_width, label=lab1)
        ax.bar(np.arange(len(dif1)) + bar_width / 2, dif2['s'],
               width=bar_width, label=lab2)
    else:
        msg = 'Error, unkown fig type' + fig_type
        print(msg)
        return

    ax.set(xticks=sat_idx, xticklabels=sat_lab, ylim=(0, ymax))
    ax.set(xlabel='PRN', ylabel='Standard deviation [ns]', title=fig_title)
    ax.legend()

    ax.text(0, ymax * 0.8, 'mean STD (%s): %4.3f ns' % (lab1, dif1.mean()))
    ax.text(0, ymax * 0.7, 'mean STD (%s): %4.3f ns' % (lab2, dif2.mean()))

    if len(save_file) > 0:
        fig.savefig(save_file)


def draw_orbdif_sats(dif1, dif2, lab1, lab2, ymax=10, save_file='',
                     fig_title='Orbit Difference', fig_type='plot'):
    """draw the RMS value of orbit difference for each satellite"""
    if dif1.empty or dif2.empty:
        msg = "Error, the imput DataFrame is empty!"
        print(msg)
        return

    step = math.ceil(len(dif1.index) / 15)
    sat_idx = range(0, len(dif1.index), step)
    sat_lab = dif1['sat'][::step]

    fig, ax = plt.subplots(4, 1, sharex='col', figsize=(7.2, 5.4))
    bar_width = 0.3

    for i in range(4):
        if fig_type == 'plot':
            ax[i].plot(dif1.iloc[:, i + 1], 'o', label=lab1)
            ax[i].plot(dif2.iloc[:, i + 1], 'o', label=lab2)
        elif fig_type == 'bar':
            ax[i].bar(np.arange(len(dif1)) - bar_width / 2, dif1.iloc[:, i + 1],
                      width=bar_width, label=lab1)
            ax[i].bar(np.arange(len(dif2)) + bar_width / 2, dif2.iloc[:, i + 1],
                      width=bar_width, label=lab2)
        else:
            msg = 'Error, unkown fig type' + fig_type
            print(msg)
            return

        ax[i].set(xticks=sat_idx, xticklabels=sat_lab, ylim=(0, ymax))

    ax[0].set(ylabel='Along [cm]', title=fig_title)
    ax[1].set(ylabel='Cross [cm]')
    ax[2].set(ylabel='Radial [cm]')
    ax[0].legend(loc='best', framealpha=1, ncol=3)
    ax[3].set(ylabel='3 D [cm]', xlabel='PRN')

    if len(save_file) > 0:
        fig.savefig(save_file)


def draw_orbdif_days(dif1, dif2, lab1, lab2, ymax=10, save_file='',
                     fig_title='Orbit Difference', fig_type='bar'):
    """draw the RMS value of orbit difference for each day"""
    if dif1.empty or dif2.empty:
        msg = "Error, the imput DataFrame is empty!"
        print(msg)
        return

    # step = math.ceil(len(dif1.index)/15)
    # doy_idx = range(0,len(dif1.index),step)
    # doy_lab = dif1['doy'][::step]

    fig, ax = plt.subplots(4, 1, sharex='col', figsize=(10, 6))
    bar_width = 0.3

    for i in range(4):
        if fig_type == 'plot':
            ax[i].plot(dif1['doy'], dif1.iloc[:, i + 1], 's', markersize=6, label=lab1)
            ax[i].plot(dif2['doy'], dif2.iloc[:, i + 1], 'o', markersize=6, label=lab2)
        elif fig_type == 'bar':
            ax[i].bar(dif1['doy'] - bar_width / 2, dif1.iloc[:, i + 1],
                      width=bar_width, label=lab1)
            ax[i].bar(dif1['doy'] + bar_width / 2, dif2.iloc[:, i + 1],
                      width=bar_width, label=lab2)
        else:
            msg = 'Error, unkown fig type' + fig_type
            print(msg)
            return

        # ax[i].set(xticks = doy_idx, xticklabels = doy_lab, ylim = (0, ymax))
        ax[i].set(ylim=(0, ymax))

    ax[0].set(ylabel='Along [cm]', title=fig_title)
    ax[1].set(ylabel='Cross [cm]')
    ax[2].set(ylabel='Radial [cm]')
    ax[0].legend(loc='best', framealpha=1, ncol=3)
    ax[3].set(ylabel='3 D [cm]', xlabel='Day of Year')

    if len(save_file) > 0:
        fig.savefig(save_file)
    return


def draw_orbdif_series(difs=[], labs=[],
                       ymax=10, save_file='', fig_title='Orbit Difference'):
    """draw the time series of orbit difference for one satellite"""
    if len(difs) == 0:
        msg = "Error, the imput orbdif list is empty!"
    for dif in difs:
        if dif.empty:
            msg = "Error, the imput DataFrame is empty!"
            print(msg)
            return

    fig, ax = plt.subplots(3, 1, sharex='col', figsize=(15, 6))
    for i in range(3):
        for j in range(len(difs)):
            ax[i].plot(difs[j]['sec'] / 3600.0, difs[j].iloc[:, i + 1], '.', label=labs[j])
        ax[i].set(ylim=(-1 * ymax, ymax))
        ax[i].grid(True)

    ax[0].set(ylabel='Along [cm]', title=fig_title)
    if len(labs) > 0:
        ax[0].legend(ncol=len(labs))
    ax[1].set(ylabel='Cross [cm]')
    ax[2].set(ylabel='Radial [cm]', xlabel='Hour')

    plt.show()
    if len(save_file) > 0:
        fig.savefig(save_file)


def draw_clkdif_series(difs=[], labs=[],
                       ymax=1.0, save_file='', fig_title='Clock Difference'):
    """draw the time series of clock difference for one satellite"""
    if len(difs) == 0:
        msg = "Error, the imput orbdif list is empty!"
    for dif in difs:
        if dif.empty:
            msg = "Error, the imput DataFrame is empty!"
            print(msg)
            return

    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for j in range(len(difs)):
        ax.plot(difs[j]['sec'] / 3600.0, difs[j]['res'], '-o', label=labs[j])
        ax.set(ylim=(-1 * ymax, ymax))
        ax.grid(True)

    ax.set(ylabel='Clock Difference [ns]', xlabel='Hour', title=fig_title)
    if len(labs) > 0:
        ax.legend(ncol=len(labs))

    plt.show()
    if len(save_file) > 0:
        fig.savefig(save_file)


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
    plt.close()


def read_orbsum(f_name, labels, year, tbeg, seslen, ymax=5):
    try:
        with open(f_name) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        msg = "Error, the file " + f_name + " does not exist"
        print(msg)
        return

    if len(labels) == 0:
        msg = 'The input schemes are empty!'
        return
    ibeg = 0
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        if line.find('--------') == 0:
            ibeg = i
            break
    del lines[0:ibeg + 1]  # only the last set of results are used

    orbdifs_all = {}
    for lab in labels:
        orbdifs = []
        for line in lines:
            if line.find(str(year)) != 0:
                continue
            info = line.replace('\n', '').split()
            doy = int(info[1])
            if doy < tbeg or doy > tbeg + seslen:
                continue
            i = 2
            pattern = '(' + lab + ')'
            while (i <= len(info) - 4):
                if info[i] != pattern:
                    i = i + 5
                    continue
                if info[i + 1].isnumeric() and info[i + 2].isnumeric() and info[i + 3].isnumeric():
                    da = int(info[i + 1]) / 10  # units:cm
                    dc = int(info[i + 2]) / 10
                    dr = int(info[i + 3]) / 10
                    d3 = math.sqrt(da ** 2 + dc ** 2 + dr ** 2)
                    d1 = d3 / math.sqrt(3)
                    if d3 < ymax:
                        orbdif = {'doy': doy, 'rms_a': da, 'rms_c': dc,
                                  'rms_r': dr, 'rms_3d': d3, 'rms_1d': d1}
                        orbdifs.append(orbdif)
                    else:
                        msg = "RMS value too large: {:0>3d} {:.2f}".format(doy, d3)
                        # print(msg)
                i = i + 5

        if len(orbdifs) > 0:
            orbdifs_pd = pd.DataFrame(orbdifs)
            orbdifs_all[lab] = orbdifs_pd

    return orbdifs_all


def read_slromc(f_name, sat, tbeg, seslen):
    """read the PANDA slromcs"""
    try:
        with open(f_name) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        msg = "Error, the file " + f_name + " does not exist"
        print(msg)
        return

    slromc = []
    for line in lines:
        if line.find('OMCSLR') != 0:
            continue
        info = line.replace('\n', '').split()
        mjd = int(info[1])
        sod = float(info[2])
        site_id = info[3]
        # site_name = info[4]
        sat_name = info[5]
        if sat_name != sat:
            continue
        omc = float(info[6])
        if abs(omc) > 0.2:
            continue
        if site_id == '8834' and abs(omc) > 0.1:
            continue
        if mjd < tbeg or mjd > tbeg + seslen:
            continue
        fmjd = mjd + sod / 86400.0
        omc_rec = {'mjd': fmjd, 'site': site_id, 'omc': omc}
        slromc.append(omc_rec)

    return pd.DataFrame(slromc)


def draw_slromc_site(omc1, omc2, labs, exc_sites="", save_file=""):
    slr_std1 = []
    for key, value in omc1.items():
        if key in exc_sites:
            continue
        std_rec = {'site': key, 'np': len(value), 'std': value['omc'].std()}
        slr_std1.append(std_rec)

    slr_std2 = []
    for key, value in omc2.items():
        if key in exc_sites:
            continue
        std_rec = {'site': key, 'np': len(value), 'std': value['omc'].std()}
        slr_std2.append(std_rec)

    slr_std_pd1 = pd.DataFrame(slr_std1)
    slr_std_pd2 = pd.DataFrame(slr_std2)

    bar_width = 0.37
    fig, ax = plt.subplots(figsize=(10, 4))

    ax2 = ax.twinx()
    ax2.plot(slr_std_pd1['np'], '--o')
    ax2.plot(slr_std_pd2['np'], '--o', color='dimgray', label='$N_{p}$')
    ax2.set(ylabel='Number of points', ylim=(0, 8000))
    ax2.legend(loc='upper left', frameon=False)
    ax.bar(np.arange(len(slr_std_pd1)) - bar_width / 2, slr_std_pd1['std'],
           width=bar_width, label=labs[0])
    ax.bar(np.arange(len(slr_std_pd1)) + bar_width / 2, slr_std_pd2['std'],
           width=bar_width, label=labs[1])
    ax.set(xticks=np.arange(len(slr_std_pd1)),
           xticklabels=slr_std_pd1['site'],
           xlabel='ILRS sites', ylabel='STD of SLR residuals [m]',
           ylim=(0, 0.04))
    fig.autofmt_xdate()
    ax.grid()
    ax.legend(frameon=False)

    if (len(save_file) > 0):
        fig.savefig(save_file)


def draw_slromc_points(omc1, omc2, labs="", exc_sites="", save_file=""):
    omc_p1 = [];
    doy_p1 = []
    for key, value in omc1.items():
        if key in exc_sites:
            continue
        for i in range(len(value)):
            doy_p1.append(value['doy'][i])
            omc_p1.append(value['omc'][i])

    omc_p2 = [];
    doy_p2 = []
    for key, value in omc2.items():
        if key in exc_sites:
            continue
        for i in range(len(value)):
            doy_p2.append(value['doy'][i])
            omc_p2.append(value['omc'][i])

    omc_rec1 = {'doy': doy_p1, 'omc': omc_p1}
    omc_pd1 = pd.DataFrame(omc_rec1)
    omc_rec2 = {'doy': doy_p2, 'omc': omc_p2}
    omc_pd2 = pd.DataFrame(omc_rec2)
    mm1 = omc_pd1['omc'].mean() * 1000
    mm2 = omc_pd2['omc'].mean() * 1000
    std1 = omc_pd1['omc'].std() * 1000
    std2 = omc_pd2['omc'].std() * 1000
    lab1 = f"{labs[0]}: {mm1:5.2f}" + r"$\pm$" + f"{std1:5.2f} mm"
    lab2 = f"{labs[1]}: {mm2:5.2f}" + r"$\pm$" + f"{std2:5.2f} mm"

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(omc_pd1['doy'], omc_pd1['omc'], 'o',
            markersize=6, markeredgewidth=2, markerfacecolor='none', label=lab1)
    ax.plot(omc_pd2['doy'], omc_pd2['omc'], 'o',
            markersize=6, markeredgewidth=2, markerfacecolor='none', label=lab2)
    ax.legend(frameon=True)
    ax.set(ylim=(-0.2, 0.2))
    ax.grid()
    ax.set(xlabel='Day of year', ylabel='SLR residuals [m]')
    if (len(save_file) > 0):
        fig.savefig(save_file)


# Residuals analysis
def read_residuals_sum(sats_in, f_name, intv=300, sites_in=[]):
    """"Read phase residuals from Panda sum file"""
    res_all = {}
    if len(sats_in) == 0:
        msg = 'The input satellite list is empty!'
        print(msg)
        return res_all

    try:
        with open(f_name) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        msg = "Error, the file " + f_name + " does not exist"
        print(msg)
        return res_all

    # get the satellites and sites in sum file
    iflag = 0
    sites = []
    sats = []
    for line in lines:
        if line.find('NAME') == 1:
            if iflag == 0:
                sats = line[15:].replace('\n', '').split()
                iflag = 1
                continue
            else:
                break
        if iflag == 1:
            sites.append(line[1:5])

    if 'SUMM' in sites:
        sites.remove('SUMM')
    if len(sats) <= 0:
        msg = 'No satellite in file!'
        print(msg)
        return res_all
    if len(sites) <= 0:
        msg = 'No station in file!'
        print(msg)
        return res_all

    # get the number of epochs
    iflag = 0
    nepo = 0
    for line in lines:
        if line.find('EPOCH') == 1:
            if iflag == 0:
                iflag = 1
                continue
            else:
                break
        if iflag == 1:
            nepo = int(line[0:9])

    if nepo <= 0:
        msg = 'No epochs in file!'
        print(msg)
        return res_all

    ipt0 = 0
    for i in range(len(lines)):
        if lines[i].find('Residual of every satellite for each station') >= 0:
            ipt0 = i
            break

    if ipt0 == 0:
        msg = 'Cannot find Residual of every satellite for each station!'
        print(msg)
        return res_all

    for isite in range(len(sites)):
        if len(sites_in) > 0:
            if not sites[isite] in sites_in:
                continue

        ipt1 = ipt0 + 1 + isite * 290
        ipt2 = ipt1 + 289
        if ipt2 > len(lines):
            break
        site_name = lines[ipt1][4:8]
        if not site_name in sites:
            msg = 'Wrong station: ' + site_name
            print(msg)
            continue
        res_site = []
        for i in range(ipt1 + 1, ipt2):
            new_rec = {}
            iepo = int(lines[i][0:8])
            sec = (iepo - 1) * intv
            new_rec = {'sec': sec}
            for isat in range(len(sats)):
                if not sats[isat] in sats_in:
                    continue
                res_rec = lines[i][8 * isat + 8:8 * isat + 13].lstrip()
                if len(res_rec) <= 0:
                    continue
                if res_rec.find('*') >= 0:
                    continue
                new_rec[sats[isat]] = int(res_rec)
            res_site.append(new_rec)

        res_site_pd = pd.DataFrame(res_site)
        res_all[sites[isite]] = res_site_pd

    return res_all


def read_residuals(f_name):
    with open(f_name) as file_object:
        lines = file_object.readlines()

    ## read resfile header
    mjd0 = 0;
    intv = 0;
    sod0 = 0
    sats = [];
    sites = []
    for line in lines:
        if line.find('Time&Interval') == 0:
            info = line[15:52].split()
            mjd0 = int(info[0])
            sod0 = float(info[1])
            intv = float(info[2])
            intv = int(intv)  ## int
        elif line.find('Sigma') == 0:
            sig = float(line[7:20])
            if sig > 10:
                msg = f"Sigma too large: {sig:10.4f}"
                print(msg)
        elif line.find('SAT:') == 0:
            info = line[4:].replace('\n', '').split()
            sats = sats + info
        elif line.find('STA:') == 0:
            info = line[4:].replace('\n', '').split()
            sites = sites + info
        elif line.find('RES') == 0:
            break

    if mjd0 * intv * len(sats) * len(sites) == 0:
        msg = 'Reading resfile header error!'
        print(msg)
        return

    ## read resfile records
    ## cfmtres1='(a,i8,2i5,i3,2f8.3,9(f12.3,d14.6))'
    data = []
    for line in lines:
        if line.find('RES') != 0:
            continue
        rec_dic = {}
        nepo = int(line[3:11])
        rec_dic['mjd'] = mjd0 + (sod0 + (nepo - 1) * intv) / 86400.0
        rec_dic['sec'] = (nepo - 1) * intv
        isite = int(line[11:16]) - 1
        isat = int(line[16:21]) - 1
        if isite >= len(sites) or isat >= len(sats):
            continue
        rec_dic['site'] = sites[isite]
        rec_dic['sat'] = sats[isat]
        rec_dic['azim'] = float(line[24:32])
        rec_dic['elev'] = float(line[32:40])
        rec_dic['pres'] = float(line[40:52])
        rec_dic['cres'] = float(line[66:78])
        data.append(rec_dic)

    return pd.DataFrame(data)


def draw_residuals(res, sats_in=[], sites_in=[], ymax=10, fig_type='sat', save_file=''):
    """"draw the phase residuals for each satellite or station"""
    if len(res) == 0:
        msg = "Error, the imput list is empty!"
        print(msg)
        return
    if fig_type != 'sat' and fig_type != 'sta':
        msg = "Error, unkown fig type " + fig_type + ' !'
        print(msg)
        return
    if len(sats_in) == 0 or len(sites_in) == 0:
        msg = "Error, the imput sat list or site list is empty!"
        print(msg)
        return


def read_ressum(f_name, labels, year, tbeg, seslen, ymax=15):
    try:
        with open(f_name) as file_object:
            lines = file_object.readlines()
    except FileNotFoundError:
        msg = "Error, the file " + f_name + " does not exist"
        print(msg)
        return

    if len(labels) == 0:
        msg = 'The input schemes are empty!'
        return

    lcres_all = {}
    for lab in labels:
        lcres = []
        for line in lines:
            if line.find(str(year)) != 0:
                continue
            info = line.replace('\n', '').split()
            doy = int(info[1])
            if doy < tbeg or doy > tbeg + seslen:
                continue
            i = 2
            pattern = '(' + lab + ')'
            while (i <= len(info) - 1):
                if info[i] != pattern:
                    i = i + 2
                    continue
                if not '*' in info[i + 1] and not info[i + 1].isalpha():
                    rec = float(info[i + 1])
                    if rec < ymax:
                        rr = {'doy': doy, 'res': rec}
                        lcres.append(rr)
                    else:
                        msg = f"LC res too large: {doy:0>3d} {rec:6.2f}"
                        # print(msg)
                i = i + 2

        if len(lcres) > 0:
            lcres_pd = pd.DataFrame(lcres)
            lcres_all[lab] = lcres_pd

    return lcres_all


def read_daily_upd(files: dict):
    upd_first = {}
    data = []
    for mjd, file in files.items():
        try:
            with open(file) as f:
                lines = f.readlines()
        except FileNotFoundError:
            logging.warning(f"file not found {file}")
            continue

        year, mon, day = mjd2ymd(mjd)
        cal_time = datetime(year, mon, day)
        data_tmp = {}
        for line in lines:
            if not line.startswith(' '):
                continue
            sat, val, sig, nobs, *_ = line.split()
            data_tmp[sat] = [float(val), float(sig), int(nobs)]

        ref_val = {"G": 0, "R": 0, "E": 0, "C": 0}
        ref_sats = {
            "G": ["G01", "G05", "G06", "G08", "G30"],
            "R": ["R01", "R02", "R03", "R04"],
            "E": ["E01", "E02", "E03", "E04"],
            "C": ["C21", "C22", "C23", "C24", "C08"]
        }
        for sys, sats in ref_sats.items():
            for sat in sats:
                if sat in data_tmp.keys():
                    ref_val[sys] = data_tmp[sat][0]
                    break
            if ref_val[sys] == 0:
                for sat, vals in data_tmp.items():
                    if sys == sat[0]:
                        ref_val[sys] = vals[0]
                        break

        for sat, vals in data_tmp.items():
            vals[0] -= ref_val[sat[0]]
            if not sat in upd_first:
                if vals[0] > 0.5:
                    vals[0] -= 1
                elif vals[0] <= -0.5:
                    vals[0] += 1
                upd_first[sat] = vals[0]
            else:
                if vals[0] > upd_first[sat] + 0.5:
                    vals[0] -= 1
                elif vals[0] < upd_first[sat] - 0.5:
                    vals[0] += 1
            data.append({
                'date': cal_time, 'sat': sat, 'upd': vals[0], 'sig': vals[1],
                'nobs': vals[2], 'sys': gns_name(sat[0])
            })

    return pd.DataFrame(data)


def read_epo_upd(file):
    try:
        with open(file) as f:
            lines = f.readlines()
    except FileNotFoundError:
        logging.warning(f"file not found {file}")
        return pd.DataFrame()

    cal_time = datetime(1970, 1, 1)
    data = []
    for line in lines:
        if not line.startswith(' '):
            continue
        if line.startswith(' EPOCH-TIME'):
            mjd, sod = line[12:].split()
            year, mon, day = mjd2ymd(int(mjd))
            hh, mm, ss = sod2hms(sod)
            cal_time = datetime(year, mon, day, hh, mm, ss)
        elif len(line) >= 37:
            sat, val, sig, nobs, *_ = line.split()
            data.append({
                'date': cal_time, 'sat': sat, 'upd': float(val), 'sig': float(sig),
                'nobs': int(nobs), 'sys': gns_name(sat[0])
            })

    return pd.DataFrame(data)


def draw_upd(data, figfile="", figtitle="", grid=True, dform="%H:%M", linestyle='.', dpi=600):
    sats = list(set(data.sat))
    sats.sort()
    if len(sats) == 0:
        return
    nrow = 2 if len(sats) > 16 else 1
    ncol = 2 if len(sats) > 8 else 1

    nf = ncol * nrow
    nsat = math.ceil(len(sats) / nf)
    fig = plt.figure(figsize=(ncol * 5 + 2, nrow * 3 + 1.5))

    for i in range(nf):
        ax = fig.add_subplot(nrow, ncol, i + 1)
        sats_tmp = sats[nsat * i: nsat * (i + 1)]

        val = 0
        num = 0
        sat = ''
        for sat in sats_tmp:
            dd = data[data.sat == sat]
            ax.plot(dd.date, dd.upd, linestyle, label=sat)
            val += dd.upd.std()
            num += 1

        ax.text(0.05, 0.01, f"Mean STD ({gns_name(sat[0])}): {val / num:6.3f} cyc", weight='semibold',
                transform=ax.transAxes)
        ax.set(ylim=(-1.2, 1.2))
        if grid:
            ax.grid(linestyle='--')
        ax.legend(ncol=5, prop={'size':13, 'weight':'semibold'}, markerscale=1.5, loc='upper left', bbox_to_anchor=(0, 1.24), 
                    labelcolor='linecolor', columnspacing=0.35, labelspacing=0.1, handletextpad=0.25, frameon=False)
        if i % ncol == 0:
            ax.set(ylabel='UPD [cycle]')
        else:
            ax.set_yticklabels([])
        if i >= ncol * (nrow - 1):
            ax.xaxis.set_major_formatter(mdates.DateFormatter(dform))
            for tick in ax.get_xticklabels():
                tick.set_rotation(45)
        else:
            ax.set_xticklabels([])
    fig.subplots_adjust(wspace=0.05, hspace=0.24)
    if figtitle:
        fig.suptitle(figtitle)

    if figfile:
        fig.savefig(figfile, dpi=dpi, bbox_inches='tight')
        logging.info(f'save figure {figfile}')
        plt.close()


def read_nl_res(f_name):
    """"read the residuals, sigmas and alphas of each NL ambiguity"""
    nl_amb = []
    try:
        with open(f_name) as file_object:
            for line in file_object:
                info = line.split()
                if float(info[2]) > 5:
                    continue
                new_amb = {'frac': float(info[1]), 'sig': float(info[2]), 'alpha': float(info[3]),
                           'epo': int(info[4]), 'site': info[5], 'sat': info[6]}
                nl_amb.append(new_amb)
    except FileNotFoundError:
        msg = "Error, the file " + f_name + " does not exist!"
        print(msg)
        return pd.DataFrame()

    nl_amb_pd = pd.DataFrame(nl_amb)
    return nl_amb_pd


def draw_nl_upd(sats_in, nl_upd_pd, ymax=1.5, save_file=''):
    """draw the NL UPD of each satellite"""
    if nl_upd_pd.empty:
        msg = "Error, the imput DataFrame is empty!"
        print(msg)
        return

    sats = []
    for sat in sats_in:
        if sat in nl_upd_pd:
            sats.append(sat)

    if len(sats) <= 0:
        msg = "No common satellite! Please check"
        print(msg)
        return
    elif 8 >= len(sats) > 0:
        fig, ax = plt.subplots(figsize=(7.5, 4))
        for sat in sats:
            ax.plot(nl_upd_pd['sec'] / 3600, nl_upd_pd[sat],
                    '.', label=sat)
        ax.set(xlabel='Hour', ylabel='NL UPD [cycle]', ylim=(-1 * ymax, ymax))
        ax.legend(ncol=4)
    elif 8 < len(sats) <= 16:
        fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharey='row', constrained_layout=True)
        nsat_fig = math.ceil(len(sats) / 2)
        for j in range(2):
            for k in range(nsat_fig):
                ipt = j * nsat_fig + k
                if ipt >= len(sats):
                    break
                if sats[ipt] in nl_upd_pd:
                    ax[j].plot(nl_upd_pd['sec'] / 3600, nl_upd_pd[sats[ipt]],
                               '.', label=sats[ipt])
            ax[j].legend(ncol=4)
            ax[j].grid()
        ax[0].set(xlabel='Hour', ylabel='NL UPD [cycle]', ylim=(-1 * ymax, ymax))
        ax[1].set(xlabel='Hour', ylim=(-1 * ymax, ymax))
    else:
        fig, ax = plt.subplots(2, 2, figsize=(12, 7.5), constrained_layout=True, sharex='col', sharey='row')
        nsat_fig = math.ceil(len(sats) / 4)
        for i in range(2):
            for j in range(2):
                for k in range(nsat_fig):
                    ipt = i * nsat_fig * 2 + j * nsat_fig + k
                    if ipt >= len(sats):
                        break
                    if sats[ipt] in nl_upd_pd:
                        ax[i, j].plot(nl_upd_pd['sec'] / 3600, nl_upd_pd[sats[ipt]],
                                      '.', label=sats[ipt])
                ax[i, j].set(ylim=(-1 * ymax, ymax))
                if j == 0:
                    ax[i, j].set(ylabel='NL UPD [cycle]')
                if i == 1:
                    ax[i, j].set(xlabel='Hour')
                ax[i, j].legend(ncol=4)
                ax[i, j].grid()

    if len(save_file) > 0:
        fig.savefig(save_file, dpi=300)


def draw_wl_upd(sats_in, wl_upd_pd, mode="WL", save_file=''):
    """draw the WL UPD of each satellite"""
    if wl_upd_pd.empty:
        msg = "Error, the imput DataFrame is empty!"
        print(msg)
        return

    sats = []
    for sat in sats_in:
        if sat in wl_upd_pd:
            sats.append(sat)

    if len(sats) <= 0:
        msg = "No common satellite! Please check"
        print(msg)
        return
    elif len(sats) <= 8 and len(sats) > 0:
        fig, ax = plt.subplots(figsize=(7.5, 4))
        for sat in sats:
            ax.plot(wl_upd_pd['doy'], wl_upd_pd[sat],
                    '-o', label=sat)
        ax.set(xlabel='Day of year', ylabel=f"{mode.upper()} UPD [cycle]", ylim=(-1.5, 1.5))
        ax.legend(ncol=4)
        ax.grid()
    elif len(sats) > 8 and len(sats) <= 16:
        fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharey='row', constrained_layout=True)
        nsat_fig = math.ceil(len(sats) / 2)
        for j in range(2):
            for k in range(nsat_fig):
                ipt = j * nsat_fig + k
                if ipt >= len(sats):
                    break
                if sats[ipt] in wl_upd_pd:
                    ax[j].plot(wl_upd_pd['doy'], wl_upd_pd[sats[ipt]],
                               '-o', label=sats[ipt])
            ax[j].set(xlabel='Day of year', ylim=(-1.5, 1.5))
            ax[j].legend(ncol=4)
            ax[j].grid()
        ax[0].set(ylabel=f"{mode.upper()} UPD [cycle]")
    else:
        fig, ax = plt.subplots(2, 2, figsize=(12, 7.5), constrained_layout=True, sharex='col', sharey='row')
        nsat_fig = math.ceil(len(sats) / 4)
        for i in range(2):
            for j in range(2):
                for k in range(nsat_fig):
                    ipt = i * nsat_fig * 2 + j * nsat_fig + k
                    if ipt >= len(sats):
                        break
                    if sats[ipt] in wl_upd_pd:
                        ax[i, j].plot(wl_upd_pd['doy'], wl_upd_pd[sats[ipt]],
                                      '-o', label=sats[ipt])
                ax[i, j].set(ylim=(-1.5, 1.5))
                if j == 0:
                    ax[i, j].set(ylabel=f"{mode.upper()} UPD [cycle]")
                if i == 1:
                    ax[i, j].set(xlabel='DOY')
                ax[i, j].legend(ncol=4)
                ax[i, j].grid()

    if len(save_file) > 0:
        fig.savefig(save_file, dpi=300)


def draw_upd_std(sats_in, nl_upd_pd, ymax=0.5, save_file='', unit="cycle"):
    """draw the standard deviation of NL/WL UPD for each satellite"""
    if nl_upd_pd.empty:
        msg = "Error, the imput DataFrame is empty!"
        print(msg)
        return

    sats = []
    sat_std = {}
    for sat in sats_in:
        if sat in nl_upd_pd:
            sats.append(sat)
            sat_std[sat] = nl_upd_pd[sat].std()

    if len(sats) <= 0:
        msg = "No common satellite! Please check"
        print(msg)
        return

    step = math.ceil(len(sats) / 15)
    sat_idx = range(0, len(sat_std), step)
    sat_lab = sats[::step]

    fig, ax = plt.subplots(figsize=(7, 3.3))
    ax.bar(range(0, len(sat_std)), sat_std.values())
    ax.set(xticks=sat_idx, xticklabels=sat_lab, ylim=(0, ymax))
    ax.set(xlabel='PRN', ylabel=f"Standard deviation [{unit}]")
    m_std = np.mean(list(sat_std.values()))
    ax.text(0, ymax * 0.8, 'mean STD: %5.3f' % m_std, fontsize=13)
    ax.grid()

    if len(save_file) > 0:
        fig.savefig(save_file, dpi=300)


def draw_nl_res(nl_res, save_file=''):
    """draw the histogram of NL ambiguity residuals"""
    if nl_res.empty:
        msg = "Error, the imput DataFrame is empty!"
        print(msg)
        return
    sigma = nl_res['frac'].std()
    mu = nl_res['frac'].mean()
    ntot = len(nl_res)

    fig, ax = plt.subplots()
    n = ax.hist(nl_res['frac'], bins=40,
                range=(-0.5, 0.5), density=True)
    bins = n[1]
    y = ((1 / (np.sqrt(2 * np.pi) * sigma)) *
         np.exp(-0.5 * (1 / sigma * (bins - mu)) ** 2))
    ax.plot(bins, y, '--')
    ax.set_xlabel('NL ambiguity residuals [cycle]')
    ax.set_ylabel('Probability density')
    ax.text(-0.52, 11.5, r'$\mu=%0.3f ,\ \sigma=%0.3f$' % (mu, sigma))
    ax.set(xlim=(-0.6, 0.6), ylim=(0, 14))
    ax.grid(True)
    for a in range(10, 38, 7):
        num = len(nl_res[abs(nl_res.frac) < a / 100])
        per = num / ntot * 100
        yp = 11.5 - (a - 10) / 5
        ax.text(0.16, yp, 'within %0.2f: %3.1f%%' % (a / 100, per))

    if len(save_file) > 0:
        fig.savefig(save_file)


def _sat_visible(data, sats, lat, lon, cut):
    xsta = np.array(ell2cart(lat, lon, 0))
    num = 0
    for sat in sats:
        if sat not in list(data.sat):
            continue
        dt = data[data.sat == sat]
        xsat = np.array([float(dt.px), float(dt.py), float(dt.pz)])
        dx = xsat - xsta
        dist = math.sqrt(dx.dot(dx))

        elev = xsta.dot(dx) / np.sqrt(xsta.dot(xsta)) / dist
        elev = 90 - math.degrees(math.acos(elev))
        if elev > cut:
            num += 1
    return num


def sat_visible(f_sp3, f_out='', gs='G', cut=10):
    data = read_sp3_file(f_sp3)
    if data.empty:
        return
    dd = data[data.sod == 0]

    sats = gns_sat(gs)
    if gs == 'C2':
        sats = [s for s in sats if s < 'C19']
    if gs == 'C3':
        sats = [s for s in sats if s > 'C16']

    data_out = []
    lines = []
    for lat in np.arange(-88.75, 88.75, 2.5):
        for lon in np.arange(-177.5, 180, 5):
            num = _sat_visible(dd, sats, lat, lon, cut)

            data_out.append({'lat': lat, 'lon': lon, 'num': num})
            if f_out:
                lines.append(f'{lat:18.4f} {lon:18.4f} {num:14d}')

    if f_out:
        with open(f_out, 'w') as f:
            for line in lines:
                f.write(f'{line}\n')

    return data_out

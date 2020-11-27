import time
#import pandas as pd
import os
import logging
import math
from gnss_time import GNSStime
from constants import _GNS_NAME, _LEO_INFO


def read_sp3file(f_sp3):
    start = time.time()
    if not os.path.isfile(f_sp3):
        logging.error(f"NO SP3 file {f_sp3}")
        return
    with open(f_sp3) as file_object:
        sp3 = file_object.readlines()
    num = 0
    nsat = 0
    for i in range(len(sp3)):
        if sp3[i][0:1] == '#':
            continue
        elif sp3[i][0:2] == '+ ':
            if isint(sp3[i][1:6]):
                nsat = int(sp3[i][1:6])
        elif sp3[i][0] == '*' and sp3[i][3:7].isdigit():
            num = i
            break

    if nsat == 0:
        logging.error("no satellite in SP3 file")
        return

    del sp3[0:num]
    # delete Velocities
    lines = []
    for line in sp3:
        if line[0] != 'V':
            lines.append(line)
    # sp3 = [j.replace('P  ', 'PG0') for j in sp3]
    # sp3 = [j.replace('P ', 'PG') for j in sp3]

    data = []
    # header = ['time', 'sod', 'sat', 'px', 'py', 'pz']
    while True:
        epoch = GNSStime()
        for i in range(nsat + 1):
            if lines[i][0] == '*':
                info = lines[i].split()
                year = int(info[1])
                month = int(info[2])
                day = int(info[3])
                sod = int(info[4]) * 3600 + int(info[5]) * 60 + float(info[6])
                epoch.set_ymd(year, month, day, sod)
            elif lines[i][0] == 'P':
                sat = lines[i][1:4]
                px = float(lines[i].split()[1]) * 1000  # units: m
                py = float(lines[i].split()[2]) * 1000
                pz = float(lines[i].split()[3]) * 1000
                sat_dict = {'epoch': epoch.mjd + epoch.sod / 86400.0, 'sod': sod, 'sat': sat, 'px': px, 'py': py,
                            'pz': pz}
                data.append(sat_dict)
        del lines[0:nsat + 1]
        if 'EOF' in lines[0]:
            break
    # ------------------------------------------------------------------
    end = time.time()
    msg = f"{f_sp3} file is read in {end - start:.2f} seconds"
    logging.info(msg)
    #return pd.DataFrame(data)
    return data


def read_rnxc_file(f_name, mode="AS"):
    if not os.path.isfile(f_name):
        logging.error(f"NO RINEXC file {f_name}")
        return

    data = []
    with open(f_name) as f:
        for line in f:
            if line[0:2] != mode:
                continue
            if len(line) < 59:
                continue
            epoch = GNSStime()
            name = line[3:7].strip()
            year = int(line[8:12])
            mon = int(line[13:15])
            dd = int(line[16:18])
            sod = int(line[19:21]) * 3600 + int(line[22:24]) * 60 + float(line[25:34])
            epoch.set_ymd(year, mon, dd, sod)
            value = float(line[37:59])
            sat_dict = {'epoch': epoch.mjd + epoch.sod / 86400.0, 'sod': sod, 'name': name, 'clk': value}
            data.append(sat_dict)

    #return pd.DataFrame(data)
    return data


def read_rnxo_file(f_name):
    start = time.time()
    if not os.path.isfile(f_name):
        logging.error(f"NO RINEXO file {f_name}")
        return

    obs_type = {}
    with open(f_name) as file_object:
        lines = file_object.readlines()

    # read rnxo header
    nline = 0
    for line in lines:
        if line.find("END OF HEADER") == 60:
            nline += 1
            break
        elif line.find("SYS / # / OBS TYPES") == 60:
            ot = line[0:60].split()
            ot_num = int(ot[1])
            ot_one = ot[2:]
            nline += 1
            if ot_num > 13:
                for _ in range(int(math.ceil(ot_num / 13)) - 1):
                    ot_one.extend(lines[nline][0:60].split())
                    nline += 1
            obs_type[line[0]] = ot_one
        else:
            nline += 1
    del lines[0:nline]

    # read rnxo data
    data = []
    nline = 0
    while True:
        epoch = GNSStime()
        # =============================================================================
        while True:
            if 'COMMENT' in lines[0]:
                del lines[0]
                nline += 1
            elif 'APPROX POSITION XYZ' in lines[0]:
                del lines[0]
                nline += 1
            elif 'REC # / TYPE / VERS' in lines[0]:
                raise Warning("Receiver type is changed! | Exiting...")
            else:
                break
        # =============================================================================
        if lines[0][0] == ">":
            epochLine = lines[0][1:].split()
            if len(epochLine) == 8:
                epoch_year, epoch_month, epoch_day, epoch_hour, epoch_minute, epoch_second, epoch_flag, epoch_sat_num = \
                    lines[0][1:].split()
                receiver_clock = 0
            elif len(epochLine) == 9:
                epoch_year, epoch_month, epoch_day, epoch_hour, epoch_minute, epoch_second, epoch_flag, epoch_sat_num, receiver_clock = \
                    lines[0][1:].split()
            else:
                raise Warning("Unexpected epoch line format detected! | Program stopped!")
        else:
            raise Warning("Unexpected format detected! | Program stopped!")
        # =========================================================================
        if epoch_flag in {"1", "3", "5", "6"}:
            raise Warning("Deal with this later!")
        elif epoch_flag == "4":
            del lines[0]
            while True:
                if 'COMMENT' in lines[0]:
                    print(lines[0])
                    del lines[0]
                    nline += 1
                elif 'SYS / PHASE SHIFT' in lines[0]:
                    del lines[0]
                    # line += 1
                else:
                    break
        else:
            # =========================================================================
            sod = int(epoch_hour) * 3600 + int(epoch_minute) * 60 + float(epoch_second)
            epoch.set_ymd(int(epoch_year), int(epoch_month), int(epoch_day), sod)
            del lines[0]  # delete epoch header line
            # =============================================================================
            epoch_sat_num = int(epoch_sat_num)
            for svLine in range(epoch_sat_num):
                sat = lines[svLine][0:3]
                sys_ot = obs_type[sat[0]]
                ot_num = len(sys_ot)
                epoch_obs = {'epoch': epoch.mjd + epoch.sod / 86400.0, 'sat': sat}
                for i in range(ot_num):
                    if sys_ot[i][0] != 'C' and sys_ot[i][0] != 'L':
                        continue
                    if isfloat(lines[svLine][3 + 16 * i:16 * i + 17]):
                        epoch_obs[sys_ot[i]] = float(lines[svLine][3 + 16 * i:16 * i + 17])
                data.append(epoch_obs)

            # =============================================================================
            del lines[0:epoch_sat_num]  # number of rows in epoch equals number of visible satellites in RINEX 3
        if len(lines) == 0:
            break

    end = time.time()
    msg = f"{f_name} file is read in {end - start:.2f} seconds"
    logging.info(msg)
    #return pd.DataFrame(data)
    return data


def read_resfile_great(f_res):
    with open(f_res) as file_object:
        lines = file_object.readlines()

    data = []
    for line in lines:
        if line.find("RES") != 0:
            continue
        rec_dict = {}
        tt = GNSStime()
        tt.set_datetime(line[11:30])
        rec_dict['mjd'] = tt.mjd + tt.sod/86400.0
        rec_dict['sod'] = tt.sod
        rec_dict['site'] = line[39:43]
        rec_dict['sat'] = line[48:51]
        rec_dict['ot'] = line[57:59]
        rec_dict['res'] = float(line[74:89])
        data.append(rec_dict)
    #return pd.DataFrame(data)
    return  data


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


def check_ambflag(f_ambflag):
    """ check if the ambflag file is correct"""
    try:
        with open(f_ambflag) as f:
            lfound = False
            for line in f:
                if line[0:3] == "AMB" or line[0:3] == "IAM":
                    lfound = True
                    break
            if not lfound:
                logging.warning(f"no valid ambiguity in {f_ambflag}")
            return lfound
    except FileNotFoundError:
        logging.warning(f"ambflag file not found {f_ambflag}")
        return False


def check_rnxo_ant(f_rnxo, f_atx, change=True):
    """ check if the antenna of RINEXO file in igs14.atx """
    if os.path.isfile(f_rnxo):
        rnxo_ant = ""
        with open(f_rnxo) as file_object:
            for line in file_object:
                if line.find("ANT #") == 60:
                    rnxo_ant = line[20:40]
                    break
                if line.find("END OF HEADER") > 0:
                    logging.warning(f"cannot find ANT # in RINEXO file {f_rnxo}")
                    return False
        if not rnxo_ant:
            logging.warning(f"cannot find ANT # in RINEXO file {f_rnxo}")
            return False
    else:
        logging.warning(f"RINEXO file not found {f_rnxo}")
        return False
    if os.path.isfile(f_atx):
        atx_ant = ""
        with open(f_atx) as file_object:
            for line in file_object:
                if line[0:16] == rnxo_ant[0:16]:
                    atx_ant = line[0:20]
                    break
        if not atx_ant:
            logging.warning(f"cannot find {rnxo_ant[0:16].rstrip()} in {f_atx}")
            return False
        if rnxo_ant != atx_ant:
            if change:
                logging.info(f"convert RINEXO ant from {rnxo_ant} to {atx_ant}")
                alter_file(f_rnxo, rnxo_ant, atx_ant, count=1)
                return True
            else:
                logging.warning(f"Antenna in RINEXO not consistent with igs.atx")
                return False
        else:
            return True
    else:
        logging.warning(f"atx file not found {f_atx}")
        return False


def check_att_file(f_att):
    """ modify the attitude file header """
    sat = os.path.basename(f_att).split('_')[-1]
    if not sat.lower() in _LEO_INFO.keys():
        logging.warning(f"Unknown LEO satellite {sat} in att file name")
        return False
    if os.path.isfile(f_att):
        with open(f_att) as file_object:
            lines = file_object.readlines()
        pos = 0
        for i in range(len(lines)):
            if lines[i][0] == '%':
                continue
            pos = i
            break
        del lines[0:pos]
        if len(lines) < 100:
            logging.warning(f"records in attitude file too few: {len(lines)}")
            return False
        first = GNSStime()
        second = GNSStime()
        third = GNSStime()
        last = GNSStime()
        first.set_mjd(int(lines[0].split()[0]), float(lines[0].split()[1]))
        second.set_mjd(int(lines[1].split()[0]), float(lines[1].split()[1]))
        third.set_mjd(int(lines[2].split()[0]), float(lines[2].split()[1]))
        last.set_mjd(int(lines[-1].split()[0]), float(lines[-1].split()[1]))
        dt1 = first.time_difference(second)
        dt2 = second.time_difference(third)
        if dt1 - dt2 < 0.001:
            interval = int((dt1 + dt2)/2)
        else:
            logging.warning(f"cannot get the interval of att file: {dt1} != {dt2}")
            return False
        with open(f_att, "w") as file_object:
            file_object.write("%% Header of attitude data for LEO satellite\n")
            file_object.write(f"% Satellite     {sat.upper()}\n")
            file_object.write(f"% Start time   {int(first.mjd):>5d}   {first.sod:>12.5f}\n")
            file_object.write(f"% End time     {int(last.mjd):>5d}   {last.sod:>12.5f}\n")
            file_object.write(f"% Time interval {interval:>5.1f}\n")
            file_object.write("%% End of Header\n")
            file_object.writelines(lines)
        return True
    else:
        logging.warning(f"attitude file not found: {f_att}")
        return False


def alter_file(file, old_str, new_str, count=0):
    if not os.path.isfile(file):
        logging.warning(f"file not found {file}")
        return
    with open(file, "r", encoding="utf-8") as file_object:
        data = file_object.read()
    with open(file, "w", encoding="utf-8") as file_object:
        if count > 0:
            file_object.write(data.replace(old_str, new_str, count))
        else:
            file_object.write(data.replace(old_str, new_str))


def alter_file_content(file, old_str, new_str, end="", count=0):
    """
    Purpose: sed -i "s/old_str/new_str/g" file
    :param count: substitute each line until "count" times
    :param end: substitute each line until containing "end"
    :param file: Input file name
    :param old_str: old string
    :param new_str: new string
    :return:
    """
    file_data = ""
    is_end = False
    num = 0
    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            if not is_end:
                if end:
                    if end in line:
                        is_end = True
                if count > 0:
                    if num >= count:
                        is_end = True
            if old_str in line and not is_end:
                line = line.replace(old_str, new_str)
                num += 1
            file_data += line
    with open(file, "w", encoding="utf-8") as f:
        f.write(file_data)

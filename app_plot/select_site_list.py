import logging
import pandas as pd

def get_ant_type(file):
    rec_type = []
    try:    
        with open(file) as f:
            for line in f:
                rec_type.append({
                    'site': line[0:4], 'ant': line[33:53].strip()
                })
    except FileNotFoundError:
        logging.error(f"file not found: {file}")
        return pd.DataFrame()

    return pd.DataFrame(rec_type)


def get_rec_type(file):
    rec_type = []
    try:    
        with open(file) as f:
            for line in f:
                rec_type.append({
                    'site': line[0:4], 'rec': line[33:53].strip()
                })
    except FileNotFoundError:
        logging.error(f"file not found: {file}")
        return pd.DataFrame()

    return pd.DataFrame(rec_type)


def read_site_list(f_list):
    """ read a site list file """
    try:
        with open(f_list) as f:
            lines = f.readlines()
            return [line[1:5].lower() for line in lines if line.startswith(' ')]
    except FileNotFoundError:
        logging.error("site_list not found")
        return


def get_site_list(wkdir, doy0, doy1, site_list='site_list'):
    sites_all = {}
    for i in range(doy0, doy1+1):
        sites = read_site_list(f'{wkdir}/{i:0>3d}/{site_list}')
        for s in sites:
            if s not in sites_all.keys():
                sites_all[s] = 1
            else:
                sites_all[s] += 1

    tmp = []
    for k, v in sites_all.items():
        tmp.append({
            'site': k, 'num': v
        })

    return pd.DataFrame(tmp)


if __name__ == '__main__':
    # antenna with five frequency Galileo PCOPCV and triple-frequency GPS PCOPCV
    select_ant = [
    'ASH700936D_M    SCIS', # all
    'ASH701945B_M    SCIS',
    'ASH701945E_M    SCIT',
    'ASH701945E_M    SCIS', # all
    'JAVRINGANT_DM   NONE', # all
    'JAVRINGANT_G5T  JAVC',
    'JAV_RINGANT_G3T NONE',
    'JAV_GRANT-G3T   NONE', # all
    'LEIAR20         LEIM', # all
    'LEIAR20         NONE', # all
    'LEIAR25.R3      LEIT', # all
    'LEIAR25.R4      LEIT', # all
    'LEIAR25.R4      NONE', # all
    'LEIAT504GG      NONE', # all
    'RNG80971.00     NONE',
    'SEPCHOKE_B3E6   SPKE', # all
    'TPSCR.G3        NONE', # all
    'TPSCR.G3        SCIS', # all
    'TPSCR.G5        TPSH', # all
    'TRM115000.00    NONE', # all
    'TRM57971.00     NONE', # all
    'TRM59800.00     NONE', # all
    'TRM59800.00     SCIS', # all
    'TRM59800.80     NONE',
    'TRM59800.80     SCIS'
    ]
    da = pd.DataFrame({'ant': select_ant})
 
    doy0 = 180
    doy1 = 240

    file = '/home/jqwu/gnss_data/obs_E/2022/180/ant_type'
    ant = get_ant_type(file)

    file = '/home/jqwu/gnss_data/obs_E/2022/180/rec_type'
    rec = get_rec_type(file)

    # select Galileo sites
    wkdir='/home/jqwu/gnss_data/obs_E/2022'
    data_E = get_site_list(wkdir, doy0, doy1, 'site_list')
    data = pd.merge(data_E, ant)
    data = pd.merge(data, rec)
    data = pd.merge(data, da)

    sites_E = list(data[data.num > 56].site.values)
    sites_E.sort()

    # selcet GPS sites
    wkdir='/home/jqwu/gnss_data/obs_G/2022'
    data_G = get_site_list(wkdir, doy0, doy1, 'site_list')
    data = pd.merge(data_G, ant)
    data = pd.merge(data, rec)
    data = pd.merge(data, da)

    sites_G = list(data[data.num > 56].site.values)
    sites_G.sort()

    sites_GE = [s for s in sites_E if s in sites_G]
    file = '/home/jqwu/gnss_data/obs_G/site_list_GE'
    with open(file, 'w') as f:
        for s in sites_GE:
            f.write(f' {s}\n')

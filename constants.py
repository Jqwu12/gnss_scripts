import logging

_GPS_SAT = [f"G{i:0>2d}" for i in range(1, 33)]
_BDS_SAT = [f"C{i:0>2d}" for i in range(1, 62)]
_GAL_SAT = [f"E{i:0>2d}" for i in range(1, 37)]
_GLO_SAT = [f"R{i:0>2d}" for i in range(1, 25)]
_QZS_SAT = [f"J{i:0>2d}" for i in range(1, 8)]
_GPS_SAT_EXC = ['G04']
_BDS_SAT_EXC = ['C31', 'C56', 'C57', 'C58', 'C61']
_GAL_SAT_EXC = ['E20', 'E22', 'E06', 'E10', 'E16', 'E17', 'E23', 'E28', 'E29', 'E32', 'E34', 'E35']
_GLO_SAT_EXC = []
_QZS_SAT_EXC = []
_GPS_SAT = list(set(_GPS_SAT).difference(set(_GPS_SAT_EXC)))
_BDS_SAT = list(set(_BDS_SAT).difference(set(_BDS_SAT_EXC)))
_GAL_SAT = list(set(_GAL_SAT).difference(set(_GAL_SAT_EXC)))
_GLO_SAT = list(set(_GLO_SAT).difference(set(_GLO_SAT_EXC)))
_QZS_SAT = list(set(_QZS_SAT).difference(set(_QZS_SAT_EXC)))
_GPS_SAT.sort()
_BDS_SAT.sort()
_GAL_SAT.sort()
_GLO_SAT.sort()
_QZS_SAT.sort()

_GNS_NAME = {'G': 'GPS',
             'R': 'GLO',
             'E': 'GAL',
             'C': 'BDS',
             'J': 'QZS'}

_GNS_INFO = {
    'GPS': {'sat': _GPS_SAT, 'band': [1, 2, 5], 'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02},
    'BDS': {'sat': _BDS_SAT, 'band': [2, 7, 6], 'code': 1.70, 'phase': 0.01, 'code_leo': 4.0, 'phase_leo': 0.02},
    'GAL': {'sat': _GAL_SAT, 'band': [1, 5, 7], 'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02},
    'GLO': {'sat': _GLO_SAT, 'band': [1, 2], 'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02},
    'QZS': {'sat': _QZS_SAT, 'band': [1, 2, 5], 'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02}
}


def _get_gns_info(sys):
    if sys[0] == 'G':
        return _GNS_INFO['GPS']
    elif sys[0] == 'C':
        return _GNS_INFO['BDS']
    elif sys[0] == 'E':
        return _GNS_INFO['GAL']
    elif sys[0] == 'R':
        return _GNS_INFO['GLO']
    elif sys[0] == 'J':
        return _GNS_INFO['QZS']
    else:
        msg = f"Warning: unknown GNSS {sys[0]}"
        print(msg)
        return


_LEO_INFO = {
    'grace-a': {'abbr': 'graa', 'slrnam': 'gracea', 'ant': 'GRAALEOANNTE'},
    'grace-b': {'abbr': 'grab', 'slrnam': 'graceb', 'ant': 'GRABLEOANNTE'},
    'grace-c': {'abbr': 'grac', 'slrnam': 'gracefo1', 'ant': 'GRACLEOANNTE'},
    'grace-d': {'abbr': 'grad', 'slrnam': 'gracefo2', 'ant': 'GRADLEOANNTE'},
    'jason-2': {'abbr': 'jas2', 'slrnam': 'jason2', 'ant': 'JA2_PA'},
    'jason-3': {'abbr': 'jas3', 'slrnam': 'jason3', 'ant': 'JA3_PA'},
    'kompsat5': {'abbr': 'koms', 'slrnam': 'kompsat5', 'ant': 'KOMPSAT5_ANT'},
    'metop-a': {'abbr': 'meta', 'slrnam': 'metopa', 'ant': 'METOP-A_PA'},
    'metop-b': {'abbr': 'metb', 'slrnam': 'metopb', 'ant': 'METOP-B_PA'},
    'metop-c': {'abbr': 'metc', 'slrnam': 'metopc', 'ant': 'METOP-C_PA'},
    'pazsat': {'abbr': 'pazs', 'slrnam': 'pazsat', 'ant': 'PAZ_ANT'},
    'sentinel-1a': {'abbr': 'se1a', 'slrnam': 'sentinel1a', 'ant': 'SEN-1A-GPSA'},
    'sentinel-1b': {'abbr': 'se1b', 'slrnam': 'sentinel1b', 'ant': 'SEN-1B-GPSA'},
    'sentinel-2a': {'abbr': 'se2a', 'slrnam': 'sentinel2a', 'ant': 'SEN-2A-GPSA'},
    'sentinel-2b': {'abbr': 'se2b', 'slrnam': 'sentinel2b', 'ant': 'SEN-2B-GPSA'},
    'sentinel-3a': {'abbr': 'se3a', 'slrnam': 'sentinel3a', 'ant': 'SEN-3A-GPSA'},
    'sentinel-3b': {'abbr': 'se3b', 'slrnam': 'sentinel3b', 'ant': 'SEN-3B-GPSA'},
    'swarm-a': {'abbr': 'swaa', 'slrnam': 'swarma', 'ant': 'SWARM-A_ANT'},
    'swarm-b': {'abbr': 'swab', 'slrnam': 'swarmb', 'ant': 'SWARM-B_ANT'},
    'swarm-c': {'abbr': 'swac', 'slrnam': 'swarmc', 'ant': 'SWARM-C_ANT'},
    'tandem-x': {'abbr': 'tadx', 'slrnam': 'tandemx', 'ant': 'TDX_ANT'},
    'terrasar-x': {'abbr': 'tesx', 'slrnam': 'terrasarx', 'ant': 'TSX_POD0'}
}


def form_leolist(leos):
    """ get a list containing LEO long names from the input list """
    leo_out = []
    for leo in leos:
        if _leo_short2long(leo):
            leo_out.append(_leo_short2long(leo))
            continue
        if leo in _LEO_INFO.keys():
            leo_out.append(leo)
        else:
            logging.warning(f"Unknown LEO name: {leo}")

    return leo_out


def _leo_short2long(leo):
    for key, val in _LEO_INFO.items():
        if val['abbr'] == leo.strip():
            return key


_LSQ_SCHEME = {
    'BASIC': {
        'inputs': ['rinexo', 'DE', 'poleut1', 'leapsecond', 'atx', 'biabern'],
        'outputs': []
    },
    'LEO_KIN': {
        'inputs': ['orb', 'rinexc', 'sp3', 'satpars', 'attitude'],
        'outputs': ['recclk', 'sp3']
    },
    'LEO_DYN': {
        'inputs': ['orb', 'rinexc', 'ics', 'satpars', 'attitude'],
        'outputs': ['recclk', 'ics']
    },
    'PPP_EST': {
        'inputs': ['rinexn', 'sp3', 'rinexc', 'blq', 'ifcb'],
        'outputs': ['ppp', 'enu', 'flt', 'ambupd', 'recover']
    },
    'PCE_EST': {
        'inputs': ['rinexn', 'sp3', 'blq', 'ifcb', 'satpars'],
        'outputs': ['satclk', 'recclk', 'recover']
    },
    'POD_EST': {
        'inputs': ['orb', 'ics', 'blq', 'satpars', 'rinexn', 'rinexc_all'],
        'outputs': ['ics', 'satclk', 'recclk', 'recover']
    }
}


def read_site_list(f_list):
    """ read a site list file """
    try:
        with open(f_list) as f:
            lines = f.readlines()
    except FileNotFoundError:
        logging.error("site_list not found")
        return

    sites = []
    for line in lines:
        if line[0] != " ":
            continue
        sites.append(line.split()[0])

    return sites

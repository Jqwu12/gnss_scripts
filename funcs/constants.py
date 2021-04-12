from multiprocessing import cpu_count
import pandas as pd

MAX_THREAD = min(8, cpu_count())

_GNS_NAME = {'G': 'GPS',
             'R': 'GLO',
             'E': 'GAL',
             'C': 'BDS',
             'J': 'QZS'}


_GNS_BAND = {'GPS': [1, 2, 5],
             'BDS': [2, 6, 5, 9, 8],
             'GAL': [1, 5, 7, 8, 6],
             'GLO': [1, 2],
             'QZS': [1, 2, 5]}


_GNS_SIG = {'GPS': {'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02},
            'BDS': {'code': 1.70, 'phase': 0.01, 'code_leo': 4.0, 'phase_leo': 0.02},
            'GAL': {'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02},
            'GLO': {'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02},
            'QZS': {'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02}}


def gns_name(gsys: str) -> str:
    if len(gsys) == 1:
        if gsys in _GNS_NAME.keys():
            return _GNS_NAME[gsys]
    if len(gsys) == 3:
        if gsys in _GNS_NAME.values():
            return gsys
    return ''


def gns_id(gsys: str) -> str:
    if len(gsys) == 1:
        if gsys in _GNS_NAME.keys():
            return gsys
    if len(gsys) == 3:
        for k, v in _GNS_NAME.items():
            if v == gsys:
                return k
    return ''


def gns_band(gsys: str) -> list:
    gsys = gns_name(gsys)
    if gsys not in _GNS_BAND.keys():
        return []
    return _GNS_BAND[gsys]


def gns_sig(gsys: str) -> dict:
    gsys = gns_name(gsys)
    if gsys not in _GNS_SIG.keys():
        return {}
    return _GNS_SIG[gsys]


def gns_sat(gsys, sats_rm=None):
    if sats_rm is None:
        sats_rm = []
    gsys = gns_name(gsys)
    if gsys == 'GPS':
        _GPS_SAT = [f"G{i:0>2d}" for i in range(1, 33)]
        _GPS_SAT_EXC = []  # G04 is now available
        _GPS_SAT_EXC.extend(sats_rm)
        _GPS_SAT = list(set(_GPS_SAT).difference(set(_GPS_SAT_EXC)))
        _GPS_SAT.sort()
        return _GPS_SAT
    elif gsys == 'BDS':
        _BDS_SAT = [f"C{i:0>2d}" for i in range(1, 62)]
        _BDS_SAT_EXC = ['C31', 'C56', 'C57', 'C58', 'C61']
        _BDS_SAT_EXC.extend(sats_rm)
        _BDS_SAT = list(set(_BDS_SAT).difference(set(_BDS_SAT_EXC)))
        _BDS_SAT.sort()
        return _BDS_SAT
    elif gsys == 'GAL':
        _GAL_SAT = [f"E{i:0>2d}" for i in range(1, 37)]
        _GAL_SAT_EXC = ['E20', 'E22', 'E06', 'E10', 'E16', 'E17', 'E23', 'E28', 'E29', 'E32', 'E34', 'E35']
        _GAL_SAT_EXC.extend(sats_rm)
        _GAL_SAT = list(set(_GAL_SAT).difference(set(_GAL_SAT_EXC)))
        _GAL_SAT.sort()
        return _GAL_SAT
    elif gsys == 'GLO':
        _GLO_SAT = [f"R{i:0>2d}" for i in range(1, 25)]
        _GLO_SAT_EXC = []
        _GLO_SAT_EXC.extend(sats_rm)
        _GLO_SAT = list(set(_GLO_SAT).difference(set(_GLO_SAT_EXC)))
        _GLO_SAT.sort()
        return _GLO_SAT
    elif gsys == 'QZS':
        _QZS_SAT = [f"J{i:0>2d}" for i in range(1, 8)]
        _QZS_SAT_EXC = []
        _QZS_SAT_EXC.extend(sats_rm)
        _QZS_SAT = list(set(_QZS_SAT).difference(set(_QZS_SAT_EXC)))
        _QZS_SAT.sort()
        return _QZS_SAT


def get_gns_info(gsys, sat_rm=None, band=None):
    if band is None:
        band = []
    if sat_rm is None:
        sat_rm = []
    gsys = gns_name(gsys)
    if not gsys:
        return
    # get the GNSS information
    sats = gns_sat(gsys, sat_rm)
    if band:
        bands = band
    else:
        bands = _GNS_BAND[gsys]
    info = {'sat': sats, 'band': bands}
    info.update(_GNS_SIG[gsys])
    return info


leo_df = pd.DataFrame(
    [
        ['grace-a',     'graa', 'gracea',     'GRAALEOANNTE'],
        ['grace-b',     'grab', 'graceb',     'GRABLEOANNTE'],
        ['grace-c',     'grac', 'gracefo1',   'GRACLEOANNTE'],
        ['grace-d',     'grad', 'gracefo2',   'GRADLEOANNTE'],
        ['jason-2',     'jas2', 'jason2',     'JA2_PA'],
        ['jason-3',     'jas3', 'jason3',     'JA3_PA'],
        ['kompsat5',    'koms', 'kompsat5',   'KOMPSAT5_ANT'],
        ['metop-a',     'meta', 'metopa',     'METOP-A_PA'],
        ['metop-b',     'metb', 'metopb',     'METOP-B_PA'],
        ['metop-c',     'metc', 'metopc',     'METOP-C_PA'],
        ['pazsat',      'pazs', 'pazsat',     'PAZ_ANT'],
        ['sentinel-1a', 'se1a', 'sentinel1a', 'SEN-1A-GPSA'],
        ['sentinel-1b', 'se1b', 'sentinel1b', 'SEN-1B-GPSA'],
        ['sentinel-2a', 'se2a', 'sentinel2a', 'SEN-2A-GPSA'],
        ['sentinel-2b', 'se2b', 'sentinel2b', 'SEN-2B-GPSA'],
        ['sentinel-3a', 'se3a', 'sentinel3a', 'SEN-3A-GPSA'],
        ['sentinel-3b', 'se3b', 'sentinel3b', 'SEN-3B-GPSA'],
        ['swarm-a',     'swaa', 'swarma',     'SWARM-A_ANT'],
        ['swarm-b',     'swab', 'swarmb',     'SWARM-B_ANT'],
        ['swarm-c',     'swac', 'swarmc',     'SWARM-C_ANT'],
        ['tandem-x',    'tadx', 'tandemx',    'TDX_ANT'],
        ['terrasar-x',  'tesx', 'terrasarx',  'TSX_POD0']
    ], columns=['svn', 'name', 'slr', 'ant']
)


__all__ = ['gns_id', 'gns_name', 'gns_sat', 'gns_band', 'gns_sig', 'leo_df', 'MAX_THREAD']

from multiprocessing import cpu_count
import pandas as pd

MAX_THREAD = min(8, cpu_count())

_GNS_NAME = {'G':  'GPS',
             'R':  'GLO',
             'E':  'GAL',
             'C':  'BDS',
             'C2': 'BD2',
             'C3': 'BD3',
             'CG': 'BDG',
             'CI': 'BDI',
             'CM': 'BDM',
             'J':  'QZS'}

_GNS_BAND = {'GPS': [1, 2, 5],
             'BDS': [2, 6, 5, 9, 8],
             'GAL': [1, 5, 7, 8, 6],
             'GLO': [1, 2],
             'QZS': [1, 2, 5]}

_GNS_SIG = {'GPS': {'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02},
            'BDS': {'code': 1.70, 'phase': 0.01, 'code_leo': 4.0, 'phase_leo': 0.02},
            'GAL': {'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02},
            'GLO': {'code': 3.00, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02},
            'QZS': {'code': 0.60, 'phase': 0.01, 'code_leo': 2.0, 'phase_leo': 0.02}}


def gns_name(gsys: str) -> str:
    if len(gsys) < 3:
        if gsys in _GNS_NAME.keys():
            return _GNS_NAME[gsys]
    if len(gsys) == 3:
        if gsys in _GNS_NAME.values():
            return gsys
    return ''


def gns_id(gsys: str) -> str:
    if len(gsys) < 3:
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


def gns_sat(gsys, sats_rm=None) -> list:
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
        _BDS_SAT = [f"C{i:0>2d}" for i in range(1, 62) if i < 47 or i > 58]
        _BDS_SAT_EXC = ['C15', 'C17', 'C18', 'C31', 'C61']
        _BDS_SAT_EXC.extend(sats_rm)
        _BDS_SAT = list(set(_BDS_SAT).difference(set(_BDS_SAT_EXC)))
        _BDS_SAT.sort()
        return _BDS_SAT
    elif gsys == 'BD2':
        _BDS_SAT = [f"C{i:0>2d}" for i in range(1, 17)]
        _BDS_SAT_EXC = ['C15']
        _BDS_SAT_EXC.extend(sats_rm)
        _BDS_SAT = list(set(_BDS_SAT).difference(set(_BDS_SAT_EXC)))
        _BDS_SAT.sort()
        return _BDS_SAT
    elif gsys == 'BD3':
        _BDS_SAT = [f"C{i:0>2d}" for i in range(19, 62) if i < 47 or i > 58]
        _BDS_SAT_EXC = ['C31', 'C61']
        _BDS_SAT_EXC.extend(sats_rm)
        _BDS_SAT = list(set(_BDS_SAT).difference(set(_BDS_SAT_EXC)))
        _BDS_SAT.sort()
        return _BDS_SAT
    elif gsys == 'BDG':
        _BDS_SAT = ['C01', 'C02', 'C03', 'C04', 'C05', 'C59', 'C60']
        _BDS_SAT = list(set(_BDS_SAT).difference(set(sats_rm)))
        _BDS_SAT.sort()
        return _BDS_SAT
    elif gsys == 'BDI':
        _BDS_SAT = ['C06', 'C07', 'C08', 'C09', 'C10', 'C13', 'C16', 'C38', 'C39', 'C40']
        _BDS_SAT = list(set(_BDS_SAT).difference(set(sats_rm)))
        _BDS_SAT.sort()
        return _BDS_SAT
    elif gsys == 'BDM':
        _BDS_SAT = [f"C{i:0>2d}" for i in range(11, 47)]
        _BDS_SAT_EXC = ['C13', 'C16', 'C38', 'C39', 'C40']
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
    return []


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
        ['grace-a',     'graa',     'gracea', 'GRAALEOANNTE'],
        ['grace-b',     'grab',     'graceb', 'GRABLEOANNTE'],
        ['grace-c',     'grac',   'gracefo1', 'GRACLEOANNTE'],
        ['grace-d',     'grad',   'gracefo2', 'GRADLEOANNTE'],
        ['jason-2',     'jas2',     'jason2', 'JA2_PA'],
        ['jason-3',     'jas3',     'jason3', 'JA3_PA'],
        ['kompsat5',    'koms',   'kompsat5', 'KOMPSAT5_ANT'],
        ['metop-a',     'meta',     'metopa', 'METOP-A_PA'],
        ['metop-b',     'metb',     'metopb', 'METOP-B_PA'],
        ['metop-c',     'metc',     'metopc', 'METOP-C_PA'],
        ['pazsat',      'pazs',     'pazsat', 'PAZ_ANT'],
        ['sentinel-1a', 'se1a', 'sentinel1a', 'SEN-1A-GPSA'],
        ['sentinel-1b', 'se1b', 'sentinel1b', 'SEN-1B-GPSA'],
        ['sentinel-2a', 'se2a', 'sentinel2a', 'SEN-2A-GPSA'],
        ['sentinel-2b', 'se2b', 'sentinel2b', 'SEN-2B-GPSA'],
        ['sentinel-3a', 'se3a', 'sentinel3a', 'SEN-3A-GPSA'],
        ['sentinel-3b', 'se3b', 'sentinel3b', 'SEN-3B-GPSA'],
        ['swarm-a',     'swaa',     'swarma', 'SWARM-A_ANT'],
        ['swarm-b',     'swab',     'swarmb', 'SWARM-B_ANT'],
        ['swarm-c',     'swac',     'swarmc', 'SWARM-C_ANT'],
        ['tandem-x',    'tadx',    'tandemx', 'TDX_ANT'],
        ['terrasar-x',  'tesx',  'terrasarx', 'TSX_POD0']
    ], columns=['svn', 'name', 'slr', 'ant']
)

site_namelong = {
    'abmf': 'ABMF00GLP', 'abpo': 'ABPO00MDG', 'acrg': 'ACRG00GHA', 'adis': 'ADIS00ETH', 'aggo': 'AGGO00ARG',
    'aira': 'AIRA00JPN', 'ajac': 'AJAC00FRA', 'albh': 'ALBH00CAN', 'algo': 'ALGO00CAN', 'alic': 'ALIC00AUS',
    'alrt': 'ALRT00CAN', 'amc4': 'AMC400USA', 'ankr': 'ANKR00TUR', 'anmg': 'ANMG00MYS', 'antc': 'ANTC00CHL',
    'areg': 'AREG00PER', 'areq': 'AREQ00PER', 'arht': 'ARHT00ATA', 'artu': 'ARTU00RUS', 'aruc': 'ARUC00ARM',
    'ascg': 'ASCG00SHN', 'aspa': 'ASPA00USA', 'atru': 'ATRU00KAZ', 'auck': 'AUCK00NZL', 'badg': 'BADG00RUS',
    'baie': 'BAIE00CAN', 'bake': 'BAKE00CAN', 'bako': 'BAKO00IDN', 'bamf': 'BAMF00CAN', 'barh': 'BARH00USA',
    'bele': 'BELE00BRA', 'bhr3': 'BHR300BHR', 'bhr4': 'BHR400BHR', 'bik0': 'BIK000KGZ', 'bill': 'BILL00USA',
    'bjco': 'BJCO00BEN', 'bjfs': 'BJFS00CHN', 'bjnm': 'BJNM00CHN', 'blyt': 'BLYT00USA', 'bnoa': 'BNOA00IDN',
    'boav': 'BOAV00BRA', 'bogi': 'BOGI00POL', 'bogt': 'BOGT00COL', 'bor1': 'BOR100POL', 'braz': 'BRAZ00BRA',
    'brew': 'BREW00USA', 'brft': 'BRFT00BRA', 'brmg': 'BRMG00DEU', 'brmu': 'BRMU00GBR', 'brst': 'BRST00FRA',
    'brun': 'BRUN00BRN', 'brux': 'BRUX00BEL', 'bshm': 'BSHM00ISR', 'btng': 'BTNG00IDN', 'bucu': 'BUCU00ROU',
    'bzr2': 'BZR200ITA', 'cags': 'CAGS00CAN', 'cas1': 'CAS100ATA', 'ccj2': 'CCJ200JPN', 'cebr': 'CEBR00ESP',
    'cedu': 'CEDU00AUS', 'cggn': 'CGGN00NGA', 'chan': 'CHAN00CHN', 'chil': 'CHIL00USA', 'chof': 'CHOF00JPN',
    'chpg': 'CHPG00BRA', 'chpi': 'CHPI00BRA', 'chti': 'CHTI00NZL', 'chum': 'CHUM00KAZ', 'chur': 'CHUR00CAN',
    'chwk': 'CHWK00CAN', 'cibg': 'CIBG00IDN', 'cit1': 'CIT100USA', 'ckis': 'CKIS00COK', 'cksv': 'CKSV00TWN',
    'cmp9': 'CMP900USA', 'cmum': 'CMUM00THA', 'cnmr': 'CNMR00USA', 'coco': 'COCO00AUS', 'cord': 'CORD00ARG',
    'coso': 'COSO00USA', 'cote': 'COTE00ATA', 'coyq': 'COYQ00CHL', 'cpnm': 'CPNM00THA', 'cpvg': 'CPVG00CPV',
    'crao': 'CRAO00UKR', 'crfp': 'CRFP00USA', 'cro1': 'CRO100VIR', 'cusv': 'CUSV00THA', 'cut0': 'CUT000AUS',
    'cuut': 'CUUT00THA', 'cyne': 'CYNE00GUF', 'cztg': 'CZTG00ATF', 'dae2': 'DAE200KOR', 'daej': 'DAEJ00KOR',
    'dakr': 'DAKR00SEN', 'darw': 'DARW00AUS', 'dav1': 'DAV100ATA', 'dear': 'DEAR00ZAF', 'dgar': 'DGAR00GBR',
    'dhlg': 'DHLG00USA', 'djig': 'DJIG00DJI', 'dlf1': 'DLF100NLD', 'dltv': 'DLTV00VNM', 'drag': 'DRAG00ISR',
    'drao': 'DRAO00CAN', 'dubo': 'DUBO00CAN', 'dumg': 'DUMG00ATA', 'dund': 'DUND00NZL', 'dyng': 'DYNG00GRC',
    'ebre': 'EBRE00ESP', 'eil3': 'EIL300USA', 'eil4': 'EIL400USA', 'enao': 'ENAO00PRT', 'eprt': 'EPRT00USA',
    'escu': 'ESCU00CAN', 'faa1': 'FAA100PYF', 'fair': 'FAIR00USA', 'fale': 'FALE00WSM', 'falk': 'FALK00FLK',
    'ffmj': 'FFMJ00DEU', 'flin': 'FLIN00CAN', 'flrs': 'FLRS00PRT', 'frdn': 'FRDN00CAN', 'ftna': 'FTNA00WLF',
    'func': 'FUNC00PRT', 'gamb': 'GAMB00PYF', 'gamg': 'GAMG00KOR', 'ganp': 'GANP00SVK', 'gcgo': 'GCGO00USA',
    'geno': 'GENO00ITA', 'glps': 'GLPS00ECU', 'glsv': 'GLSV00UKR', 'gmsd': 'GMSD00JPN', 'gode': 'GODE00USA',
    'godn': 'GODN00USA', 'gods': 'GODS00USA', 'godz': 'GODZ00USA', 'gol2': 'GOL200USA', 'gold': 'GOLD00USA',
    'gop6': 'GOP600CZE', 'gop7': 'GOP700CZE', 'gope': 'GOPE00CZE', 'grac': 'GRAC00FRA', 'gras': 'GRAS00FRA',
    'graz': 'GRAZ00AUT', 'guam': 'GUAM00GUM', 'guao': 'GUAO00CHN', 'guat': 'GUAT00GTM', 'guug': 'GUUG00GUM',
    'hal1': 'HAL100USA', 'hamd': 'HAMD00IRN', 'harb': 'HARB00ZAF', 'hers': 'HERS00GBR', 'hert': 'HERT00GBR',
    'hksl': 'HKSL00HKG', 'hkws': 'HKWS00HKG', 'hlfx': 'HLFX00CAN', 'hnlc': 'HNLC00USA', 'hnpt': 'HNPT00USA',
    'hnus': 'HNUS00ZAF', 'hob2': 'HOB200AUS', 'hofn': 'HOFN00ISL', 'holb': 'HOLB00CAN', 'holm': 'HOLM00CAN',
    'holp': 'HOLP00USA', 'hrag': 'HRAG00ZAF', 'hrao': 'HRAO00ZAF', 'hueg': 'HUEG00DEU', 'hyde': 'HYDE00IND',
    'ieng': 'IENG00ITA', 'iisc': 'IISC00IND', 'ineg': 'INEG00MEX', 'invk': 'INVK00CAN', 'iqal': 'IQAL00CAN',
    'iqqe': 'IQQE00CHL', 'irkj': 'IRKJ00RUS', 'irkm': 'IRKM00RUS', 'irkt': 'IRKT00RUS', 'isba': 'ISBA00IRQ',
    'ishi': 'ISHI00JPN', 'ispa': 'ISPA00CHL', 'ista': 'ISTA00TUR', 'izmi': 'IZMI00TUR', 'jctw': 'JCTW00ZAF',
    'jfng': 'JFNG00CHN', 'jnav': 'JNAV00VNM', 'jog2': 'JOG200IDN', 'joz2': 'JOZ200POL', 'joze': 'JOZE00POL',
    'jplm': 'JPLM00USA', 'jpre': 'JPRE00ZAF', 'karr': 'KARR00AUS', 'kat1': 'KAT100AUS', 'kerg': 'KERG00ATF',
    'kgni': 'KGNI00JPN', 'khar': 'KHAR00UKR', 'kir0': 'KIR000SWE', 'kir8': 'KIR800SWE', 'kiri': 'KIRI00KIR',
    'kiru': 'KIRU00SWE', 'kit3': 'KIT300UZB', 'kitg': 'KITG00UZB', 'kmnm': 'KMNM00TWN', 'kokb': 'KOKB00USA',
    'kokv': 'KOKV00USA', 'kos1': 'KOS100NLD', 'kost': 'KOST00KAZ', 'kouc': 'KOUC00NCL', 'koug': 'KOUG00GUF',
    'kour': 'KOUR00GUF', 'krgg': 'KRGG00ATF', 'krs1': 'KRS100TUR', 'kuj2': 'KUJ200CAN', 'kzn2': 'KZN200RUS',
    'lae1': 'LAE100PNG', 'lama': 'LAMA00POL', 'laut': 'LAUT00FJI', 'lbch': 'LBCH00USA', 'lck3': 'LCK300IND',
    'lck4': 'LCK400IND', 'leij': 'LEIJ00DEU', 'lhaz': 'LHAZ00CHN', 'licc': 'LICC00GBR', 'llag': 'LLAG00ESP',
    'lmmf': 'LMMF00MTQ', 'lpal': 'LPAL00ESP', 'lpgs': 'LPGS00ARG', 'lroc': 'LROC00FRA', 'm0se': 'M0SE00ITA',
    'mac1': 'MAC100AUS', 'mad2': 'MAD200ESP', 'madr': 'MADR00ESP', 'mag0': 'MAG000RUS', 'maju': 'MAJU00MHL',
    'mal2': 'MAL200KEN', 'mana': 'MANA00NIC', 'mar6': 'MAR600SWE', 'mar7': 'MAR700SWE', 'mars': 'MARS00FRA',
    'mas1': 'MAS100ESP', 'mat1': 'MAT100ITA', 'mate': 'MATE00ITA', 'matg': 'MATG00ITA', 'maui': 'MAUI00USA',
    'maw1': 'MAW100ATA', 'mayg': 'MAYG00MYT', 'mbar': 'MBAR00UGA', 'mchl': 'MCHL00AUS', 'mcil': 'MCIL00JPN',
    'mcm4': 'MCM400ATA', 'mdo1': 'MDO100USA', 'mdvj': 'MDVJ00RUS', 'medi': 'MEDI00ITA', 'meli': 'MELI00ESP',
    'mers': 'MERS00TUR', 'met3': 'MET300FIN', 'metg': 'METG00FIN', 'mets': 'METS00FIN', 'mfkg': 'MFKG00ZAF',
    'mgue': 'MGUE00ARG', 'mikl': 'MIKL00UKR', 'mizu': 'MIZU00JPN', 'mkea': 'MKEA00USA', 'mobj': 'MOBJ00RUS',
    'mobk': 'MOBK00RUS', 'mobn': 'MOBN00RUS', 'mobs': 'MOBS00AUS', 'moiu': 'MOIU00KEN', 'monp': 'MONP00USA',
    'morp': 'MORP00GBR', 'mqzg': 'MQZG00NZL', 'mrc1': 'MRC100USA', 'mrl1': 'MRL100NZL', 'mrl2': 'MRL200NZL',
    'mro1': 'MRO100AUS', 'mtka': 'MTKA00JPN', 'mtv1': 'MTV100URY', 'mtv2': 'MTV200URY', 'nain': 'NAIN00CAN',
    'nano': 'NANO00CAN', 'naur': 'NAUR00NRU', 'ncku': 'NCKU00TWN', 'nico': 'NICO00CYP', 'nist': 'NIST00USA',
    'nium': 'NIUM00NIU', 'nklg': 'NKLG00GAB', 'nlib': 'NLIB00USA', 'nnor': 'NNOR00AUS', 'not1': 'NOT100ITA',
    'novm': 'NOVM00RUS', 'nrc1': 'NRC100CAN', 'nril': 'NRIL00RUS', 'nrmd': 'NRMD00NCL', 'ntus': 'NTUS00SGP',
    'nvsk': 'NVSK00RUS', 'nya1': 'NYA100NOR', 'nya2': 'NYA200NOR', 'nyal': 'NYAL00NOR', 'oak1': 'OAK100GBR',
    'oak2': 'OAK200GBR', 'obe4': 'OBE400DEU', 'ohi2': 'OHI200ATA', 'ohi3': 'OHI300ATA', 'ons1': 'ONS100SWE',
    'onsa': 'ONSA00SWE', 'op71': 'OP7100FRA', 'opmt': 'OPMT00FRA', 'orid': 'ORID00MKD', 'osn3': 'OSN300KOR',
    'osn4': 'OSN400KOR', 'ous2': 'OUS200NZL', 'owmg': 'OWMG00NZL', 'pado': 'PADO00ITA', 'palm': 'PALM00ATA',
    'parc': 'PARC00CHL', 'park': 'PARK00AUS', 'pdel': 'PDEL00PRT', 'pen2': 'PEN200HUN', 'penc': 'PENC00HUN',
    'pert': 'PERT00AUS', 'pets': 'PETS00RUS', 'pgen': 'PGEN00PHL', 'picl': 'PICL00CAN', 'pie1': 'PIE100USA',
    'pimo': 'PIMO00PHL', 'pin1': 'PIN100USA', 'pngm': 'PNGM00PNG', 'poal': 'POAL00BRA', 'pohn': 'POHN00FSM',
    'pol2': 'POL200KGZ', 'polv': 'POLV00UKR', 'pots': 'POTS00DEU', 'pove': 'POVE00BRA', 'pppc': 'PPPC00PHL',
    'prds': 'PRDS00CAN', 'pre3': 'PRE300ZAF', 'pre4': 'PRE400ZAF', 'ptag': 'PTAG00PHL', 'ptbb': 'PTBB00DEU',
    'ptgg': 'PTGG00PHL', 'ptvl': 'PTVL00VUT', 'qaq1': 'QAQ100GRL', 'qiki': 'QIKI00CAN', 'qui3': 'QUI300ECU',
    'qui4': 'QUI400ECU', 'quin': 'QUIN00USA', 'rabt': 'RABT00MAR', 'raeg': 'RAEG00PRT', 'ramo': 'RAMO00ISR',
    'rbay': 'RBAY00ZAF', 'rcmn': 'RCMN00KEN', 'rdsd': 'RDSD00DOM', 'redu': 'REDU00BEL', 'reso': 'RESO00CAN',
    'reun': 'REUN00REU', 'reyk': 'REYK00ISL', 'rgdg': 'RGDG00ARG', 'riga': 'RIGA00LVA', 'rio2': 'RIO200ARG',
    'riop': 'RIOP00ECU', 'roag': 'ROAG00ESP', 'rock': 'ROCK00USA', 'roth': 'ROTH00ATA', 'salu': 'SALU00BRA',
    'samo': 'SAMO00WSM', 'sant': 'SANT00CHL', 'sask': 'SASK00CAN', 'savo': 'SAVO00BRA', 'sbok': 'SBOK00ZAF',
    'sch2': 'SCH200CAN', 'scip': 'SCIP00USA', 'scor': 'SCOR00GRL', 'scrz': 'SCRZ00BOL', 'sctb': 'SCTB00ATA',
    'scub': 'SCUB00CUB', 'sejn': 'SEJN00KOR', 'seme': 'SEME00KAZ', 'sey2': 'SEY200SYC', 'seyg': 'SEYG00SYC',
    'sfdm': 'SFDM00USA', 'sfer': 'SFER00ESP', 'sgoc': 'SGOC00LKA', 'sgpo': 'SGPO00USA', 'shao': 'SHAO00CHN',
    'she2': 'SHE200CAN', 'sin1': 'SIN100SGP', 'smst': 'SMST00JPN', 'sni1': 'SNI100USA', 'sod3': 'SOD300FIN',
    'sofi': 'SOFI00BGR', 'solo': 'SOLO00SLB', 'spk1': 'SPK100USA', 'spt0': 'SPT000SWE', 'sptu': 'SPTU00BRA',
    'ssia': 'SSIA00SLV', 'stfu': 'STFU00USA', 'sthl': 'STHL00GBR', 'stj3': 'STJ300CAN', 'stjo': 'STJO00CAN',
    'stk2': 'STK200JPN', 'stpm': 'STPM00SPM', 'str1': 'STR100AUS', 'str2': 'STR200AUS', 'sulp': 'SULP00UKR',
    'suth': 'SUTH00ZAF', 'sutm': 'SUTM00ZAF', 'suwn': 'SUWN00KOR', 'svtl': 'SVTL00RUS', 'sydn': 'SYDN00AUS',
    'syog': 'SYOG00ATA', 'tabl': 'TABL00USA', 'tana': 'TANA00ETH', 'tash': 'TASH00UZB', 'tcms': 'TCMS00TWN',
    'tdou': 'TDOU00ZAF', 'tehn': 'TEHN00IRN', 'thtg': 'THTG00PYF', 'thti': 'THTI00PYF', 'thu2': 'THU200GRL',
    'tid1': 'TID100AUS', 'tidb': 'TIDB00AUS', 'tit2': 'TIT200DEU', 'tixi': 'TIXI00RUS', 'tlse': 'TLSE00FRA',
    'tlsg': 'TLSG00FRA', 'tnml': 'TNML00TWN', 'tong': 'TONG00TON', 'topl': 'TOPL00BRA', 'torp': 'TORP00USA',
    'tow2': 'TOW200AUS', 'trak': 'TRAK00USA', 'tro1': 'TRO100NOR', 'tsk2': 'TSK200JPN', 'tskb': 'TSKB00JPN',
    'tubi': 'TUBI00TUR', 'tuva': 'TUVA00TUV', 'twtf': 'TWTF00TWN', 'ucal': 'UCAL00CAN', 'uclp': 'UCLP00USA',
    'uclu': 'UCLU00CAN', 'ufpr': 'UFPR00BRA', 'ulab': 'ULAB00MNG', 'uldi': 'ULDI00ZAF', 'unb3': 'UNB300CAN',
    'unbd': 'UNBD00CAN', 'unbj': 'UNBJ00CAN', 'unbn': 'UNBN00CAN', 'unsa': 'UNSA00ARG', 'unx2': 'UNX200AUS',
    'unx3': 'UNX300AUS', 'ural': 'URAL00RUS', 'urum': 'URUM00CHN', 'usn7': 'USN700USA', 'usn8': 'USN800USA',
    'usn9': 'USN900USA', 'usno': 'USNO00USA', 'usp1': 'USP100FJI', 'usud': 'USUD00JPN', 'utqi': 'UTQI00USA',
    'uzhl': 'UZHL00UKR', 'vacs': 'VACS00MUS', 'vald': 'VALD00CAN', 'vill': 'VILL00ESP', 'vis0': 'VIS000SWE',
    'vndp': 'VNDP00USA', 'voim': 'VOIM00MDG', 'wab2': 'WAB200CHE', 'wark': 'WARK00NZL', 'warn': 'WARN00DEU',
    'wdc5': 'WDC500USA', 'wdc6': 'WDC600USA', 'wes2': 'WES200USA', 'wgtn': 'WGTN00NZL', 'whc1': 'WHC100USA',
    'whit': 'WHIT00CAN', 'widc': 'WIDC00USA', 'will': 'WILL00CAN', 'wind': 'WIND00NAM', 'wlsn': 'WLSN00USA',
    'wroc': 'WROC00POL', 'wsrt': 'WSRT00NLD', 'wtz3': 'WTZ300DEU', 'wtza': 'WTZA00DEU', 'wtzr': 'WTZR00DEU',
    'wtzs': 'WTZS00DEU', 'wtzz': 'WTZZ00DEU', 'wuh2': 'WUH200CHN', 'wuhn': 'WUHN00CHN', 'xmis': 'XMIS00AUS',
    'yakt': 'YAKT00RUS', 'yar2': 'YAR200AUS', 'yar3': 'YAR300AUS', 'yarr': 'YARR00AUS', 'yebe': 'YEBE00ESP',
    'yel2': 'YEL200CAN', 'yell': 'YELL00CAN', 'yibl': 'YIBL00OMN', 'ykro': 'YKRO00CIV', 'yons': 'YONS00KOR',
    'yssk': 'YSSK00RUS', 'zamb': 'ZAMB00ZMB', 'zeck': 'ZECK00RUS', 'zim2': 'ZIM200CHE', 'zim3': 'ZIM300CHE',
    'zimm': 'ZIMM00CHE', 'bing': 'BING00AUS', 'cmak': 'CMAK00IDN', 'cool': 'COOL00AUS', 'csby': 'CSBY00IDN',
    'cuke': 'CUKE00IDN', 'hklm': 'HKLM00HKG', 'lamb': 'LAMB00AUS', 'lord': 'LORD00AUS', 'mao0': 'MAO000USA',
    'norf': 'NORF00AUS', 'nrmg': 'NRMG00NCL', 'pthl': 'PTHL00AUS'
}

__all__ = ['gns_id', 'gns_name', 'gns_sat', 'gns_band', 'gns_sig', 'leo_df', 'site_namelong', 'MAX_THREAD']

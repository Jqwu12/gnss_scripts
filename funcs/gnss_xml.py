from funcs.constants import get_gns_info, get_gns_sat, _LSQ_SCHEME
from funcs import gnss_tools as gt
import xml.etree.ElementTree as ET
import os
import logging


def generate_great_xml(config, app, f_xml, **kwargs):
    if app == 'great_turboedit':
        use_res_crd = False
        for key, val in kwargs.items():
            if key == 'use_res_crd':
                use_res_crd = val
        _generate_turboedit_xml(config, f_xml, use_res_crd)
    elif app == 'great_clockrepair':
        _generat_clockrepair_xml(config, f_xml)
    elif app in ['great_podlsq', 'great_ppplsq', 'great_pcelsq']:
        mode = ''
        ambcon = False
        fix_mode = "NO"
        use_res_crd = False
        for key, val in kwargs.items():
            if key == 'ambcon':
                ambcon = val
            elif key == 'mode':
                mode = val
            elif key == 'fix_mode':
                fix_mode = val
            elif key == 'use_res_crd':
                use_res_crd = val
        if len(mode) == 0:
            logging.critical("LSQ mode missing [LEO_KIN/...]")
            raise SystemExit("LSQ mode missing [LEO_KIN/...]")
        _generate_lsq_xml(config, f_xml, mode, ambcon, fix_mode, use_res_crd)
    elif app == "great_preedit":
        _generate_preedit_xml(config, f_xml)
    elif app == 'great_oi':
        sattype = 'gns'
        for key, val in kwargs.items():
            if key == 'sattype':
                sattype = val
        _generate_oi_xml(config, f_xml, sattype=sattype)
    elif app == 'great_sp3orb':
        sattype = 'gns'
        for key, val in kwargs.items():
            if key == 'sattype':
                sattype = val
        _generate_sp3orb_xml(config, f_xml, sattype=sattype)
    elif app == 'great_clkdif':
        _generate_clkdif_xml(config, f_xml)
    elif app == 'great_orbdif':
        trans = "STRD"
        excsat = "C01 C02 C03 C04 C05 G18 G23"
        for key, val in kwargs.items():
            if key == 'trans':
                trans = val
            elif key == "excsat":
                excsat = val
        _generate_orbdif_xml(config, f_xml, trans, excsat)
    elif app == 'great_orbfit':
        _generate_orbfit_xml(config, f_xml)
    elif app == 'great_orbfitleo':
        fit = False
        trans = ""
        unit = "mm"
        for key, val in kwargs.items():
            if key == 'fit':
                fit = val
            elif key == 'trans':
                trans = val
            elif key == 'unit':
                unit = val
        _generate_orbfitleo_xml(config, f_xml, fit, trans, unit)
    elif app == 'great_editres':
        nshort = 120
        jump = 100
        bad = 100
        mode = "L12"
        edt_amb = False
        all_sites = False
        for key, val in kwargs.items():
            if key == 'nshort':
                nshort = val
            elif key == 'jump':
                jump = val
            elif key == 'bad':
                bad = val
            elif key == 'mode':
                mode = val
            elif key == 'edt_amb':
                edt_amb = val
            elif key == 'all_sites':
                all_sites = val
        _generate_edtres_xml(config, f_xml, nshort, jump, bad, mode, edt_amb, all_sites)
    elif app == 'great_ambfixD':
        _generate_ambfix_xml(config, f_xml, "SD")
    elif app == 'great_ambfixDd':
        _generate_ambfix_xml(config, f_xml, "DD")
    elif app == 'great_updlsq':
        mode = "WL"
        for key, val in kwargs.items():
            if key == 'mode':
                mode = val.upper()
        _generate_updlsq_xml(config, f_xml, mode)
    elif app == 'great_convobs':
        _generate_convobs_xml(config, f_xml)
    else:
        logging.error(f"Unknown GREAT App {app}")


def _generat_clockrepair_xml(config, f_xml_out):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    # <gen>
    gen = _get_element_gen(config, ['intv', 'sys', 'rec'])
    root.append(gen)
    # <inputs>
    inp = _get_element_io(config, 'inputs', ['rinexo'], check=True)
    root.append(inp)
    # <outputs>
    out = ET.SubElement(root, 'outputs')
    out_ele = ET.SubElement(out, 'obs_dir')
    out_ele.text = config.get_filename('obs_trimcor', check=False)
    # write new xml
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _generate_preedit_xml(config, f_xml_out):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    # <gen>
    gen = _get_element_gen(config, ['intv', 'sys', 'rec'])
    root.append(gen)
    # <inputs>
    f_inputs = ['rinexo', 'rinexn', 'poleut1', 'sinex']
    inp = _get_element_io(config, 'inputs', f_inputs, check=True)
    root.append(inp)
    # <outputs>
    out = ET.SubElement(root, 'outputs')
    out_ele = ET.SubElement(out, 'ics')
    out_ele.text = config.get_filename('ics', check=False)
    # <gps> <bds> <gal> <glo>
    for gns in _get_element_gns(config):
        root.append(gns)
    # <force_model> : get from template xml file
    force_model = _get_force_model_from_template(config)
    if force_model:
        root.append(force_model)
    # write new xml
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _generate_turboedit_xml(config, f_xml_out, use_res_crd=False):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    # <gen>
    gen = _get_element_gen(config, ['intv', 'sys', 'rec'])
    root.append(gen)
    # <receiver> <parameters>
    if config.stalist():
        rec = _get_receiver(config, use_res_crd)
        par = _get_lsq_param(config, "PPP_EST")
        root.append(rec)
        root.append(par)
    # <gps> <bds> <gal> <glo>
    for gns in _get_element_gns(config):
        root.append(gns)
    # <inputs>
    f_inputs = ['rinexo', 'rinexn']
    inp = _get_element_io(config, 'inputs', f_inputs, check=True)
    root.append(inp)
    # <outputs>
    out = ET.SubElement(root, 'outputs')
    out.set('append', 'false')
    out.set('verb', '1')
    xml_log = ET.SubElement(out, 'log')
    xml_log.text = str(f_xml_out).strip().replace(".xml", ".log")
    ambflag_dir = ET.SubElement(out, 'ambflag_dir')
    if config.get_filename('ambflagdir').isspace():
        ambflag_dir.text = 'log_tb'
    else:
        ambflag_dir.text = config.get_filename('ambflagdir')
    # <process>
    proc = ET.SubElement(root, 'process')
    for key, val in config.xml_process().items():
        proc.set(key, val)
    # <filter> <turboedit> : get from template xml file
    xml_temp = ''
    if config.config.has_section('xml_template'):
        if config.config.has_option('xml_template', 'turboedit'):
            xml_temp = config.config.get('xml_template', 'turboedit')
    if os.path.isfile(xml_temp):
        ref_tree = ET.parse(xml_temp)
        ref_root = ref_tree.getroot()
        filt = ref_root.find('filter')
        tb = ref_root.find('turboedit')
        root.append(filt)
        root.append(tb)
    else:
        logging.error(f"xml template for turboedit {xml_temp} not found!")
    # write new xml
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _generate_convobs_xml(config, f_xml_out):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    # <gen>
    gen = _get_element_gen(config, ['intv', 'sys', 'rec'])
    root.append(gen)
    # <inputs>
    f_inputs = ['rinexo', 'ambflag']
    if int(config.config['process_scheme']['frequency']) > 2:
        f_inputs.append('ambflag13')
    inp = _get_element_io(config, 'inputs', f_inputs, check=True)
    root.append(inp)
    # <outputs>
    out = ET.SubElement(root, 'outputs')
    out.set('append', 'false')
    out.set('verb', '1')
    out_ele = ET.SubElement(out, 'obs_dir')
    out_ele.text = config.get_filename('obs_fix')
    for gns in _get_element_gns(config):
        root.append(gns)
    # write new xml
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _generate_lsq_xml(config, f_xml_out, mode, ambcon=False, fix_mode="NO", use_res_crd=False):
    if fix_mode != "NO":
        config.update_process(ambiguity="AR")
    else:
        config.update_process(ambiguity="F")  # this is only for enu outputs
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    # <gen>
    gen = _get_element_gen(config, ['intv', 'sys', 'rec', 'est'])
    root.append(gen)
    # <receiver> <parameters>
    if config.stalist():
        f_preedit = os.path.join('xml', 'preedit.xml')
        if os.path.isfile(f_preedit):
            ref_tree = ET.parse(f_preedit)
            ref_root = ref_tree.getroot()
            rec = ref_root.find('receiver')
        else:
            rec = _get_receiver(config, use_res_crd)
        par = _get_lsq_param(config, mode)
        root.append(rec)
        root.append(par)
    # <inputs> <outputs>
    if mode.upper() in _LSQ_SCHEME.keys():
        inp, out = _get_element_lsq_io(config, mode)
    else:
        logging.error("Unknown LSQ MODE [LEO_KIN/...]")
        return
    if ambcon:
        inp_ele = ET.SubElement(inp, 'ambcon')
        inp_ele.text = config.get_filename('ambcon', check=True)
    if fix_mode != "NO" or config.apply_carrier_range() \
            and mode not in ["POD_EST", "PCE_EST"]:
        inp_ele = ET.SubElement(inp, 'upd')
        inp_ele.text = config.get_filename('upd', check=True)
    root.append(inp)
    out_ele = ET.SubElement(out, 'log')
    out_ele.text = str(f_xml_out).strip().replace(".xml", ".log")
    root.append(out)
    # <process>
    proc = ET.SubElement(root, 'process')
    for key, val in config.xml_process().items():
        proc.set(key, val)
    if ambcon:
        proc.set('ambfix', 'true')
    else:
        proc.set('ambfix', 'false')
    if mode == "PCE_EST" or mode == "POD_EST":
        proc.set('ref_clk', _set_ref_clk(config, mode='site'))
        # proc.set('ref_clk', '')
        proc.set('sig_ref_clk', '0.001')
        proc.set('num_thread', '8')
        proc.set('sysbias_model', 'ISB+CON')  # only ISB, no GLONASS IFB
    ifb_model = ET.SubElement(proc, 'ifb_model')
    if config.config['process_scheme']['obs_combination'] == "RAW_ALL":
        ifb_model.text = 'EST_REC_IFB'
    else:
        ifb_model.text = 'NONE'
    for gns in _get_element_gns(config):
        root.append(gns)
    if 'LEO' in mode.upper():
        leo = ET.SubElement(root, 'LEO')
        leosat = ET.SubElement(leo, 'sat')
        leosat.text = gt.list2str(config.leolist())
    # <ambiguity>
    if "PPP" in mode.upper():
        ambfix = _get_ambfix(config, fix_mode=fix_mode)
        root.append(ambfix)
    # write new xml
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _get_element_lsq_io(config, mode):
    if mode.upper() in _LSQ_SCHEME.keys():
        f_inputs = _LSQ_SCHEME['BASIC']['inputs'] + _LSQ_SCHEME[mode.upper()]['inputs']
        f_outputs = _LSQ_SCHEME['BASIC']['outputs'] + _LSQ_SCHEME[mode.upper()]['outputs']
    else:
        logging.error("Unknown LSQ MODE [LEO_KIN/...]")
        return
    inputs = ET.Element('inputs')
    for file in f_inputs:
        if file == 'ifcb':
            if "GPS" not in config.gnssys():
                continue
            if int(config.config['process_scheme']['frequency']) < 3:
                continue
        if file == 'ics' and mode.upper() == "LEO_DYN":
            inp_ele = ET.SubElement(inputs, 'icsleo')
            inp_ele.text = config.get_filename(file, check=True, sattype='leo')
            continue
        if file == 'orb' and mode.upper() == "LEO_DYN":
            inp_ele = ET.SubElement(inputs, 'orb')
            inp_ele.text = config.get_filename(file, check=True, sattype='gnsleo')
            continue
        if file == 'sp3' and mode.upper() == "LEO_KIN":
            inp_ele = ET.SubElement(inputs, 'sp3')
            inp_ele.text = config.get_filename(file, check=True, sattype='gnsleo')
            continue
        if file == 'rinexc_all':
            if mode.upper() == "POD_EST":
                inp_ele = ET.SubElement(inputs, 'rinexc')
                inp_ele.text = config.get_filename('satclk', check=True) + " " + config.get_filename('recclk', check=True)
            else:
                inp_ele = ET.SubElement(inputs, 'rinexc')
                inp_ele.text = config.get_filename('rinexc_all', check=True)
            continue
        inp_ele = ET.SubElement(inputs, file)
        inp_ele.text = config.get_filename(file, check=True, sattype='gns')
    outputs = ET.Element('outputs')
    for file in f_outputs:
        if file == 'ics' and mode.upper() == "LEO_DYN":
            out_ele = ET.SubElement(outputs, 'icsleo')
            out_ele.text = config.get_filename(file, check=False, sattype='leo')
            continue
        if file == 'sp3' and mode.upper() == "LEO_KIN":
            out_ele = ET.SubElement(outputs, 'sp3')
            out_ele.text = config.get_filename(file, check=False, sattype='leo')
            continue
        out_ele = ET.SubElement(outputs, file)
        out_ele.text = config.get_filename(file, check=False, sattype='gns')
    outputs.set('append', 'false')
    outputs.set('verb', '2')
    return inputs, outputs


def _get_receiver(config, use_res_crd=False):
    receiver = ET.Element('receiver')
    # get coordinates from IGS snx file
    f_snx = config.get_filename('sinex', check=True)
    crds_snx = {}
    if not f_snx.isspace():
        crds_snx = gt.read_snxfile(f_snx, config.stalist())
    # get coordinates from GREAT residuals file
    if use_res_crd:
        crds_res = gt.get_crd_res(config)
    else:
        crds_res = {}
    # get receiver elements
    for site in config.stalist():
        if site in crds_snx.keys():
            ele = ET.SubElement(receiver, 'rec')
            ele.set('X',  f"{crds_snx[site][0]:20.8f}")
            ele.set('Y',  f"{crds_snx[site][2]:20.8f}")
            ele.set('Z',  f"{crds_snx[site][4]:20.8f}")
            ele.set('dX', f"{crds_snx[site][1]:8.4f}")
            ele.set('dY', f"{crds_snx[site][3]:8.4f}")
            ele.set('dZ', f"{crds_snx[site][5]:8.4f}")
            ele.set('id', f"{site.upper()}")
            ele.set('obj', "SNX")
            continue
        if site in crds_res.keys():
            ele = ET.SubElement(receiver, 'rec')
            ele.set('X', f"{crds_res[site][0]:20.8f}")
            ele.set('Y', f"{crds_res[site][1]:20.8f}")
            ele.set('Z', f"{crds_res[site][2]:20.8f}")
            ele.set('dX', "  0.0001")
            ele.set('dY', "  0.0001")
            ele.set('dZ', "  0.0001")
            ele.set('id', f"{site.upper()}")
            ele.set('obj', "RES")
            continue
    return receiver


def _get_lsq_param(config, mode):
    param = ET.Element('parameters')
    if mode == "POD_EST" or mode == "PCE_EST":
        ele = ET.SubElement(param, 'STA')
        ele.set("ID", "XXXX")
        ele.set("sigCLK", "9000")
        ele.set("sigPOS", "0.1_0.1_0.1")
        ele.set("sigCLK", "9000")
        ele.set("sigZTD", "0.201")
        ele = ET.SubElement(param, 'SAT')
        ele.set("ID", "XXX")
        if config.config['process_scheme']['obs_combination'] == "RAW_ALL":
            ele.set("sigCLK", "9000")
        else:
            ele.set("sigCLK", "5000")
        return param
    for site in config.stalist():
        ele = ET.SubElement(param, 'STA')
        ele.set("ID", site.upper())
        ele.set("sigCLK", "9000")
        ele.set("sigPOS", "100_100_100")
        ele.set("sigCLK", "9000")
        ele.set("sigTropPd", "0.015")
        ele.set("sigZTD", "0.201")
    return param


def _set_ref_clk(config, mode='sat', sats=None):
    ref_sats = ['G08', 'G05', 'E01', 'E02', 'C08', 'R01']
    ref_sites = ['gop6', 'hob2', 'ptbb', 'algo']
    if mode == 'sat':
        for sat in ref_sats:
            if not sats:
                if sat in config.all_gnssat():
                    return sat
            else:
                if sat in sats and sat in config.all_gnssat():
                    return sat
        sat = config.all_gnssat()[0]
        logging.warning(f"Cannot find ref sat in {gt.list2str(ref_sats)}, use the first sat {sat}")
        return sat
    else:
        for site in ref_sites:
            if site in config.stalist():
                return site.upper()
        site = config.stalist()[0]
        logging.warning(f"Cannot find ref site in {gt.list2str(ref_sites)}, use the first site {site}")
        return site


def _generate_updlsq_xml(config, f_xml_out, mode="WL"):
    if mode.upper() == "IFCB":
        mode = "ifcb"
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    # <gen>
    gen = _get_element_gen(config, ['intv', 'sys', 'rec'])
    root.append(gen)
    # <inputs>
    amb_dict = config.xml_ambiguity()
    if mode == "ifcb":
        f_inputs = ['rinexo', 'rinexn', 'ambflag', 'ambflag13', 'biabern']
        inp = _get_element_io(config, 'inputs', f_inputs, check=True)
        root.append(inp)
    else:
        if config.config['process_scheme']['obs_comb'] == "UC":
            inp = ET.SubElement(root, "inputs")
            ele = ET.SubElement(inp, "rinexn")
            ele.text = config.get_filename("rinexn", check=True)
            ele = ET.SubElement(inp, "ambupd")
            ele.text = config.get_filename("ambupd_in", check=True)
            if mode == "NL":
                ele = ET.SubElement(inp, "upd")
                if int(config.config['process_scheme']['frequency']) > 2:
                    ele.text = config.get_filename("upd_wl", check=True) + " " + \
                               config.get_filename("upd_ewl", check=True)
                else:
                    ele.text = config.get_filename("upd_wl", check=True)
                if amb_dict['carrier_range'].upper() == "YES":
                    ele = ET.SubElement(inp, "ambflag")
                    ele.text = config.get_filename("ambflag", check=True)
                    if int(config.config['process_scheme']['frequency']) > 2:
                        ele = ET.SubElement(inp, "ambflag13")
                        ele.text = config.get_filename("ambflag13", check=True)
        else:
            if mode == "WL":
                f_inputs = ['rinexo', 'rinexn', 'ambflag', 'biabern']
                inp = _get_element_io(config, 'inputs', f_inputs, check=True)
            elif mode == "EWL":
                f_inputs = ['rinexo', 'rinexn', 'ambflag', 'ambflag13', 'biabern', 'ifcb']
                inp = _get_element_io(config, 'inputs', f_inputs, check=True)
            elif mode == "EWL24":
                f_inputs = ['rinexo', 'rinexn', 'ambflag', 'ambflag14', 'biabern']
                inp = _get_element_io(config, 'inputs', f_inputs, check=True)
            elif mode == "EWL25":
                f_inputs = ['rinexo', 'rinexn', 'ambflag', 'ambflag15', 'biabern']
                inp = _get_element_io(config, 'inputs', f_inputs, check=True)
            elif mode == "NL":
                inp = _get_element_io(config, 'inputs', ['rinexn'], check=True)
                ele = ET.SubElement(inp, "ambupd")
                ele.text = config.get_filename("ambupd_in", check=True)
                ele = ET.SubElement(inp, "upd")
                ele.text = config.get_filename("upd_wl", check=True)
                if amb_dict['carrier_range'].upper() == "YES":
                    ele = ET.SubElement(inp, "ambflag")
                    ele.text = config.get_filename("ambflag", check=True)
            root.append(inp)
    # <outputs>
    out = ET.SubElement(root, "outputs")
    out_ele = ET.SubElement(out, "log")
    out_ele.text = "LOGRT.log"
    out_ele = ET.SubElement(out, "upd")
    if mode == "WL":
        out_ele.text = config.get_filename("upd_wl")
    elif mode == "EWL":
        out_ele.text = config.get_filename("upd_ewl")
    elif mode == "EWL24":
        out_ele.text = config.get_filename("upd_ewl24")
    elif mode == "EWL25":
        out_ele.text = config.get_filename("upd_ewl25")
    elif mode == "ifcb":
        out_ele.text = config.get_filename("ifcb")
    elif mode == "NL":
        out_ele.text = config.get_filename("upd_nl")
    if mode == "NL" and amb_dict['carrier_range'].upper() == "YES":
        out_ele = ET.SubElement(out, "ambflag_dir")
        out_ele.text = config.get_filename("ambflagdir")
    out.set('verb', '2')
    # <gps> <bds> <gal> <glo>
    for gns_sys in config.gnssys().split():
        gns = ET.Element(gns_sys.lower())
        GNS_INFO = get_gns_info(gns_sys, config.sat_rm(), config.band(gns_sys))
        sat = ET.SubElement(gns, 'sat')
        sat.text = gt.list2str(GNS_INFO['sat'])
        mfreq = config.gnsfreq(gns_sys)
        if mode == "EWL25" and mfreq < 5:
            logging.critical(f"UPD mode is EWL25 while {gns_sys} frequency is {mfreq}")
            raise SystemExit(f"UPD mode is EWL25 while {gns_sys} frequency is {mfreq}")
        if mode == "EWL24" and mfreq < 4:
            logging.critical(f"UPD mode is EWL24 while {gns_sys} frequency is {mfreq}")
            raise SystemExit(f"UPD mode is EWL24 while {gns_sys} frequency is {mfreq}")
        if mode == "EWL25":
            upd_band = GNS_INFO['band'][0:2] + [GNS_INFO['band'][4]]
        elif mode == "EWL24":
            upd_band = GNS_INFO['band'][0:2] + [GNS_INFO['band'][3]]
        else:
            upd_band = GNS_INFO['band'][0:3]
        band = ET.SubElement(gns, 'band')
        band.text = gt.list2str(upd_band)
        freq = ET.SubElement(gns, 'freq')
        freq.text = gt.list2str(list(range(1, 4)))
        root.append(gns)
    # <process>
    proc = ET.SubElement(root, 'process')
    for key, val in config.xml_process().items():
        if key != 'obs_combination':
            continue
        if mode == "ifcb":
            proc.set(key, "IONO_FREE")
        else:
            proc.set(key, val)
    # <ambiguity>
    amb = ET.SubElement(root, "ambiguity")
    upd = ET.SubElement(amb, "upd")
    if mode == "NL":
        upd_ele = ET.SubElement(amb, "carrier_range_out")
        upd_ele.text = amb_dict['carrier_range'].upper()
    upd.text = mode
    # write new xml
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _generate_ambfix_xml(config, f_xml_out, mode='SD'):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    # <gen>
    gen = _get_element_gen(config, ['intv', 'sys', 'rec'])
    root.append(gen)
    # <gps> <bds> <gal> <glo>
    for gns in _get_element_gns(config):
        root.append(gns)
    # <inputs>
    f_inputs = ['rinexo', 'biabern', 'recover']
    if mode == 'SD':
        f_inputs.append('upd')
    inp = _get_element_io(config, 'inputs', f_inputs, check=True)
    root.append(inp)
    # <outputs>
    out = ET.SubElement(root, 'outputs')
    if mode == 'SD':
        out_ele = ET.SubElement(out, 'ambcon_leo')
    else:
        out_ele = ET.SubElement(out, 'ambcon')
    out_ele.text = config.get_filename('ambcon')
    out.set('verb', '2')
    # <ambfix>
    ambfix = _get_ambfix(config)
    root.append(ambfix)
    ambfix = ET.SubElement(root, 'ambiguity')
    # <process>
    proc = ET.SubElement(root, 'process')
    for key, val in config.xml_process().items():
        proc.set(key, val)
    proc.set('ambfix', 'true')
    # write new xml
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _get_ambfix(config, fix_mode="ROUND"):
    ambfix = ET.Element('ambiguity')
    amb_ele = ET.SubElement(ambfix, "fix_mode")
    amb_ele.text = fix_mode
    amb_ele = ET.SubElement(ambfix, 'upd_mode')
    if config.is_integer_clock():
        if config.is_integer_clock_osb():
            amb_ele.text = "OSB"
        else:
            amb_ele.text = "IRC"
    else:
        amb_ele.text = "UPD"
    for key, val in config.xml_ambiguity().items():
        if key == 'upd_mode' or key == 'fix_mode':
            continue
        if key == 'widelane_decision' or key == 'extra_widelane_decision' or key == 'narrowlane_decision':
            amb_ele = ET.SubElement(ambfix, key)
            amb_ele.set('maxdev', val[0])
            amb_ele.set('maxsig', val[1])
            amb_ele.set('alpha', val[2])
        else:
            amb_ele = ET.SubElement(ambfix, key)
            amb_ele.text = val
    return ambfix


def _generate_edtres_xml(config, f_xml_out, nshort=120, jump=100, bad=100, mode="L12", edt_amb=False, all_sites=False):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    if mode == "L12":
        f_inputs = ['ambflag']
    elif mode == "L13":
        f_inputs = ['ambflag13']
    inp = _get_element_io(config, 'inputs', f_inputs, check=True)
    ele = ET.SubElement(inp, "recover")
    if all_sites:
        ele.text = config.get_filename("recover_all", check=True)
    else:
        ele.text = config.get_filename("recover_in", check=True)
    root.append(inp)
    f_outputs = ['sum']
    out = _get_element_io(config, 'outputs', f_outputs, check=False)
    root.append(out)
    proc = ET.SubElement(root, 'editres')
    if edt_amb:
        ele_proc = ET.SubElement(proc, 'edt_amb')
        ele_proc.text = 'YES'
    ele_proc = ET.SubElement(proc, 'mode')
    ele_proc.text = str(mode)
    ele_proc = ET.SubElement(proc, 'short_elisp')
    ele_proc.text = str(nshort)
    ele_proc = ET.SubElement(proc, 'jump_elisp')
    ele_proc.text = str(jump)
    ele_proc = ET.SubElement(proc, 'bad_elisp')
    ele_proc.text = str(bad)
    # write new xml
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _generate_oi_xml(config, f_xml_out, sattype='gns'):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    f_inputs = ['blq', 'poleut1', 'oceantide', 'leapsecond',
                'satpars', 'de', 'egm']
    if sattype == 'leo':
        f_inputs.extend(['pannel', 'attitude', 'desaiscopolecoef'])
        inp = _get_element_io(config, 'inputs', f_inputs, check=True, sattype=sattype)
        inp_ele = ET.SubElement(inp, 'solar')
        if config.get_atoms_drag() == "MSISE00":
            inp_ele.text = config.get_filename("solar_MSISE", check=True, sattype=sattype)
        else:
            inp_ele.text = config.get_filename("solar", check=True, sattype=sattype)
        inp_ele = ET.SubElement(inp, 'icsleo')
        inp_ele.text = config.get_filename('ics', sattype='leo')
        gen = _get_element_gen(config)
        root.append(gen)
        leo = ET.SubElement(root, 'LEO')
        leosat = ET.SubElement(leo, 'sat')
        leosat.text = gt.list2str(config.leolist())
    else:
        f_inputs.extend(['ics'])
        inp = _get_element_io(config, 'inputs', f_inputs, check=True, sattype=sattype)
        gen = _get_element_gen(config, ['sys'])
        root.append(gen)
        for gns in _get_element_gns(config):
            root.append(gns)
    root.append(inp)
    out = _get_element_io(config, 'outputs', ['orb'], check=False, sattype=sattype)
    root.append(out)
    # <force_model>: get from template xml file
    force_model = _get_force_model_from_template(config, sattype=sattype)
    if force_model:
        root.append(force_model)
    # write new xml
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _get_force_model_from_template(config, sattype='GNS'):
    xml_temp = ''
    if config.config.has_section('xml_template'):
        if config.config.has_option('xml_template', 'oi'):
            xml_temp = config.config.get('xml_template', 'oi')
    if os.path.isfile(xml_temp):
        leolist = config.leolist()
        ref_tree = ET.parse(xml_temp)
        ref_root = ref_tree.getroot()
        force_model = ref_root.find('force_model')
        force_out = ET.Element('force_model')
        for child in force_model:
            if 'LEO' in sattype.upper():
                if child.get("ID").lower() in leolist or child.get("ID") == "LEO":
                    atmosphere = child.find("atmosphere")
                    atmosphere.set("model", config.get_atoms_drag())
                    force_out.append(child)
            if 'GNS' in sattype.upper():
                if child.get("ID").upper() in config.gnssys().split() or child.get("ID") == "GNS":
                    force_out.append(child)
        return force_out
    else:
        logging.error(f"xml template for oi {xml_temp} not found!")


def _generate_sp3orb_xml(config, f_xml_out, sattype='gns', frame='crs'):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    gen = _get_element_gen(config, ['sys'])
    root.append(gen)
    inp = _get_element_io(config, 'inputs', ['poleut1'], check=True)
    root.append(inp)
    out = _get_element_io(config, 'outputs', ['orb'], check=False, sattype=sattype)
    root.append(out)
    proc = ET.SubElement(root, 'sp3orb')
    sat = ET.SubElement(proc, 'sat')
    sat_all = ""
    inp_ele = ET.SubElement(inp, 'sp3')
    inp_ele.text = config.get_filename('sp3', check=True, sattype=sattype)
    if sattype == 'leo':
        out_ele = ET.SubElement(out, 'icsleo')
        out_ele.text = config.get_filename('ics', sattype='leo')
        sat_all = gt.list2str(config.leolist())
    else:
        out_ele = ET.SubElement(out, 'ics')
        out_ele.text = config.get_filename('ics', sattype='gns')
        for gns_sys in config.gnssys().split():
            sat_all = sat_all + " " + gt.list2str(get_gns_sat(gns_sys, config.sat_rm()))
    sat.text = sat_all
    frm = ET.SubElement(proc, 'frame')
    frm.text = frame
    # <force_model> : get from template xml file
    force_model = _get_force_model_from_template(config, sattype)
    if force_model:
        root.append(force_model)
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _generate_orbfit_xml(config, f_xml_out):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    gen = _get_element_gen(config, ['sys', 'intv'])
    root.append(gen)
    inp = _get_element_io(config, 'inputs', ['orb', 'rinexn', 'ics', 'poleut1'], check=True, sattype='gns')
    root.append(inp)
    out = ET.SubElement(root, 'outputs')
    out_ele = ET.SubElement(out, 'ics')
    out_ele.text = config.get_filename('ics')
    out_ele = ET.SubElement(out, 'orbfit')
    out_ele.text = config.get_filename('orbdif')
    for gns in _get_element_gns(config):
        root.append(gns)
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def get_excsys(config):
    if 'GPS' in config.gnssys():
        return "BDS GAL GLO"
    elif 'GAL' in config.gnssys():
        return "BDS GLO"
    elif "GLO" in config.gnssys():
        return "BDS"
    else:
        return ""


def _generate_orbdif_xml(config, f_xml_out, trans="STRD", excsat="C01 C02 C03 C04 C05 G18 G23"):
    # to be changed, because orbit and orbdif are two GREAT App
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    gen = _get_element_gen(config, ['sys', 'intv'])
    root.append(gen)
    inp = _get_element_io(config, 'inputs', ['orb', 'sp3', 'poleut1'], check=True, sattype='gns')
    root.append(inp)
    out = _get_element_io(config, 'outputs', ['orbdif'], check=False, sattype='gns')
    root.append(out)
    orbdif = ET.SubElement(root, 'orbdif')
    ele = ET.SubElement(orbdif, 'trans')
    ele.text = trans
    ele = ET.SubElement(orbdif, 'excsat')
    ele.text = excsat
    ele = ET.SubElement(orbdif, 'excsys')
    ele.text = get_excsys(config)
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _generate_orbfitleo_xml(config, f_xml_out, fit=False, trans="", unit="mm"):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    gen = _get_element_gen(config, ['sys', 'intv'])
    root.append(gen)
    inp = _get_element_io(config, 'inputs', ['orb', 'poleut1'], check=True, sattype='leo')
    inp_ele = ET.SubElement(inp, 'sp3')
    inp_ele.text = config.get_filename('pso', check=True)
    inp_ele = ET.SubElement(inp, 'icsleo')
    inp_ele.text = config.get_filename('ics', check=True, sattype='leo')
    root.append(inp)
    out = _get_element_io(config, 'outputs', ['orbdif'], check=False, sattype='leo')
    root.append(out)
    xml_log = ET.SubElement(out, 'log')
    xml_log.text = f"LOGRT.xml.log"
    orbdif_ele = ET.SubElement(root, 'orbdifleo')
    leolist = ET.SubElement(orbdif_ele, 'leo')
    leolist.text = gt.list2str(config.leolist())
    ele = ET.SubElement(orbdif_ele, 'trans')
    if trans:
        ele.text = trans
    ele = ET.SubElement(orbdif_ele, 'fit')
    ele.text = str(fit)
    ele = ET.SubElement(orbdif_ele, 'unit')
    ele.text = unit
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _generate_clkdif_xml(config, f_xml_out):
    root = ET.Element('config')
    tree = ET.ElementTree(root)
    f_clk_ref = config.get_filename("rinexc", check=True)
    sats = []
    if f_clk_ref:
        sats = gt.get_rnxc_satlist(f_clk_ref.split()[0])
    else:
        return
    # <gen>
    gen = _get_element_gen(config, ['sys', 'intv'])
    gen_ele = ET.SubElement(gen, "refsat")
    gen_ele.text = _set_ref_clk(config, sats=sats)
    root.append(gen)
    # <inputs>
    inp = ET.SubElement(root, "inputs")
    inp_ele = ET.SubElement(inp, "rinexc_prd")
    inp_ele.text = config.get_filename("satclk", check=True)
    inp_ele = ET.SubElement(inp, "rinexc_ref")
    inp_ele.text = config.get_filename("rinexc", check=True)
    # <outputs>
    out = ET.SubElement(root, "outputs")
    out_ele = ET.SubElement(out, 'log')
    out_ele.text = f"LOGRT.log"
    out_ele = ET.SubElement(out, 'clkdif')
    out_ele.text = config.get_filename("clkdif")
    for gns in _get_element_gns(config):
        root.append(gns)
    _pretty_xml(root, '\t', '\n', 0)
    tree.write(f_xml_out, encoding='utf-8', xml_declaration=True)


def _get_element_gen(config, ele_list=None):
    if ele_list is None:
        ele_list = []
    gen = ET.Element('gen')
    beg = ET.SubElement(gen, 'beg')
    end = ET.SubElement(gen, 'end')
    beg.text = config.timeinfo()[0].datetime()
    end.text = config.timeinfo()[1].datetime()
    if 'intv' in ele_list:
        intv = ET.SubElement(gen, 'int')
        intv.text = config.config.get('process_scheme', 'intv')
    if 'sys' in ele_list:
        sys = ET.SubElement(gen, 'sys')
        sys.text = config.gnssys()
    if 'rec' in ele_list:
        if config.leo_recs():
            rec_leo = ET.SubElement(gen, 'rec')
            rec_leo.set('type', 'leo')
            rec_leo.set('mode', config.config.get('process_scheme', 'leopodmod').upper()[0])
            rec_leo.text = gt.list2str(config.leo_recs(), True)
        if config.stalist():
            rec = ET.SubElement(gen, 'rec')
            rec.text = gt.list2str(config.stalist(), True)
    if 'est' in ele_list:
        estimator = ET.SubElement(gen, 'est')
        estimator.text = config.config.get('process_scheme', 'estimator').upper()
    if 'refsat' in ele_list:
        refsat = ET.SubElement(gen, 'refsat')
        refsat.text = ""
    # sat_rm = ET.SubElement(gen, 'sat_rm')
    return gen


def _get_element_io(config, name, f_inputs, check=True, sattype='gns'):
    inputs = ET.Element(name)
    for file in f_inputs:
        inp_ele = ET.SubElement(inputs, file)
        inp_ele.text = config.get_filename(file, check=check, sattype=sattype)
    return inputs


def _get_element_gns(config):
    gns_ele = []
    for gns_sys in config.gnssys().split():
        gns = ET.Element(gns_sys.lower())
        GNS_INFO = get_gns_info(gns_sys, config.sat_rm(), config.band(gns_sys))
        gns.set('sigma_C', str(GNS_INFO['code']))
        gns.set('sigma_L', str(GNS_INFO['phase']))
        gns.set('sigma_C_LEO', str(GNS_INFO['code_leo']))
        gns.set('sigma_L_LEO', str(GNS_INFO['phase_leo']))
        sat = ET.SubElement(gns, 'sat')
        sat.text = gt.list2str(GNS_INFO['sat'])
        band = ET.SubElement(gns, 'band')
        nfreq = config.config.get('process_scheme', 'frequency')
        mfreq = min(int(nfreq), len(GNS_INFO['band']))
        # mfreq = min(3, len(_GNS_INFO[gns_sys]['band']))
        band.text = gt.list2str(GNS_INFO['band'][0:mfreq])
        freq = ET.SubElement(gns, 'freq')
        freq.text = gt.list2str(list(range(1, mfreq + 1)))
        gns_ele.append(gns)
    return gns_ele


def _auto_wrap(line, intent, linelen=60):
    if isinstance(line, list):
        parts = line
    else:
        parts = line.split()
    info = ''
    newline = 1
    for part in parts:
        info = info + ' ' + part
        if len(info) >= newline * linelen + (1 + len(intent)) * (newline - 1):
            if newline == 1:
                linelen = len(info)
            info = info + '\n' + intent
            newline += 1
    info = info.rstrip()
    return info


def _pretty_xml(element, indent='\t', newline='\n', level=0):
    """
    element:  xml node
    indent:   '\t'
    newline:  '\n'
    """
    if element:
        if (element.text is None) or element.text.isspace():
            element.text = newline + indent * (level + 1)
        else:
            element.text = newline + indent * (level + 1) + element.text.strip() + newline + indent * (level + 1)
    else:
        if not element.text is None:
            if len(element.text) > 60:
                element.text = newline + indent * (level + 1) + _auto_wrap(element.text, indent * (
                        level + 1)) + newline + indent * level
                element.tail = newline + indent * level
            else:
                element.text = ' ' + element.text + ' '
    temp = list(element)
    for subelement in temp:
        if temp.index(subelement) < (len(temp) - 1):
            subelement.tail = newline + indent * (level + 1)
        else:
            subelement.tail = newline + indent * level
        _pretty_xml(subelement, indent, newline, level=level + 1)

from concurrent.futures import ThreadPoolExecutor
import subprocess
import platform
import xml.etree.ElementTree as ET
import os
import logging
from .gnss_tools import timeblock, split_receivers, get_rnxc_satlist, pretty_xml
from .gnss_config import GnssConfig
from .constants import MAX_THREAD, gns_sat


def _run_cmd(cmd):
    logging.debug(cmd)
    try:
        subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError:
        logging.error(f"RunTimeError: {cmd}")
        return False


class GrtCmd:
    grt_app = ''

    def __init__(self, config: GnssConfig, label=None, nmp=1, stop=True, str_args='', **kwargs):
        if label is None:
            label = self.grt_app
        if not os.path.isdir(config.grt_bin):
            raise ValueError(f"GREAT Bin {config.grt_bin} not exist")

        self._config = config
        if platform.system() == 'Windows':
            self.grt_exe = os.path.join(self._config.grt_bin, f'{self.grt_app}.exe')
        else:
            self.grt_exe = os.path.join(self._config.grt_bin, f'{self.grt_app}')
        self.label = label
        self.xml = os.path.join('xml', f'{self.label}.xml')
        self.log = os.path.join('tmp', f'{self.label}.log')
        self.nmp = min(nmp, MAX_THREAD)
        self.stop = stop
        self.str_args = str_args

    def form_xml(self, ithd=-1):
        raise NotImplementedError

    def xml_receiver(self):
        f_preedit = os.path.join('xml', 'preedit.xml')
        rec = None
        if os.path.isfile(f_preedit):
            ref_tree = ET.parse(f_preedit)
            ref_root = ref_tree.getroot()
            rec = ref_root.find('receiver')
        
        if not rec:
            rec = self._config.get_xml_receiver()
        return rec

    def prepare_xml(self, ithd=-1):
        root = self.form_xml(ithd)
        tree = ET.ElementTree(root)
        pretty_xml(root, '\t', '\n', 0)
        tree.write(self.xml, encoding='utf-8', xml_declaration=True)

    def form_cmd(self):
        if self.nmp < 2:
            self.prepare_xml()
            return [f"{self.grt_exe} -x {self.xml} {self.str_args} > {self.log} 2>&1"]
        else:
            all_sites = self._config.site_list
            all_leos = self._config.leo_list
            sites, leos = split_receivers(self._config, self.nmp)
            cmds = []
            for i in range(self.nmp):
                if i >= len(sites):
                    self._config.site_list = []
                    self._config.leo_list = leos[i - len(sites)]
                else:
                    self._config.site_list = sites[i]
                    self._config.leo_list = []
                self.xml = os.path.join('xml', f"{self.label}{i + 1:0>2d}.xml")
                self.log = os.path.join('tmp', f"{self.label}{i + 1:0>2d}.log")
                self.prepare_xml(i)
                cmds.append(f"{self.grt_exe} -x {self.xml} {self.str_args} > {self.log} 2>&1")

            self._config.site_list = all_sites
            self._config.leo_list = all_leos
            return cmds

    def check(self):
        if not os.path.isfile(self.grt_exe):
            raise ValueError(f"GREAT App {self.grt_exe} not exist")
        if not os.path.isdir('xml'):
            os.makedirs('xml')
        if not os.path.isdir('tmp'):
            os.makedirs('tmp')
        self.nmp = min(self.nmp, len(self._config.all_sites))
        if self.nmp == 0:
            self.nmp = 1
        return True

    def run(self):
        if not self.check():
            if self.stop:
                raise RuntimeError('check failed')
            return

        cmds = self.form_cmd()
        with timeblock(f'Normal end [{len(cmds):0>2d}] {self.label}'):
            with ThreadPoolExecutor(self.nmp) as pool:
                results = pool.map(_run_cmd, cmds)

        for rst in results:
            if self.stop and not rst:
                raise RuntimeError


class GrtTurboedit(GrtCmd):
    grt_app = 'great_turboedit'

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec']))
        root.extend(self._config.get_xml_gns())
        if self._config.site_list:
            root.append(self.xml_receiver())
        isleo = True if self._config.leo_list else False
        proc = self._config.get_xml_process()
        if isleo or self._config.crd_constr.startswith('K'):
            proc.set('pos_kin', 'true')
        root.append(proc)
        root.append(self._config.get_xml_turboedit(isleo))
        root.append(self._config.get_xml_inputs(['rinexo', 'rinexn']))
        out = ET.SubElement(root, 'outputs', {'append': 'false', 'verb': '1'})
        elem = ET.SubElement(out, 'log')
        elem.text = self.xml.replace(".xml", ".log")
        elem = ET.SubElement(out, 'ambflag_dir')
        elem.text = ' '.join(self._config.get_xml_file('ambflagdir'))
        return root


class GrtClockRepair(GrtCmd):
    grt_app = 'great_clockrepair'

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec']))
        root.append(self._config.get_xml_inputs(['rinexo']))
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'obs_dir')
        elem.text = ' '.join(self._config.get_xml_file('obs_trimcor'))
        return root


class GrtPreedit(GrtCmd):
    grt_app = 'great_preedit'

    def __init__(self, config: GnssConfig, stop=True, crd=False):
        super().__init__(config, 'preedit', nmp=1, stop=stop)
        self.crd = crd

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec'] if self.crd else ['intv', 'sys']))
        root.extend(self._config.get_xml_gns())
        root.append(self._config.get_xml_force())
        if self.crd:
            root.append(self._config.get_xml_inputs(['rinexo', 'rinexn', 'poleut1', 'sinex'], check=True))
        else:
            root.append(self._config.get_xml_inputs(['rinexn', 'poleut1'], check=True))
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'ics')
        elem.text = ' '.join(self._config.get_xml_file('ics'))
        return root


class GrtOi(GrtCmd):
    grt_app = 'great_oi'

    def __init__(self, config, label=None, stop=True, sattype='gns'):
        str_args = '-leo' if sattype == 'leo' else ''
        self.sattype = sattype
        super().__init__(config, label, nmp=1, stop=stop, str_args=str_args)

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['sys']))
        ET.SubElement(root, 'process', attrib={'num_threads': str(min(MAX_THREAD, 6))})
        root.append(self._config.get_xml_force(self.sattype))
        f_inputs = ['blq', 'poleut1', 'oceantide', 'leapsecond', 'satpars', 'de', 'egm']
        if self.sattype == 'leo':
            f_inputs.extend(['pannel', 'attitude', 'desaiscopolecoef'])
            inp = self._config.get_xml_inputs(f_inputs, sattype='leo')
            elem = ET.SubElement(inp, 'solar')
            if self._config.atoms_drag == "MSISE00":
                elem.text = ' '.join(self._config.get_xml_file("solar_MSISE", check=True, sattype='leo'))
            else:
                elem.text = ' '.join(self._config.get_xml_file("solar", check=True, sattype='leo'))
            elem = ET.SubElement(inp, 'icsleo')
            elem.text = ' '.join(self._config.get_xml_file('ics', check=True, sattype='leo'))
            leo = ET.SubElement(root, 'LEO')
            leosat = ET.SubElement(leo, 'sat')
            leosat.text = ' '.join(self._config.leo_sats)
        else:
            f_inputs.extend(['ics'])
            inp = self._config.get_xml_inputs(f_inputs)
            root.extend(self._config.get_xml_gns())
        root.append(inp)
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'orb')
        elem.text = ' '.join(self._config.get_xml_file('orb', sattype=self.sattype))
        return root


class GrtSp3orb(GrtOi):
    grt_app = 'great_sp3orb'

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['sys']))
        root.append(self._config.get_xml_force(self.sattype))
        proc = ET.SubElement(root, 'sp3orb')
        elem = ET.SubElement(proc, 'frame')
        elem.text = 'crs'
        elem = ET.SubElement(proc, 'sat')
        elem.text = ' '.join(self._config.leo_sats) if self.sattype == 'leo' else ' '.join(self._config.all_gnssat)
        
        inps = ET.SubElement(root, 'inputs')
        elem = ET.SubElement(inps, 'sp3')
        elem.text = ' '.join(self._config.get_xml_file('sp3_inp', sattype=self.sattype, check=True))
        elem = ET.SubElement(inps, 'poleut1')
        elem.text = ' '.join(self._config.get_xml_file('poleut1', sattype=self.sattype, check=True))
        # root.append(self._config.get_xml_inputs(['poleut1', 'sp3'], sattype=self.sattype))
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'orb')
        elem.text = ' '.join(self._config.get_xml_file('orb', sattype=self.sattype))
        if self.sattype == 'leo':
            elem = ET.SubElement(out, 'icsleo')
            elem.text = ' '.join(self._config.get_xml_file('ics', sattype='leo'))
        else:
            elem = ET.SubElement(out, 'ics')
            elem.text = ' '.join(self._config.get_xml_file('ics', sattype='gns'))
        return root


class GrtOrbsp3(GrtOi):
    grt_app = 'great_orbsp3'

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv']))
        proc = ET.SubElement(root, 'orbsp3')
        elem = ET.SubElement(proc, 'sat')
        elem.text = ' '.join(self._config.leo_sats) if self.sattype == 'leo' else ' '.join(self._config.all_gnssat)
        root.append(self._config.get_xml_inputs(['poleut1', 'orb'], sattype=self.sattype))
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'sp3')
        elem.text = ' '.join(self._config.get_xml_file('sp3_out'))
        return root


class GrtOrbfit(GrtCmd):
    grt_app = 'great_orbfit'

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['sys', 'intv']))
        root.extend(self._config.get_xml_gns())
        root.append(self._config.get_xml_inputs(['orb', 'rinexn', 'ics', 'poleut1']))
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'ics')
        elem.text = ' '.join(self._config.get_xml_file('ics'))
        elem = ET.SubElement(out, 'orbfit')
        elem.text = ' '.join(self._config.get_xml_file('orbdif'))
        return root


class GrtOrbdif(GrtCmd):
    grt_app = 'great_orbdif'

    def __init__(self, config: GnssConfig, label=None, nmp=1, stop=False, trans='STRD',
                 excsat="C01 C02 C03 C04 C05 G18 G23"):
        super().__init__(config, label, nmp, stop)
        self.trans = trans
        self.excsat = excsat

    @property
    def excsys(self):
        if 'GPS' in self._config.gsystem:
            return "BDS GAL GLO"
        elif 'GAL' in self._config.gsystem:
            return "BDS GLO"
        elif "GLO" in self._config.gsystem:
            return "BDS"
        else:
            return ""

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['sys', 'intv']))
        orbdif = ET.SubElement(root, 'orbdif')
        for opt in ['trans', 'excsat', 'excsys']:
            elem = ET.SubElement(orbdif, opt)
            elem.text = getattr(self, opt, '')
        root.append(self._config.get_xml_inputs(['orb', 'sp3', 'poleut1']))
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'orbdif')
        elem.text = ' '.join(self._config.get_xml_file('orbdif'))
        return root


class GrtOrbfitLeo(GrtCmd):
    grt_app = 'great_orbfitleo'

    def __init__(self, config: GnssConfig, label=None, nmp=1, stop=True, trans='', fit=False, unit="mm"):
        super().__init__(config, label, nmp, stop)
        self.trans = trans
        self.fit = fit
        self.unit = unit

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['sys', 'intv']))
        orbfitleo = ET.SubElement(root, 'orbdifleo')
        elem = ET.SubElement(orbfitleo, 'leo')
        elem.text = ' '.join(self._config.leo_sats)
        for opt in ['trans', 'fit', 'unit']:
            elem = ET.SubElement(orbfitleo, opt)
            elem.text = str(getattr(self, opt, ''))
        inp = self._config.get_xml_inputs(['poleut1'])
        elem = ET.SubElement(inp, 'orb')
        elem.text = ' '.join(self._config.get_xml_file('orb', check=True, sattype='leo'))
        elem = ET.SubElement(inp, 'sp3')
        elem.text = ' '.join(self._config.get_xml_file('pso', check=True))
        elem = ET.SubElement(inp, 'icsleo')
        elem.text = ' '.join(self._config.get_xml_file('ics', check=True, sattype='leo'))
        root.append(inp)
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'orbdif')
        elem.text = ' '.join(self._config.get_xml_file('orbdif', sattype='leo'))
        return root


class GrtClkdif(GrtCmd):
    grt_app = 'great_clkdif'

    def __init__(self, config, label=None, stop=False):
        super().__init__(config, label, stop=stop)

    def ref_clk_sats(self):
        if self._config.orb_ac.startswith('clk') or self._config.orb_ac in ['grt', 'cnt']:
            return [s for gs in self._config.gsystem for s in gns_sat(gs)]
        f_clks = self._config.get_xml_file('rinexc', check=True)
        if not f_clks:
            return []
        return get_rnxc_satlist(f_clks[0])

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        gen = self._config.get_xml_gen(['sys', 'intv'])
        elem = ET.SubElement(gen, 'refsat')
        elem.text = self._config.set_ref_clk(mode='sat', sats=self.ref_clk_sats())
        root.append(gen)
        root.extend(self._config.get_xml_gns())
        inp = ET.SubElement(root, 'inputs')
        elem = ET.SubElement(inp, "rinexc_prd")
        if self._config.lsq_mode == 'EPO':
            elem.text = ' '.join(self._config.get_xml_file('satclk_epo', check=True))
        else:
            elem.text = ' '.join(self._config.get_xml_file('satclk', check=True))
        elem = ET.SubElement(inp, 'rinexc_ref')
        fname = 'ssrclk' if self._config.orb_ac.startswith('clk') else 'rinexc'
        elem.text = ' '.join(self._config.get_xml_file(fname, check=True))
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'clkdif')
        elem.text = ' '.join(self._config.get_xml_file('clkdif'))
        return root

    def check(self):
        if super().check():
            if self.ref_clk_sats():
                return True
        return False


class GrtEditres(GrtCmd):
    grt_app = 'great_editres'

    def __init__(self, config, label=None, nmp=1, stop=True,
                 nshort=600, bad=50, jump=50, freq='LC12', mode='L12', edt_amb=False, all_sites=False):
        super().__init__(config, label, nmp, stop)
        self.short_elisp = str(nshort)
        self.bad_elisp = str(bad)
        self.jump_elisp = str(jump)
        self.freq = freq
        self.mode = mode
        self.edt_amb = 'YES' if edt_amb else 'NO'
        self.all_sites = all_sites

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        proc = ET.SubElement(root, 'editres')
        for opt in ['edt_amb', 'freq', 'mode', 'short_elisp', 'jump_elisp', 'bad_elisp']:
            elem = ET.SubElement(proc, opt)
            elem.text = getattr(self, opt, '')
        f_inputs = ['ambflag']
        if self.mode == "L13" or self.mode == "L3":
            f_inputs = [f"ambflag13"]
        elif self.mode == "L14" or self.mode == "L4":
            f_inputs = [f"ambflag14"]
        elif self.mode == "L15" or self.mode == "L5":
            f_inputs = [f"ambflag15"]
        inp = self._config.get_xml_inputs(f_inputs)
        elem = ET.SubElement(inp, "recover")
        elem.text = ' '.join(self._config.get_xml_file("recover_all", check=True)) if self.all_sites \
            else ' '.join(self._config.get_xml_file("recover_in", check=True))
        root.append(inp)
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'sum')
        elem.text = ' '.join(self._config.get_xml_file('sum'))
        return root


class GrtConvobs(GrtCmd):
    grt_app = 'great_convobs'

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec']))
        root.extend(self._config.get_xml_gns())
        f_inputs = ['rinexo', 'ambflag']
        if self._config.freq > 2:
            f_inputs.append('ambflag13')
        root.append(self._config.get_xml_inputs(f_inputs))
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'obs_dir')
        elem.text = ' '.join(self._config.get_xml_file('obs_fix'))
        return root


class GrtUpdlsq(GrtCmd):
    grt_app = 'great_updlsq'
    updlsq_mode = ['IFCB', 'NL', 'WL', 'EWL', 'EWL24', 'EWL25']

    def __init__(self, config, mode: str, label=None, nmp=1, stop=True):
        super().__init__(config, label, nmp, stop)
        self.mode = mode.upper()
        if self.mode not in self.updlsq_mode:
            raise TypeError('Wrong updlsq mode')

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec']))
        # <gps> <bds> <gal> <glo>
        if not self.mode.startswith('EWL'):
            root.extend(self._config.get_xml_gns())
        else:
            for gs in self._config.gsystem:
                gns = ET.SubElement(root, gs.lower())
                band = self._config.band[gs]
                mfreq = self._config.gnsfreq(gs)
                if self.mode == 'EWL25':
                    if mfreq < 5:
                        raise ValueError('ewl25 freq must >= 5')
                    upd_band = f'{band[0]} {band[1]} {band[4]}'
                elif self.mode == 'EWL24':
                    if mfreq < 4:
                        raise ValueError('ewl24 freq must >= 4')
                    upd_band = f'{band[0]} {band[1]} {band[3]}'
                else:
                    if mfreq < 3:
                        raise ValueError('ewl freq must >= 3')
                    upd_band = f'{band[0]} {band[1]} {band[2]}'
                elem = ET.SubElement(gns, 'sat')
                elem.text = ' '.join(gns_sat(gs, self._config.sat_rm))
                elem = ET.SubElement(gns, 'band')
                elem.text = upd_band
                elem = ET.SubElement(gns, 'freq')
                elem.text = '1 2 3'
        # <process>
        root.append(self._config.get_xml_process())
        # <ambiguity>
        amb = self._config.get_xml_ambiguity()
        elem = ET.SubElement(amb, "upd")
        elem.text = self.mode
        root.append(amb)
        # <inputs>
        if self.mode == "IFCB":
            root.append(self._config.get_xml_inputs(['rinexo', 'rinexn', 'ambflag', 'ambflag13', 'biabern']))
        else:
            if self._config.obs_comb == 'UC':
                f_inputs = ['rinexn', 'upd'] if self.mode == 'NL' else ['rinexn']
                if self.mode == 'NL' and self._config.carrier_range_out:
                    f_inputs.append('ambflag')
                    if self._config.freq > 2:
                        f_inputs.append('ambflag13')
                self._config.upd_mode = 'IRC'
                inp = self._config.get_xml_inputs(f_inputs)
                self._config.upd_mode = 'UPD'
                elem = ET.SubElement(inp, "ambupd")
                elem.text = ' '.join(self._config.get_xml_file("ambupd_in", check=True))
                root.append(inp)
            else:
                if self.mode == 'EWL':
                    root.append(self._config.get_xml_inputs(['rinexo', 'rinexn', 'ambflag', 'ambflag13', 'biabern', 'ifcb']))
                elif self.mode == "EWL24":
                    root.append(self._config.get_xml_inputs(['rinexo', 'rinexn', 'ambflag', 'ambflag14', 'biabern']))
                elif self.mode == 'EWL25':
                    root.append(self._config.get_xml_inputs(['rinexo', 'rinexn', 'ambflag', 'ambflag15', 'biabern']))
                elif self.mode == 'WL':
                    root.append(self._config.get_xml_inputs(['rinexo', 'rinexn', 'ambflag', 'biabern']))
                else:
                    f_inputs = ['rinexn', 'upd']
                    if self._config.carrier_range_out:
                        f_inputs.append('ambflag')
                        if self._config.freq > 2:
                            f_inputs.append('ambflag13')
                    self._config.upd_mode = 'IRC'
                    inp = self._config.get_xml_inputs(f_inputs)
                    self._config.upd_mode = 'UPD'
                    elem = ET.SubElement(inp, "ambupd")
                    elem.text = ' '.join(self._config.get_xml_file("ambupd_in", check=True))
                    root.append(inp)
        # <outputs>
        out = ET.SubElement(root, "outputs")
        elem = ET.SubElement(out, "upd")
        if self.mode == "IFCB":
            elem.text = ' '.join(self._config.get_xml_file('ifcb'))
        elif self.mode == "EWL":
            elem.text = ' '.join(self._config.get_xml_file('upd_ewl'))
        elif self.mode == "EWL24":
            elem.text = ' '.join(self._config.get_xml_file('upd_ewl24'))
        elif self.mode == "EWL25":
            elem.text = ' '.join(self._config.get_xml_file('upd_ewl25'))
        elif self.mode == "WL":
            elem.text = ' '.join(self._config.get_xml_file('upd_wl'))
        else:
            elem.text = ' '.join(self._config.get_xml_file('upd_nl'))
        if self.mode == "NL" and self._config.carrier_range_out:
            out_ele = ET.SubElement(out, "ambflag_dir")
            out_ele.text = ' '.join(self._config.get_xml_file('ambflagdir'))
        return root


class GrtAmbfix(GrtCmd):
    grt_app = 'great_ambfix'
    amb_types = ["DD", "SD", "UD"]

    def __init__(self, config, mode: str, label=None, nmp=1, stop=True, all_sites=False):
        super().__init__(config, label, nmp, stop)
        self.all_sites = all_sites
        self.mode = mode.upper()
        if self.mode not in self.amb_types:
            raise TypeError('Wrong ambiguity types')

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec']))
        root.extend(self._config.get_xml_gns())
        root.append(self._config.get_xml_receiver())
        # <process>
        proc = ET.SubElement(root, 'process', attrib={
            'obs_combination': self._config.obs_combination,
            'frequency': str(self._config.freq), 'num_threads': str(min(MAX_THREAD, 6, int(16 / self.nmp)))})
        elem = ET.SubElement(proc, 'read_ofile_mode')
        elem.text = "REALTIME"
        # <ambiguity>
        amb = self._config.get_xml_ambiguity()
        elem = ET.SubElement(amb, 'fix_mode')
        elem.text = 'ROUND'
        elem = ET.SubElement(amb, 'amb_type')
        elem.text = self.mode
        root.append(amb)
        proc = self._config.get_xml_process()
        proc.set('ambfix', 'true')
        # <inputs>
        f_inps = ['biabern']
        if self._config.obs_comb == "IF":
            f_inps.append('rinexo')
        if self.mode != "DD":
            f_inps.append('upd')
        inp = self._config.get_xml_inputs(f_inps)
        elem = ET.SubElement(inp, "recover")
        elem.text = ' '.join(self._config.get_xml_file("recover_all", check=True)) if self.all_sites \
            else ' '.join(self._config.get_xml_file("recover_in", check=True))
        root.append(inp)
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'ambcon')
        # f_ambcon = self._config.get_xml_file('ambcon')[0]
        # if ithd >= 0:
        #     f_ambcon += f"_{ithd+1:0>2d}"
        elem.text = ' '.join(self._config.get_xml_file("ambcon", check=False))
        return root


class GrtAmbfixD(GrtCmd):
    grt_app = 'great_ambfixD'

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec']))
        root.extend(self._config.get_xml_gns())
        amb = self._config.get_xml_ambiguity()
        elem = ET.SubElement(amb, 'fix_mode')
        elem.text = 'ROUND'
        root.append(amb)
        proc = self._config.get_xml_process()
        proc.set('ambfix', 'true')
        inp = self._config.get_xml_inputs(['rinexo', 'biabern', 'upd'])
        elem = ET.SubElement(inp, "recover")
        elem.text = ' '.join(self._config.get_xml_file('recover_in', check=True))
        root.append(inp)
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'ambcon_leo')
        elem.text = ' '.join(self._config.get_xml_file('ambcon'))
        return root


class GrtAmbfixDd(GrtCmd):
    grt_app = 'great_ambfixDd'

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec']))
        root.extend(self._config.get_xml_gns())
        amb = self._config.get_xml_ambiguity()
        elem = ET.SubElement(amb, 'fix_mode')
        elem.text = 'ROUND'
        root.append(amb)
        proc = self._config.get_xml_process()
        proc.set('ambfix', 'true')
        inp = self._config.get_xml_inputs(['rinexo', 'biabern'])
        elem = ET.SubElement(inp, "recover")
        elem.text = ' '.join(self._config.get_xml_file('recover_in', check=True))
        root.append(inp)
        out = ET.SubElement(root, 'outputs')
        elem = ET.SubElement(out, 'ambcon')
        elem.text = ' '.join(self._config.get_xml_file('ambcon'))
        return root


class GrtPodlsq(GrtCmd):
    grt_app = 'great_podlsq'
    f_outs = ['ics', 'satclk', 'recclk', 'recover']

    def __init__(self, config, label=None, stop=True, str_args='', fix_amb=False, use_res_crd=False):
        super().__init__(config, label, nmp=1, stop=stop, str_args=str_args)
        self.fix_amb = fix_amb
        self.use_res_crd = use_res_crd
        if self.fix_amb and not self.str_args:
            self.str_args = '-ambfix'

    def xml_receiver(self):
        f_preedit = os.path.join('xml', 'preedit.xml')
        if self.use_res_crd:
            rec = self._config.get_xml_receiver(True)
        else:
            rec  = None
            if os.path.isfile(f_preedit):
                ref_tree = ET.parse(f_preedit)
                ref_root = ref_tree.getroot()
                rec = ref_root.find('receiver')
        
            if not rec:
                rec = self._config.get_xml_receiver()
        return rec

    def xml_parameter(self):
        param = ET.Element('parameters')
        ET.SubElement(param, 'STA', attrib={
            'ID': 'XXXX', 'sigCLK': '9000', 'sigPOS': '0.1_0.1_0.1', 'sigZTD': '0.201'
        })
        if self._config.obs_comb == 'UC':
            ET.SubElement(param, 'SAT', attrib={'ID': 'XXX', 'sigCLK': '9000'})
        else:
            ET.SubElement(param, 'SAT', attrib={'ID': 'XXX', 'sigCLK': '5000'})
        return param

    def xml_proc(self):
        proc = self._config.get_xml_process()
        proc.set('ambfix', 'true' if self.fix_amb and self._config.lsq_mode == 'LSQ' else 'false')
        # real time or simulating real time, use satellite as reference
        if self._config.real_time or self._config.ultra_sp3:
            proc.set('ref_clk', self._config.set_ref_clk(mode='sat'))
        else:
            proc.set('ref_clk', self._config.set_ref_clk(mode='site'))
        proc.set('sig_ref_clk', '0.001')
        proc.set('num_threads', str(min(MAX_THREAD, 6)))
        proc.set('matrix_remove', 'true')
        proc.set('cmb_equ_multi_thread', 'true')
        # proc.set('sysbias_model', 'ISB+CON' if self._config.lsq_mode == 'LSQ' else 'ISB+WHIT')
        # only ISB, no GLONASS IFB;
        # proc.set('sysbias_model', 'ISB+CON')
        proc.set('lsq_buffer_size', '500')
        elem = ET.SubElement(proc, 'ifb_model')
        elem.text = 'EST_REC_IFB' if self._config.obs_comb == 'UC' else 'NONE'
        return proc

    def xml_inputs(self):
        f_inps = ['rinexo', 'DE', 'poleut1', 'leapsecond', 'atx', 'biabern',
                  'orb', 'ics', 'blq', 'satpars', 'rinexn']
        if 'G' in self._config.gsys and self._config.freq > 2:
            f_inps.append('ifcb')
        if self.fix_amb:
            f_inps.append('ambcon')
        inp = self._config.get_xml_inputs(f_inps)
        elem = ET.SubElement(inp, 'rinexc')
        elem.text = ' '.join(self._config.get_xml_file('clk', check=True))
        return inp

    def xml_outputs(self):
        out = ET.Element('outputs')
        elem = ET.SubElement(out, 'log')
        elem.text = self.xml.replace(".xml", ".log")
        for f in self.f_outs:
            elem = ET.SubElement(out, f)
            elem.text = ' '.join(self._config.get_xml_file(f))
        return out

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec', 'est']))
        root.append(self.xml_receiver())
        root.append(self.xml_parameter())
        # <gps> <glo> <gal> <bds>
        root.extend(self._config.get_xml_gns())
        # <process>
        root.append(self.xml_proc())
        # <turboedit>
        if self._config.real_time or self._config.lite_mode:
            root.append(self._config.get_xml_turboedit(False))
        # <inputs> <outputs>
        root.append(self.xml_inputs())
        root.append(self.xml_outputs())
        return root


class GrtPodleo(GrtPodlsq):

    def __init__(self, config, label=None, stop=True, fix_amb=False):
        super().__init__(config, label, stop=stop, fix_amb=fix_amb)

    def xml_proc(self):
        proc = self._config.get_xml_process()
        proc.set('ambfix', 'true' if self.fix_amb and self._config.lsq_mode == 'LSQ' else 'false')
        proc.set('num_threads', str(min(MAX_THREAD, 6)))
        proc.set('matrix_remove', 'false')
        proc.set('cmb_equ_multi_thread', 'true')
        proc.set('lsq_buffer_size', '500')
        elem = ET.SubElement(proc, 'ifb_model')
        elem.text = 'EST_REC_IFB' if self._config.obs_comb == 'UC' else 'NONE'
        return proc

    def xml_inputs(self):
        f_inps = ['rinexo', 'DE', 'poleut1', 'leapsecond', 'atx', 'biabern']
        if 'G' in self._config.gsys and self._config.freq > 2:
            f_inps.append('ifcb')
        if self.fix_amb:
            f_inps.append('ambcon')
            if self._config.upd_mode != 'OSB':
                f_inps.append('upd')
        if self._config.leo_mode == 'D':
            # LEO Dynamic POD
            f_inps.extend(['orb', 'rinexc', 'ics', 'satpars', 'attitude'])
            inp = self._config.get_xml_inputs(f_inps)
            elem = ET.SubElement(inp, 'rinexc')
            elem.text = ' '.join(self._config.get_xml_file('rinexc_all', check=True))
            elem = ET.SubElement(inp, 'icsleo')
            elem.text = ' '.join(self._config.get_xml_file('ics', check=True, sattype='leo'))
            elem = ET.SubElement(inp, 'orb')
            elem.text = ' '.join(self._config.get_xml_file('orb', check=True, sattype='gnsleo'))
        else:
            # LEO Kinematic POD
            f_inps.extend(['orb', 'rinexc', 'satpars', 'attitude'])
            inp = self._config.get_xml_inputs(f_inps)
            elem = ET.SubElement(inp, 'rinexc')
            elem.text = ' '.join(self._config.get_xml_file('rinexc_all', check=True))
            elem = ET.SubElement(inp, 'sp3')
            elem.text = ' '.join(self._config.get_xml_file('sp3', check=True, sattype='gnsleo'))
        return inp

    def xml_outputs(self):
        out = ET.Element('outputs')
        elem = ET.SubElement(out, 'log')
        elem.text = self.xml.replace(".xml", ".log")
        elem = ET.SubElement(out, 'recclk')
        elem.text = ' '.join(self._config.get_xml_file('recclk', sattype='leo'))
        if self._config.leo_mode == 'D':
            elem = ET.SubElement(out, 'icsleo')
            elem.text = ' '.join(self._config.get_xml_file('ics', sattype='leo'))
        else:
            elem = ET.SubElement(out, 'sp3')
            elem.text = ' '.join(self._config.get_xml_file('sp3', sattype='leo'))
        return out

    def form_xml(self, ithd=-1):
        root = ET.Element('config')
        root.append(self._config.get_xml_gen(['intv', 'sys', 'rec', 'est']))
        # <gps> <glo> <gal> <bds>
        root.extend(self._config.get_xml_gns())
        leo = ET.SubElement(root, 'LEO')
        elem = ET.SubElement(leo, 'sat')
        elem.text = ' '.join(self._config.leo_sats)
        # <process>
        root.append(self.xml_proc())
        # <turboedit>
        if self._config.real_time or self._config.lite_mode:
            root.append(self._config.get_xml_turboedit(False))
        # <inputs> <outputs>
        root.append(self.xml_inputs())
        root.append(self.xml_outputs())
        return root

    def check(self):
        if super().check():
            if self._config.leo_list:
                return True
            logging.error('no LEO satellite to process')
        return False


class GrtPcelsq(GrtPodlsq):
    grt_app = 'great_pcelsq'
    f_outs = ['satclk', 'recclk', 'recover']

    def xml_inputs(self):
        f_inps = ['rinexo', 'DE', 'poleut1', 'leapsecond', 'atx', 'biabern',
                  'rinexn', 'sp3', 'blq', 'satpars', 'sinex']
        if 'G' in self._config.gsys and self._config.freq > 2:
            f_inps.append('ifcb')
        if self.fix_amb:
            f_inps.append('ambcon')
        inp = self._config.get_xml_inputs(f_inps)
        elem = ET.SubElement(inp, 'rinexc')
        elem.text = ' '.join(self._config.get_xml_file('clk', check=True))
        return inp


class GrtPpplsq(GrtPodlsq):
    grt_app = 'great_ppplsq'
    f_outs = ['ppp', 'enu', 'flt', 'ambupd', 'recover']

    def __init__(self, config, label=None, stop=True, nmp=1, fix_amb=False):
        super().__init__(config, label, stop)
        self.fix_amb = fix_amb
        self.nmp = min(nmp, MAX_THREAD)

    def xml_parameter(self):
        param = ET.Element('parameters')
        for site in self._config.site_list:
            ET.SubElement(param, 'STA', attrib={
                'ID': site.upper(), 'sigCLK': '9000', 'sigPOS': '100_100_100',
                'sigTropPd': '0.015', 'sigZTD': '0.201'
            })
        return param

    def xml_proc(self):
        proc = self._config.get_xml_process()
        elem = ET.SubElement(proc, 'ifb_model')
        elem.text = 'EST_REC_IFB' if self._config.obs_comb == 'UC' else 'NONE'
        proc.set('ambfix', 'true' if self.fix_amb and self._config.lsq_mode == 'LSQ' else 'false')
        return proc

    def xml_inputs(self):
        f_inps = ['rinexo', 'DE', 'poleut1', 'leapsecond', 'atx', 'biabern',
                  'rinexn', 'sp3', 'rinexc', 'blq']
        if 'G' in self._config.gsys and self._config.freq > 2:
            f_inps.append('ifcb')
        if self._config.carrier_range:
            f_inps.append('upd')
        elif self.fix_amb:
            f_inps.append('upd' if self._config.lsq_mode == 'EPO' else 'ambcon_all')
        return self._config.get_xml_inputs(f_inps)

    def form_xml(self, ithd=-1):
        if self.fix_amb:
            self._config.set_process(ambiguity='AR')
        else:
            self._config.set_process(ambiguity='F')
        root = super().form_xml()
        if self._config.lsq_mode == 'EPO':
            amb = self._config.get_xml_ambiguity()
            elem = ET.SubElement(amb, 'fix_mode')
            elem.text = 'SEARCH' if self.fix_amb else 'NO'
            root.append(amb)
        return root

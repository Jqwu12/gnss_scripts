import logging
import os
import math
import seaborn as sns
import sys
from datetime import datetime
import pandas as pd
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import GnssTime, read_clkdif_sum, gns_sat, gns_name, GnssConfig, GrtClkdif, timeblock
from gnss_plot import draw_clkdif_std


def eval_one_prod(cen, gns, overwrite=False):
    cf_file = os.path.join(os.path.dirname(__file__), f'cf_{cen}.ini')
    if not os.path.isfile(cf_file):
        return
    config = GnssConfig.from_file(cf_file)
    gsys = config.gsys
    gss = [s for s in gns if s in gsys]
    config.intv = 5

    last_time = GnssTime.from_datetime(datetime.utcnow())
    last_time -= 86400
    first_time = last_time - 7 * 86400
    wkdir = config.workdir
    if not os.path.isdir(wkdir):
        os.makedirs(wkdir)
    os.chdir(wkdir)
    if not os.path.isdir('clkdif'):
        os.makedirs('clkdif')
    if not os.path.isdir('figs'):
        os.makedirs('figs')
    beg_time = GnssTime(first_time.mjd, 0.0)

    cen_refs = ['gbm', 'cor']
    while beg_time < last_time:
        end_time = GnssTime(beg_time.mjd, 86400 - config.intv)
        config.beg_time = beg_time
        config.end_time = end_time
        fig_dir = os.path.join('figs', f'{beg_time.doy:0>3d}')
        if not os.path.isdir(fig_dir):
            os.makedirs(fig_dir)

        for cr in cen_refs:
            fig_file = os.path.join(fig_dir, f'clkdif_{beg_time.year}{beg_time.doy:0>3d}_{cen}_{cr}.png')
            if os.path.isfile(fig_file) and not overwrite:
                continue
            config.orb_ac = cr
            data = pd.DataFrame()
            for gs in gss:
                file = os.path.join('clkdif', f'{beg_time.doy:0>3d}',
                                    f'clkdif_{beg_time.year}{beg_time.doy:0>3d}_{cen}_{cr}_{gs}')
                if not os.path.isfile(file) or overwrite:
                    config.gsys = gs
                    GrtClkdif(config, f'clkdif_{cen}_{cr}_{gs}').run()

                f_dif_xml = os.path.join(wkdir, 'xml', f'clkdif_{cen}_{cr}_{gs}.xml')
                ref_tree = ET.parse(f_dif_xml)
                refsat = ref_tree.getroot().find('gen').find('refsat').text.strip()
                data_tmp = read_clkdif_sum(file, beg_time.mjd, refsat)
                data = data.append(data_tmp)

            if not data.empty:
                draw_clkdif_std(data, fig_file, f'{str(beg_time)}~{str(end_time)} ({cen.upper()}-{cr.upper()})')
            else:
                logging.warning(f'no data for {str(beg_time)}~{str(end_time)}, origin: {cen}, reference: {cr}')

        beg_time += 86400


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)8s: %(message)s')
    sns.set_context("paper", font_scale=1.7, rc={"lines.linewidth": 1.5})
    sns.set_style("whitegrid")
    sns.set_palette("deep")

    cens = ['clk93', 'clk01', 'cnt', 'igc']
    gss = ['GREC', 'GREC', 'GREC', 'G']
    overwrite = [False, False, False, False]
    with timeblock('Finished draw clock difference'):
        with ThreadPoolExecutor(8) as pool:
            results = pool.map(eval_one_prod, cens, gss, overwrite)

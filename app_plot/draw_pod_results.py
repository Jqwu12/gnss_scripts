import sys
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import sum_orbdif, gns_name

def draw_orbdif_sats(data1, data2, lab1="", lab2="", fig_file="", fig_title="", ymax=15, dpi=300):
    tps = ['along', 'cross', 'radial', '3d']
    ylabs = ['Along [cm]', 'Cross [cm]', 'Radial [cm]', '3 D [cm]']
    sats = list(set(data1.sat).union(set(data1.sat)))
    sats.sort()

    fig, ax = plt.subplots(4, 1, sharex = 'col', figsize=(8, 7.5))
    bar_width = 0.3
    x = np.arange(len(sats))

    for i in range(4):
        val1 = data1[data1.type == tps[i]].rms
        val2 = data2[data2.type == tps[i]].rms
        ax[i].bar(x-bar_width/2, val1, width=bar_width, label=lab1, color='darkblue')
        ax[i].bar(x+bar_width/2, val2, width=bar_width, label=lab2, color='red')
        ax[i].grid(axis="y", linestyle="--")
        msg = f"{val1.mean():4.2f}/{val2.mean():4.2f} cm"
        ax[i].text(0.1, 0.8, msg, fontsize=13, transform=ax[i].transAxes)

        ax[i].set(ylim = (0, ymax), ylabel=ylabs[i])
        ax[i].set_xticks(x)
        ax[i].set_xticklabels(sats, rotation = 90)

    if fig_title:
        ax[0].set(title=f"Orbit differece with {acs[prod]} ({name})")
    ax[0].legend(loc = 'upper right', framealpha=1, ncol=3)

    if fig_file:
        fig.savefig(fig_file, dpi=dpi, bbox_inches='tight')

if __name__ == '__main__':
    gs = "G"
    freq = 2
    cmb = "IF"
    proj = f"/home/jqwu/projects/POD/results_{gs}_{freq}_{cmb}"
    year = 2020
    doy0 = 1
    doy1 = 366
    prod = "com"
    f_list1 = []
    f_list2 = []
    for doy in range(doy0, doy1+1):
        f1 = os.path.join(proj, 'orbdif', str(year), f"orbdif_{year}{doy:0>3d}_{prod}_F3")
        f2 = os.path.join(proj, 'orbdif', str(year), f"orbdif_{year}{doy:0>3d}_{prod}_AR")
        if os.path.isfile(f1) and os.path.isfile(f2):
            f_list1.append(f1)
            f_list2.append(f2)
    
    fig_dir = os.path.join(proj, 'figs')
    if not os.path.isdir(fig_dir):
        os.makedirs(fig_dir)
    
    data1 = sum_orbdif(f_list1, mode='sat')
    data2 = sum_orbdif(f_list2, mode='sat')

    acs = {'com':'CODE', 'wum': 'WHU', 'gbm': 'GFZ'}
    ymax = {'GPS':15, 'GAL':15, 'BDS':40, 'GLO':15}
    name = f"{doy0:0>3d}-{doy1:0>3d}"
    for g in gs:
        gns = gns_name(g)
        dd1 = data1[data1.gsys == gns]
        dd2 = data2[data2.gsys == gns]
        fig_file = os.path.join(fig_dir, f"orbdif_{prod}_{gs}_{name}.png")
        fig_title = f"Orbit differece with {acs[prod]} ({name})"
        draw_orbdif_sats(data1, data2, "Float", "AR", fig_file, fig_title, ymax[gns])




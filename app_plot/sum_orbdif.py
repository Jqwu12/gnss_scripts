import os
import sys
sys.path.append('/home/jqwu/projects/gnss_scripts')
from funcs import sum_orbdif

proj = f"/home/jqwu/projects/POD_GAL"
year = 2022
doy0 = 180
doy1 = 240

freqs = ['E1E5', 'E1E5E7', 'E1E5E7E8', 'E1E5E7E8E6']
#freqs = ['E1E5', 'E1E5E7']
#freqs = ['E1E5E7E8E6']
labs = [f"mf60_F{i}_ud" for i in range(2, 6)]

for i in range(len(freqs)):
    flist = []
    for doy in range(doy0, doy1):
        # /home/jqwu/projects/POD_GAL/mf_ant/E1E5_ud/orbfit/fit
        f = os.path.join(proj, 'mf_ant_60', freqs[i] + "_ud", "orbfit", "fit", f'orbfit_{year}{doy:0>3d}')
        #f = os.path.join(proj, 'fig_data', 'orbdif_' + labs[i], str(year), f'orbdif_{year}{doy:0>3d}_com_AR')
        #f = os.path.join(proj, '30sites_dd1', f"{freqs[i]}", str(year), f'{doy:0>3d}', 'orbdif', f'overlap_{year}{doy:0>3d}')
        flist.append(f)
    
    data = sum_orbdif(flist, mode='none', max=40)
    # data.to_csv(f'{proj}/statistics/orbdif_com_{labs[i]}.csv')
    data.to_csv(f'{proj}/statistics/orbfit_{labs[i]}.csv')
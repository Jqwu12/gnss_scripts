import argparse
import os


def merge_epo_upd(f_ins, f_out, intv=30):
    lines_in = []
    nlines = []
    nsats = []
    idx_sys = []
    for isys in range(0, len(f_ins)):
        idxHeads = []
        with open(f_ins[isys]) as file_object:
            lines = file_object.readlines()
        nline = len(lines)
        nlines.append(nline)
        for i in range(0, nline):
            lines_in.append(lines[i])
            if len(idxHeads) < 3:
                if "EPOCH-TIME" in lines[i]:
                    idxHeads.append(i)
        recLen = idxHeads[1] - idxHeads[0] - 1
        nsats.append(recLen)

    idx_sys.append(0)
    idx = nlines[0]
    for isys in range(1, len(f_ins)):
        idx_sys.append(idx)
        idx += nlines[isys]

    first_line = ""
    with open(f_ins[0]) as f:
        for line in f:
            first_line = line
            break
    nepo = int(86400 / intv) + 1
    with open(f_out, 'w') as file_object:
        file_object.write(first_line)
        for i in range(1, nepo):
            idx1 = 2 + (i - 1) * (nsats[0] + 1) - 1
            idx2 = 1 + i * (nsats[0] + 1) - 1
            for j in range(idx1, idx2 + 1):
                file_object.write(lines_in[j])

            for isys in range(1, len(f_ins)):
                idx1 = idx_sys[isys] + 3 + (i - 1) * (nsats[isys] + 1) - 1
                idx2 = idx_sys[isys] + 1 + i * (nsats[isys] + 1) - 1
                for j in range(idx1, idx2 + 1):
                    file_object.write(lines_in[j])
        file_object.write("EOF\n")


def merge_upd(f_ins, f_out):
    first_line = ""
    with open(f_ins[0]) as f:
        for line in f:
            first_line = line
            break
    with open(f_out, 'w') as f1:
        f1.write(first_line)
        for file in f_ins:
            with open(file) as f2:
                for line in f2:
                    if line[0] != "%" and line.find("EOF") < 0:
                        f1.write(line)
        f1.write("EOF\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='merge upd files')
    parser.add_argument('-i', dest='finp', required=True, nargs='+', help='input upd files: file1 file2 file3')
    parser.add_argument('-o', dest='fout', required=True, help='input upd files: file')
    parser.add_argument('-n', dest='intv', type=int, default=30, help='upd interval (seconds)')
    parser.add_argument('-d', dest='wkdir', help='work path')
    parser.add_argument('-e', dest='epo', action='store_true', help='whether is epoch file')
    args = parser.parse_args()

    wkdir = args.wkdir
    if wkdir:
        os.chdir(wkdir)
    finp = [f for f in args.finp if os.path.isfile(f)]
    fout = args.fout
    intv = args.intv

    if args.epo:
        merge_epo_upd(finp, fout, intv)
    else:
        merge_upd(finp, fout)



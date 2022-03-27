#!/usr/bin/env python3

#
# This file is part of ECPKart64.
#
# Copyright (c) 2021-2022 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse
import binascii

from litex import RemoteClient

from .util.dump import dump_binary

def parse_args():
    parser = argparse.ArgumentParser(description="""ECPKart64 Dump Utility""")
    parser.add_argument("--csr-csv", default="csr.csv", help="SoC CSV file")
    parser.add_argument("--address", default=0x40000000, type=lambda x: int(x, 0))
    parser.add_argument("--length", default=64, type=lambda x: int(x, 0))
    parser.add_argument("--file", default=None, type=argparse.FileType('wb'))
    parser.add_argument("--print", default=False, action='store_true')
    args = parser.parse_args()
    return args

def main():
    args = parse_args()

    # Create and open remote control.
    if not os.path.exists(args.csr_csv):
        raise ValueError("{} not found. This is necessary to load the 'regs' of the remote. Try setting --csr-csv here to "
                         "the path to the --csr-csv argument of the SoC build.".format(args.csr_csv))

    data = dump_binary(args.csr_csv, args.address, args.length)

    if args.file is not None:
        args.file.write(data)
        args.file.close()

    if args.print:
        hexdata = binascii.hexlify(data).decode("utf-8")
        for i in range(0, len(hexdata), 16):
            line = f"{args.address + i//2:08X}  "
            for j in range(i, i+16, 2):
                line += f"{hexdata[j:j+2]} "
            print(line)

if __name__ == "__main__":
    main()

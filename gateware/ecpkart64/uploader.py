#!/usr/bin/env python3

#
# This file is part of ECPKart64.
#
# Copyright (c) 2021-2022 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import argparse

import time

from struct import unpack
from litex import RemoteClient

def parse_args():
    parser = argparse.ArgumentParser(description="""ECPKart64 Dump Utility""")
    parser.add_argument("--csr-csv", default="csr.csv", help="SoC CSV file")
    parser.add_argument("--file", default="bootrom.z64", help="z64 ROM file")
    args = parser.parse_args()
    return args

def main():
    args = parse_args()

    # Create and open remote control.
    if not os.path.exists(args.csr_csv):
        raise ValueError("{} not found. This is necessary to load the 'regs' of the remote. Try setting --csr-csv here to "
                         "the path to the --csr-csv argument of the SoC build.".format(args.csr_csv))

    if not os.path.exists(args.file):
        raise ValueError("{} not found.".format(args.csr_csv))

    bus = RemoteClient(csr_csv=args.csr_csv, debug=True)
    bus.open()

    base = bus.mems.main_ram.base
    print(f"{base:X}")
    # exit()

    try:
        with open(args.file, "rb") as f:
            data_bytes = f.read()[:512]
            data_quads = list(unpack(f"<{len(data_bytes) // 4}I", data_bytes))

            # for j in range(16):
            #     sys.stdout.write(f"\n{j*16:08X}: ")
            #     for i in range(16//4):
            #         sys.stdout.write(f"{data_quads[j*4 + i]:02X} ")
            # exit()

            for i in range(0, len(data_quads)):
                bus.write(base + i*4, data_quads[i])
                time.sleep(0.1)
                # bus.write(base + i*4, i)

            # for i in range(0, len(data_quads), 128):
            #     bus.write(base + i*4, data_quads[i:i+128])
            #     print(i)

            f.close()

    finally:
        bus.close()

if __name__ == "__main__":
    main()

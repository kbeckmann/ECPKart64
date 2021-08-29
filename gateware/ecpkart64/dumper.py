#!/usr/bin/env python3

#
# This file is part of ECPKart64.
#
# Copyright (c) 2021 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse

from litex import RemoteClient

def parse_args():
    parser = argparse.ArgumentParser(description="""ECPKart64 Dump Utility""")
    parser.add_argument("--csr-csv", default="csr.csv", help="SoC CSV file")
    args = parser.parse_args()
    return args

def main():
    args = parse_args()

    # Create and open remote control.
    if not os.path.exists(args.csr_csv):
        raise ValueError("{} not found. This is necessary to load the 'regs' of the remote. Try setting --csr-csv here to "
                         "the path to the --csr-csv argument of the SoC build.".format(args.csr_csv))
    bus = RemoteClient(csr_csv=args.csr_csv)
    bus.open()

    try:
        for i in range(0, 2048, 128):
            values = bus.read(0x3000_0000, 128)
            for j, x in enumerate(values):
                print(f"{i+j:04X}: {x:08X}")

    finally:
        bus.close()

if __name__ == "__main__":
    main()

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
    parser.add_argument("--address", default=0x40000000)
    parser.add_argument("--length", default=64)
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

    base = args.address

    try:
        for addr in range(base, base + args.length, 4):
            value = bus.read(addr)
            v0 = value         & 0xff
            v1 = (value >>  8) & 0xff
            v2 = (value >> 16) & 0xff
            v3 = (value >> 24) & 0xff
            print(f"{addr:08X}: {v0:02X} {v1:02X} {v2:02X} {v3:02X}")

    finally:
        bus.close()

if __name__ == "__main__":
    main()

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

    log_entries = bus.regs.n64_logger_idx.read()
    print(f"Log entries: {log_entries + 1}")

    base = bus.mems.n64slave.base

    try:
        for addr in range(base, base + log_entries * 4, 4):
            value = bus.read(addr)
            print(f"{(addr - base)//4:04X}: {value:08X}")

    finally:
        bus.close()

if __name__ == "__main__":
    main()

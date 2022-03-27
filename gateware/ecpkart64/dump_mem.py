#!/usr/bin/env python3

#
# This file is part of ECPKart64.
#
# Copyright (c) 2021 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse
import struct

from litex import RemoteClient

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

    bus = RemoteClient(csr_csv=args.csr_csv)
    bus.open()
    base = args.address

    data = []
    total_words = (args.length + 3) // 4
    chunks = (total_words + 127) // 128
    for chunk in range(chunks):
        data += bus.read(base + 4 * 128 * chunk, 128 if chunk != chunks - 1 else total_words)
        total_words -= 128

    bus.close()

    if args.file is not None:
        args.file.write(struct.pack(f"<{len(data)}I", *data))
        args.file.close()

    if args.print:
        for i, value in enumerate(data):
            v0 = value         & 0xff
            v1 = (value >>  8) & 0xff
            v2 = (value >> 16) & 0xff
            v3 = (value >> 24) & 0xff
            print(f"{base + i*4:08X}: {v0:02X} {v1:02X} {v2:02X} {v3:02X}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

#
# This file is part of ECPKart64.
#
# Copyright (c) 2021-2022 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse
import struct

from PIL import Image

from .util.dump import dump_array

def parse_args():
    parser = argparse.ArgumentParser(description="""ECPKart64 Dump Utility""")
    parser.add_argument("--csr-csv", default="csr.csv", help="SoC CSV file")
    parser.add_argument("--address", default=0x40000000, type=lambda x: int(x, 0))
    parser.add_argument("--width", default=320, type=lambda x: int(x, 0))
    parser.add_argument("--height", default=240, type=lambda x: int(x, 0))
    parser.add_argument("--bpp", default=4, type=lambda x: int(x, 0))
    parser.add_argument("--file", default="dump.png", type=str)
    args = parser.parse_args()
    return args

def main():
    args = parse_args()

    # Create and open remote control.
    if not os.path.exists(args.csr_csv):
        raise ValueError("{} not found. This is necessary to load the 'regs' of the remote. Try setting --csr-csv here to "
                         "the path to the --csr-csv argument of the SoC build.".format(args.csr_csv))

    words = args.width * args.height * args.bpp // 4
    data = dump_array(args.csr_csv, args.address, words)

    # Byte swap
    swapped = []
    for word in data:
        v0 = word         & 0xff
        v1 = (word >>  8) & 0xff
        v2 = (word >> 16) & 0xff
        v3 = (word >> 24) & 0xff
        swapped.append(v1)
        swapped.append(v0)
        swapped.append(v3)
        swapped.append(v2)

    buffer = struct.pack(f"<{len(swapped)}B", *swapped)

    mode = "RGBA"

    img = Image.frombuffer(mode=mode, data=buffer, size=(args.width, args.height))
    img.save(args.file)

if __name__ == "__main__":
    main()

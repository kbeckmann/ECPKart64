#!/usr/bin/env python3

#
# This file is part of ECPKart64.
#
# Copyright (c) 2021 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import argparse

import time

from struct import unpack
from litex import RemoteClient
import serial

def parse_args():
    parser = argparse.ArgumentParser(description="""ECPKart64 Dump Utility""")
    parser.add_argument("--csr-csv", default="csr.csv", help="SoC CSV file")
    parser.add_argument("--file", default="bootrom.z64", help="z64 ROM file")
    parser.add_argument("--port", default="/dev/ttyUSB1", help="port")
    parser.add_argument("--baudrate", default="1000000", help="baud")
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
    base = bus.mems.main_ram.base
    print(f"{base:X}")
    # exit()

    port = serial.serial_for_url(args.port, args.baudrate)
    # port.open()

    try:
        with open(args.file, "rb") as f:
            data_bytes = f.read()
            port.write(bytes(f"\n\nrom_load {len(data_bytes)//4}\n".encode("utf-8")))

            port.write(data_bytes)
            # for i in range(0, len(data_bytes)):
                # port.write(data_bytes[i])
                # port.write(bytes(data_bytes[1]))
                # port.write("A".encode("utf-8"))
                # port.write(bytearray(data_bytes[i]))
                # print(data_bytes[1])

            f.close()

    finally:
        bus.close()

if __name__ == "__main__":
    main()
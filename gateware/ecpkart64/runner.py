#!/usr/bin/env python3
#
# This file is part of ECPKart64.
#
# Copyright (c) 2021-2022 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse

from litex import RemoteClient

from .mailbox import *

def dbg(*args):
    if True:
        print(*args)

def parse_args():
    parser = argparse.ArgumentParser(description="""ECPKart64 Dump Utility""")
    parser.add_argument("--csr-csv", default="csr.csv", help="SoC CSV file")
    parser.add_argument("--address", default=0x8000_0000, type=lambda x: int(x, 0))
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

    mailbox = Mailbox(bus, args.address)
    mailbox.open()

    loops = 0
    while True:
        data = mailbox.rx()
        print(f"data: {data}")

        mailbox.tx(f"hi from python {loops}...".encode("utf8"))
        loops += 1


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
#
# This file is part of ECPKart64.
#
# Copyright (c) 2021-2022 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse
import time

from litex import RemoteClient

from ..mailbox import *
from .commander import *


def dbg(*args):
    if True:
        print(*args)


class Runner():
    def __init__(self, csr_csv="csr.csv", address=0x8000_0000):
        self.csr_csv = csr_csv
        self.address = address

        self.bus = RemoteClient(csr_csv=csr_csv)
        self.bus.open()

        mailbox = Mailbox(self.bus, self.address)
        mailbox.open()

        self.commander = Commander(mailbox)

    def reboot(self):
        self.commander.execute(0x80000400)


def parse_args():
    parser = argparse.ArgumentParser(description="""ECPKart64 Runner Utility""")
    parser.add_argument("--csr-csv", default="csr.csv", help="SoC CSV file")
    parser.add_argument("--address", default=0x8000_0000, type=lambda x: int(x, 0))
    parser.add_argument("--reset", default=False, action='store_true')
    parser.add_argument("--reboot", default=False, action='store_true')
    parser.add_argument("--benchmark", default=False, action='store_true')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    # Create and open remote control.
    if not os.path.exists(args.csr_csv):
        raise ValueError("{} not found. This is necessary to load the 'regs' of the remote. Try setting --csr-csv here to "
                         "the path to the --csr-csv argument of the SoC build.".format(args.csr_csv))

    runner = Runner(args.csr_csv, address=args.address)

    if args.reset:
        return

    if args.reboot:
        runner.reboot()

    if args.benchmark:
        total = 0
        t0 = time.monotonic()
        while True:
            length = 4 * 59 * 10
            total += length
            facit = os.urandom(length)
            runner.commander.poke(0x80100000, facit)
            data = runner.commander.peek(0x80100000, len(facit))
            assert(data == facit)
            print("ok")
            # print(f"ok: {total / (time.monotonic() - t0):.00f} bytes/s")


if __name__ == "__main__":
    main()

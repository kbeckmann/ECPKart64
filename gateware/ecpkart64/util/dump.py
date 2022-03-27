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

def dump_array(csr_csv, base, words):
    bus = RemoteClient(csr_csv=csr_csv)
    bus.open()

    data = []
    total_words = words
    chunks = (total_words + 127) // 128
    for i in range(chunks):
        chunk = bus.read(base + 4 * 128 * i, 128 if i != chunks - 1 else total_words)
        data += chunk
        total_words -= 128

    bus.close()

    return data

def dump_binary(csr_csv, base, words):
    bus = RemoteClient(csr_csv=csr_csv)
    bus.open()

    data = b''
    total_words = words
    chunks = (total_words + 127) // 128
    for i in range(chunks):
        chunk = bus.read(base + 4 * 128 * i, 128 if i != chunks - 1 else total_words)
        # Data is received in 32-bit little-endian
        data += struct.pack(f"<{len(chunk)}I", *chunk)
        total_words -= 128

    bus.close()

    return data

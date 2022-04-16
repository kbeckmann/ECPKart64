#!/usr/bin/env python3
#
# This file is part of ECPKart64.
#
# Copyright (c) 2021-2022 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import struct

__all__ = [
    "unpack_uint32_le",
    "unpack_uint32_be",
    "pack_uint32_le",
    "pack_uint32_be",
    "bswap32",
]


def unpack_uint32_le(x): return list(struct.unpack(f"<{len(x)//4}I", x))
def unpack_uint32_be(x): return list(struct.unpack(f">{len(x)//4}I", x))
def pack_uint32_le(x): return struct.pack(f"<{len(x)}I", *x)
def pack_uint32_be(x): return struct.pack(f">{len(x)}I", *x)


def bswap32(x):
    return ((((x) & 0xff000000) >> 24) | (((x) & 0x00ff0000) >> 8) |
            (((x) & 0x0000ff00) << 8) | (((x) & 0x000000ff) << 24))

#!/usr/bin/env python3
#
# This file is part of ECPKart64.
#
# Copyright (c) 2021-2022 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

import time

from litex import RemoteClient

from .types import *
from ..util.byteswap import *

__all__ = ["Mailbox", "MailboxT"]

IDLE = int(MailboxStateT.MAILBOX_STATUS_IDLE)
BUSY = int(MailboxStateT.MAILBOX_STATUS_BUSY)
DONE = int(MailboxStateT.MAILBOX_STATUS_DONE)

def dbg(*args):
    # if True:
    if False:
        print(*args)


class Mailbox():
    def __init__(self, bus: RemoteClient, address: int):
        self.bus = bus
        self.address = address

        self.rx_state        = address
        self.rx_state_recv   = address +  1 * 4
        self.rx_length       = address +  2 * 4
        self.rx_payload      = address +  3 * 4

        self.tx_state        = address + 64 * 4
        self.tx_state_recv   = address + 65 * 4
        self.tx_length       = address + 66 * 4
        self.tx_payload      = address + 67 * 4

    def _writeBytes(self, addr: int, data: bytes):
        assert(len(data) % 4 == 0)
        self.bus.write(addr, unpack_uint32_be(data))

    def _writeWord(self, addr: int, word: int):
        self.bus.write(addr, word)

    def _readBytes(self, addr: int, length: int):
        return pack_uint32_le(self.bus.read(addr, length))

    def _readWord(self, addr: int) -> int:
        return bswap32(self.bus.read(addr))

    def tx_payload_write(self, payload):
        self._writeBytes(self.tx_payload, payload)
        self._writeWord(self.tx_length, len(payload) // 4)

    def rx_payload_read(self):
        length = self._readWord(self.rx_length)
        # dbg(f"{length=}")
        assert(length <= MailboxT.rx_payload.sizeof())
        return self._readBytes(self.rx_payload, length)

    def open(self, reset=True):
        if reset:
            self.bus.write(self.tx_state, [0] * 64)

        self._writeWord(self.tx_state,      IDLE)
        self._writeWord(self.tx_state_recv, IDLE)

    def rx(self):
        dbg("[RX] 1")
        t = []
        t.append(time.monotonic())
        ii = 0
        while True:
            ii += 1
            state = self._readWord(self.rx_state)
            if state == DONE:
                break
            # dbg(f"[RX] 1: {state}")
            # dbg(f"[RX] rx_state_recv= {self._readWord(self.rx_state_recv)}")
            # time.sleep(0.1)
        dbg("[RX] 2")

        t.append(time.monotonic())

        self._writeWord(self.tx_state_recv, BUSY)
        t.append(time.monotonic())
        dbg("[RX] 3")

        data = self.rx_payload_read()
        t.append(time.monotonic())
        dbg("[RX] 4")

        self._writeWord(self.tx_state_recv, DONE)
        t.append(time.monotonic())
        dbg("[RX] 5")

        while True:
            state = self._readWord(self.rx_state)
            if state == IDLE:
                break
            # dbg(state)
            # time.sleep(0.1)
        t.append(time.monotonic())

        dbg("[RX] 6")

        self._writeWord(self.tx_state_recv, IDLE)
        t.append(time.monotonic())
        dbg("[RX] 5")

        for i, x in enumerate(t[1:]):
            dbg(f"{t[i] - t[i-1]:.5f}")
        dbg(f"total: {t[-1] - t[0]:.5f}")

        dbg(ii)

        return data


    def tx(self, data, padded=True, timeout=1):
        dbg("[TX] 1")
        t = []
        t.append(time.monotonic())
        ii = 0
        while True:
            ii += 1
            state = self._readWord(self.rx_state_recv)
            if state == IDLE:
                break
            dbg(f"[TX] 1: {state}")
            # time.sleep(0.1)
        dbg("[TX] 2")

        t.append(time.monotonic())

        self._writeWord(self.tx_state, BUSY)
        t.append(time.monotonic())
        dbg("[TX] 3")

        if padded:
            padlen = len(data) % 4
            if padlen > 0:
                data += b'\x00' * (4 - padlen)
        self.tx_payload_write(data)
        t.append(time.monotonic())
        dbg("[TX] 4")

        self._writeWord(self.tx_state, DONE)
        t.append(time.monotonic())
        dbg("[TX] 5")

        while True:
            state = self._readWord(self.rx_state_recv)
            if state == DONE:
                break
            # dbg(f"[TX] rx_state= {self._readWord(self.rx_state)}")
            # dbg(f"[TX] rx_state_recv= {state}")
            # time.sleep(0.1)
        t.append(time.monotonic())

        dbg("[TX] 6")

        self._writeWord(self.tx_state, IDLE)
        t.append(time.monotonic())
        dbg("[TX] 7")

        for i, x in enumerate(t[1:]):
            dbg(f"{t[i] - t[i-1]:.5f}")
        dbg(f"total: {t[-1] - t[0]:.5f}")

        dbg(ii)

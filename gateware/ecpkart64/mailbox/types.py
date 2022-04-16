#!/usr/bin/env python3
#
# This file is part of ECPKart64.
#
# Copyright (c) 2022 Konrad Beckmann <konrad.beckmann@gmail.com
# SPDX-License-Identifier: BSD-2-Clause

from construct import *


__all__ = ["MailboxT", "MailboxStateT"]

MailboxStateT = Enum(Int32ub,
    MAILBOX_STATUS_IDLE = 0,
    MAILBOX_STATUS_BUSY = 1,
    MAILBOX_STATUS_DONE = 2,
)

MailboxT = Struct(
    # READ only
    "rx_state"            / MailboxStateT,
    "rx_state_recv"       / MailboxStateT,
    "rx_length"           / Hex(Int32ub),
    "rx_payload"          / Bytes(61*4),

    # +0x100, WRITE only
    "tx_state"            / MailboxStateT,
    "tx_state_recv"       / MailboxStateT,
    "tx_length"           / Hex(Int32ub),
    "tx_payload"          / Bytes(61*4),
)

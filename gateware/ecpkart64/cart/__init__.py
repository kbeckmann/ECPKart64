# Copyright (c) 2021 Konrad Beckmann <konrad.beckmann@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from litex.soc.interconnect.csr import *
from migen.genlib.cdc import MultiReg

# N64 Cart integration ---------------------------------------------------------------------------------------


class N64Cart(Module, AutoCSR):
    def __init__(self, pads, sys_clk_freq):
        self.pads = pads
        self._out = CSRStorage(len(pads), description="placeholder")

        n64_cold_reset = Signal()
        n64_aleh = Signal()
        n64_alel = Signal()
        n64_read = Signal()
        n64_write = Signal()
        n64_nmi = Signal()

        self.specials += MultiReg(pads.aleh,       n64_aleh)
        self.specials += MultiReg(pads.alel,       n64_alel)
        self.specials += MultiReg(pads.read,       n64_read)
        self.specials += MultiReg(pads.write,      n64_write)
        self.specials += MultiReg(pads.cold_reset, n64_cold_reset)

        n64_ad_io = []
        n64_ad_oe = Signal()
        n64_ad_out = Signal(16)
        n64_ad_in = Signal(16)
        for i in range(16):
            t = TSTriple()
            self.specials += t.get_tristate(pads.ad_io[i])
            self.comb += t.oe.eq(n64_ad_oe)
            self.comb += t.o.eq(n64_ad_out[i])
            self.specials += MultiReg(t.i, n64_ad_in[i])
            n64_ad_io.append(t)

        self.comb += pads.nmi.eq(n64_nmi)

        self.sync += If(n64_cold_reset, n64_nmi.eq(0))

# Copyright (c) 2021 Konrad Beckmann <konrad.beckmann@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from litex.soc.interconnect.csr import *
from migen.genlib.cdc import MultiReg

from struct import unpack

# N64 Cart integration ---------------------------------------------------------------------------------------


class N64Cart(Module, AutoCSR):
    def __init__(self, pads, leds):
        self.pads = pads
        self._out = CSRStorage(len(pads), description="placeholder")

        self.cold_reset = n64_cold_reset = Signal()
        self.aleh = n64_aleh = Signal()
        self.alel = n64_alel = Signal()
        self.read = n64_read = Signal()
        self.write = n64_write = Signal()
        self.nmi = n64_nmi = Signal()

        self.specials += MultiReg(pads.aleh,       n64_aleh)
        self.specials += MultiReg(pads.alel,       n64_alel)
        self.specials += MultiReg(pads.read,       n64_read)
        self.specials += MultiReg(pads.write,      n64_write)
        self.specials += MultiReg(pads.cold_reset, n64_cold_reset)
        self.specials += MultiReg(pads.nmi,        n64_nmi)

        self.ad_oe = n64_ad_oe = Signal()
        self.ad_out = n64_ad_out = Signal(16)
        self.ad_in = n64_ad_in = Signal(16)
        for i in range(16):
            t = TSTriple()
            self.specials += t.get_tristate(pads.ad_io[i])
            self.comb += t.oe.eq(n64_ad_oe)
            self.comb += t.o.eq(n64_ad_out[i])
            self.specials += MultiReg(t.i, n64_ad_in[i])


        ### WIP: Read a simple demo rom and place it in BRAM

        with open("bootrom.z64", "rb") as f:
            # Read the first 74kB (37k words) from the bootrom (controller example)
            # rom_words = 37 * 1024
            rom_words = 1024
            rom_data = unpack(f">{rom_words}H", f.read()[:rom_words * 2])

        rom = Memory(width=16, depth=rom_words, init=rom_data)
        rom_port = rom.get_port()
        self.specials += rom, rom_port


        # Handle bus access
        n64_addr_l = Signal(16)
        n64_addr_h = Signal(16)
        n64_addr = Signal(32)
        roms_cs = Signal()

        # 0x10000000	0x1FBFFFFF	Cartridge Domain 1 Address 2	Cartridge ROM
        self.comb += If(n64_addr[27:] == 0b00001, # 0x10000000
                        rom_port.adr.eq(n64_addr[1:]),
                        roms_cs.eq(1),
                     )

        led_state = Signal(4)
        # self.comb += leds.eq(Cat(led_state, n64_read, n64_write, n64_aleh, n64_alel))
        self.comb += leds.eq(Cat(led_state, n64_read, n64_nmi, n64_aleh, n64_alel))

        self.fsm = fsm = FSM(reset_state="INIT")
        self.submodules += fsm

        self.state = state = Signal(4)

        # Wait for reset to be released
        fsm.act("INIT",
            state.eq(0),
            NextValue(led_state, 0b0001),

            # Reset values
            NextValue(n64_ad_oe, 0),
            NextValue(n64_ad_in, 0),
            NextValue(n64_addr, 0),

            # Active low. If high, start.
            If(n64_cold_reset, NextState("START"))
        )

        # Sample the address
        fsm.act("START",
            state.eq(1),

            NextValue(led_state, led_state | 0b0010),

            NextValue(n64_ad_oe, 0),

            If(n64_alel,
                If(n64_aleh,
                    # High part
                    NextValue(n64_addr_h, n64_ad_in),
                    NextState("ADDR_H"),
                ).Else(
                    # Low part
                    NextValue(n64_addr_l, n64_ad_in),
                    NextValue(n64_addr, Cat(0, n64_ad_in[1:], n64_addr_h)),
                    # Begin RAM access
                    # NextValue(rom_port.r_en, 1),
                    NextState("WAIT"),
                )
            ),

            # Active low. If high, start.
            If(~n64_cold_reset, NextState("INIT"))
        )

        fsm.act("ADDR_H",
            state.eq(2),
            NextValue(n64_ad_oe, 0),
            NextValue(led_state, led_state | 0b0100),

            If(n64_alel,
                If(~n64_aleh,
                    # Low part
                    NextValue(n64_addr_l, n64_ad_in),
                    NextValue(n64_addr, Cat(0, n64_ad_in[1:], n64_addr_h)),

                    NextState("ADDR_L"),
                )
            )
        )

        fsm.act("ADDR_L",
            state.eq(3),
            NextValue(n64_ad_oe, 0),
    
            NextState("WAIT"),
        )

        # Wait for read or write. Perform a read request anyway to be ready.
        fsm.act("WAIT",
            state.eq(4),
            NextValue(led_state, led_state | 0b1000),
            # While in this state, we are processing the read request.

            # Only accept read request if we should handle it
            If(~n64_read & roms_cs,
                # dat_r hopefully contains correct data
                NextValue(n64_ad_out, rom_port.dat_r),
                
                # 0x8037FF40
                If(n64_addr[1],
                    NextValue(n64_ad_out, 0x8037),
                ).Else(
                    NextValue(n64_ad_out, 0xFF40),
                ),

                NextValue(n64_ad_oe, 1),
                NextState("READ"),
            ).Elif(n64_alel | n64_aleh,
                # This shouldn't happen, so go back to init and reset signals.
                NextValue(n64_ad_oe, 0),
                NextState("START"),
            ),

            # Active low. If high, start.
            If(~n64_cold_reset, NextState("INIT"))
        )

        fsm.act("READ",
            state.eq(5),
            NextValue(led_state, led_state | 0b1000),
            # The data was latched in the previous state. OE = 1 now

            If(n64_read,
                # Increase address
                NextValue(n64_addr, n64_addr + 2),
                NextState("WAIT"),
            ).Elif(n64_alel | n64_aleh,
                # Request done, return.
                NextValue(n64_ad_oe, 0),
                NextState("START"),
            ),

            # Active low. If high, start.
            If(~n64_cold_reset, NextState("INIT"))
        )

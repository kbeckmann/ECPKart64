#
# This file is part of ECPKart64.
#
# Copyright (c) 2021 Konrad Beckmann <konrad.beckmann@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from migen.genlib.cdc import MultiReg

from litex.soc.interconnect import wishbone
from litex.soc.interconnect.csr import *

from struct import pack, unpack
import os

# N64 Cart integration ---------------------------------------------------------------------------------------

class N64Cart(Module, AutoCSR):

    def __init__(self, pads, sdram_port, sdram_wait, fast_cd="sys2x"):
        self.pads = pads

        self.logger_idx = CSRStatus(32, description="Logger index")
        self.logger_threshold = CSRStorage(32, reset=6, description="Logger threshold")
        self.rom_header = CSRStorage(32, description="ROM Header (first word)")

        # Logging wishbone memory area
        logger_words = 4096
        logger = Memory(width=32, depth=logger_words)
        logger_wr = logger.get_port(write_capable=True)
        logger_rd = logger.get_port(write_capable=False)
        self.specials += logger, logger_wr, logger_rd

        # Wishbone slave interface
        self.wb_slave = wb_slave = wishbone.Interface()

        # Acknowledge immediately
        self.sync += [
            wb_slave.ack.eq(0),
            If (wb_slave.cyc & wb_slave.stb & ~wb_slave.ack, wb_slave.ack.eq(1))
        ]

        # Sample the write index from the fast domain
        self.specials += MultiReg(logger_wr.adr, self.logger_idx.status)

        self.comb += [
            logger_rd.adr.eq(wb_slave.adr),
            wb_slave.dat_r.eq(logger_rd.dat_r)
        ]

        self.submodules.n64cartbus = N64CartBus(
            pads,
            sdram_port,
            sdram_wait,
            logger_wr,
            logger_words,
            self.logger_threshold.storage,
            self.rom_header
        )


class N64CartBus(Module):
    def __init__(self, pads, sdram_port, sdram_wait, logger_wr, logger_words, logger_threshold, rom_header_csr):
        self.pads = pads

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
        self.raw_ad = []
        for i in range(16):
            t = TSTriple()
            self.specials += t.get_tristate(pads.ad_io[i])
            self.comb += t.oe.eq(n64_ad_oe)
            self.comb += t.o.eq(n64_ad_out[i])
            self.specials += MultiReg(t.i, n64_ad_in[i])
            self.raw_ad.append(t)

        # Keep a register with the previous value
        n64_ad_in_r = Signal.like(n64_ad_in)
        self.sync += n64_ad_in_r.eq(n64_ad_in)


        ### WIP: Read a simple demo rom and place it in BRAM

        if (os.path.isfile("bootrom.z64")):
            with open("bootrom.z64", "rb") as f:
            # with open("bootrom2.z64", "rb") as f:
                # Read the first 74kB (37k words) from the bootrom (controller example)
                rom_words = 37 * 1024
                rom_bytes = rom_words * 2
                rom_data = unpack(f">{rom_words}H", f.read()[:rom_words * 2])
        else:
            rom_words = 16 * 1024
            rom_bytes = rom_words * 2
            rom_data = pack(f">{rom_words}H", *[i for i in range(rom_words)])

        rom = Memory(width=16, depth=rom_words, init=rom_data)
        rom_port = rom.get_port()
        self.specials += rom, rom_port


        # Handle bus access
        n64_addr_l = Signal(16)
        n64_addr_h = Signal(16)
        self.n64_addr = n64_addr = Signal(32)
        sdram_sel = Signal()

        # 0x10000000	0x1FBFFFFF	Cartridge Domain 1 Address 2	Cartridge ROM
        # self.comb += If(n64_addr[27:] == 0b00001, # 0x10000000
        #                 rom_port.adr.eq(n64_addr[1:]),
        #                 sdram_sel.eq(1),
        #              )

        self.comb += If((n64_addr >= 0x1000_0000) & (n64_addr < 0x1FC0_0000),
                        rom_port.adr.eq(n64_addr[1:24]),
                        sdram_sel.eq(1),
                     )

        # SDRAM direct port
        self.sdram_port = sdram_port
        sdram_data   = Signal(16)
        self.sdram_data_r = sdram_data_r = Signal(16)

        self.comb += [
            # 16 bit
            sdram_port.cmd.addr.eq(n64_addr[1:27]),

            # 32 bit
            # sdram_port.cmd.addr.eq(n64_addr[2:27]),

            sdram_port.cmd.we.eq(0),
            sdram_port.cmd.last.eq(1),
            sdram_port.rdata.ready.eq(1),
            sdram_port.flush.eq(0),
            If((n64_addr[2:27] == 0) & (rom_header_csr.storage != 0),
                # Configure the bus to run at a slower speed *for now*
                # 50 MHz = 20ns
                #
                # SDRAM Worst stall seems to be 10 cycles.
                # 
                # Read strobe length = 16.25ns * value (high nibble)
                #
                # 0x1240 => 15 * 20 =  300 ns - Broken
                # 0x2040 => 26 * 20 =  520 ns - Broken
                # 0x2840 => 32 * 20 =  650 ns - ???
                # 0x3040 => 39 * 20 =  780 ns - Working *most of the time*
                # 0x4040 => 52 * 20 = 1040 ns - Working stable.
                sdram_data.eq(Mux(n64_addr[1],
                    Cat(rom_header_csr.storage[ 0: 8], rom_header_csr.storage[ 8:16]),
                    Cat(rom_header_csr.storage[16:24], rom_header_csr.storage[24:32]),
                )),
            ).Else(
                # 16 bit
                sdram_data.eq(
                    Cat(sdram_port.rdata.data[ 8:16], sdram_port.rdata.data[ 0: 8]),
                ),

                # 32 bit
                # sdram_data.eq(Mux(n64_addr[1],
                #     Cat(sdram_port.rdata.data[24:32], sdram_port.rdata.data[16:24]),
                #     Cat(sdram_port.rdata.data[ 8:16], sdram_port.rdata.data[ 0: 8]),
                # )),
            ),
        ]
        self.sync += If(sdram_port.rdata.valid, sdram_data_r.eq(sdram_data))

        self.read_active = n64_read_active = Signal()

        counter = Signal(32)
        self.sync += logger_wr.dat_w.eq(counter)
        # self.comb += logger_wr.dat_w.eq(n64_addr)
        self.sync += If(logger_wr.we, logger_wr.we.eq(0))

        self.fsm = fsm = FSM(reset_state="INIT")
        self.submodules += fsm

        # Wait for reset to be released.
        fsm.act("INIT",
            sdram_wait.eq(1),

            # Reset values
            NextValue(n64_addr, 0),
            NextValue(n64_read_active, 0),

            # Active low. Go to START if high.
            If(n64_cold_reset, NextState("START"))
        )

        # Wait for /ALEL and /ALEH to both go high. This starts a bus access.
        fsm.act("START",
            sdram_wait.eq(1),

            If(n64_alel & n64_aleh,
                NextState("WAIT_ADDR_H"),
            ),

            # Active low. Go to INIT if low.
            If(~n64_cold_reset, NextState("INIT"))
        )

        # Wait for /ALEH to go low and store the high part of the address.
        fsm.act("WAIT_ADDR_H",
            sdram_wait.eq(0),

            If(n64_alel & ~n64_aleh,
                NextValue(n64_addr_h, n64_ad_in_r),
                NextState("WAIT_ADDR_L"),
            ),

            # Active low. Go to INIT if low.
            If(~n64_cold_reset, NextState("INIT"))
        )

        # Wait for /ALEL to go low and store the low part of the address.
        fsm.act("WAIT_ADDR_L",
            sdram_wait.eq(0),

            If(~n64_alel & ~n64_aleh,
                # Store the low part
                NextValue(n64_addr_l, n64_ad_in_r),

                # Store the full address in n64_addr
                NextValue(n64_addr, Cat(n64_ad_in_r, n64_addr_h)),

                NextState("WAIT_READ_WRITE"),
            ),

            # Active low. Go to INIT if low.
            If(~n64_cold_reset, NextState("INIT"))
        )

        # Wait for read or write.
        # Performs the read as well.
        fsm.act("WAIT_READ_WRITE",
            sdram_wait.eq(0),

            If(n64_read_active,
                # Save one cycle latency by using rdata.valid - when this signal is high,
                # sdram_data contains valid data. (Later on, it will not, and we need to use our register)
                n64_ad_out.eq(Mux(sdram_port.rdata.valid, sdram_data, sdram_data_r)),
                n64_ad_oe.eq(1),
            ),

            # Only accept read request if we should handle it
            If(~n64_read & sdram_sel,
                # Enable the read command
                sdram_port.cmd.valid.eq(1),
                NextValue(counter, counter + 1),

                # Go to next state when we get the ack
                If(sdram_port.cmd.ready & sdram_port.rdata.valid,
                    # Log number of cycles it took to access data
                    NextValue(counter, 0),
                    If(counter > logger_threshold, # Longer than 14 cycles (280ns) is game over with 0x1240 config
                        NextValue(logger_wr.we, 1),
                        NextValue(logger_wr.adr, logger_wr.adr + 1),
                    ),

                    NextValue(n64_read_active, 1),
                    NextState("WAIT_READ_H"),
                ),
            ),

            # When /ALEH goes high the access is done. The state of /READ or /WRITE do not matter.
            If(n64_aleh,
                NextValue(n64_read_active, 0),
                NextState("START"),
            ),

            # Active low. Go to INIT if low.
            If(~n64_cold_reset, NextState("INIT"))
        )

        fsm.act("WAIT_READ_H",
            sdram_wait.eq(0),
            # The data was latched in the previous state. OE = 1 now

            n64_ad_out.eq(sdram_data_r),
            n64_ad_oe.eq(1),

            If(n64_read,
                # Increase address
                NextValue(n64_addr, n64_addr + 2),
                NextState("WAIT_READ_WRITE"),
            ).Elif(n64_alel | n64_aleh,
                # Request done, return.
                NextValue(n64_read_active, 0),
                NextState("START"),
            ),

            # Active low. Go to INIT if low.
            If(~n64_cold_reset, NextState("INIT"))
        )

        fsm.do_finalize()
        fsm.finalized = True

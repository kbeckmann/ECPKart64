#
# This file is part of ECPKart64.
#
# Copyright (c) 2021-2022 Konrad Beckmann <konrad.beckmann@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from re import M
from migen import *
from migen.genlib.cdc import MultiReg

from litex.soc.interconnect import wishbone
from litex.soc.interconnect.csr import *

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


class TestImageGenerator(Module):
    def __init__(self, addr, data, active):
        self.frame = frame = Signal(16)
        self.speed = 1

        # Hard code for 512 x 256

        h_ctr = addr[:9]
        v_ctr = addr[9:]

        r = Signal(8)
        g = Signal(8)
        b = Signal(8)

        self.sync += If((addr == 0) & active, frame.eq(frame + 1))

        frame_tri = Mux(frame[8], ~frame[:8], frame[:8])
        frame_tri2 = Mux(frame[9], ~frame[1:9], frame[1:9])

        X = Mux(v_ctr[6], h_ctr + frame[self.speed:], h_ctr - frame[self.speed:])
        Y = v_ctr

        self.comb += [
            r.eq(frame_tri[1:]),
            g.eq(v_ctr * Mux(X & Y, 255, 0)),
            b.eq(~(frame_tri2 + (X ^ Y)) * 255),
        ]

        self.comb += data.eq(Cat(1, b[-5:], g[-5:], r[-5:]))



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

        # Handle bus access
        n64_addr_l = Signal(16)
        n64_addr_h = Signal(16)
        self.n64_addr = n64_addr = Signal(32)

        # Memory area selectors
        self.sdram_sel = sdram_sel = Signal()
        self.custom_sel = custom_sel = Signal()

        # Kind of a hacky address decoder, but it works for now.
        self.comb += \
            If((n64_addr[-8:] >= 0x08) & (n64_addr[-8:] <= 0x0F), 
                # 0x08000000 - 0x0FFFFFFF (128 MB): Cartridge Domain 2 Address 2 Cartridge SRAM
                custom_sel.eq(1),
            ).Elif((n64_addr[-8:] >= 0x10) & (n64_addr[-8:] <= 0x1F), 
                # 0x10000000 - 0x1FBFFFFF (252 MB): Domain 1 Address 2 Cartridge ROM
                If(n64_addr < 0x1000_0000 + 32*1024*1024,
                    # 0 - 32MB
                    sdram_sel.eq(1),
                )
            )

        # SDRAM direct port
        self.sdram_port = sdram_port
        sdram_data   = Signal(16)
        n64_ad_out_r = Signal(16)

        self.comb += [
            # 16 bit
            sdram_port.cmd.addr.eq(n64_addr[1:27]),

            # 32 bit
            # sdram_port.cmd.addr.eq(n64_addr[2:27]),

            sdram_port.cmd.we.eq(0),
            sdram_port.rdata.ready.eq(1),
            sdram_port.cmd.last.eq(1),
            sdram_port.flush.eq(0),

            # TODO?
            # port.cmd.last.eq(~wishbone.we), # Always wait for reads.
            # port.flush.eq(~wishbone.cyc)    # Flush writes when transaction ends.

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
        self.read_active = n64_read_active = Signal()
        self.write_active = n64_write_active = Signal()

        counter = Signal(32)
        self.sync += logger_wr.dat_w.eq(counter)
        # self.comb += logger_wr.dat_w.eq(n64_addr)
        self.sync += If(logger_wr.we, logger_wr.we.eq(0))

        # ------- Custom data generator
        custom_sel_stb = Signal()
        self.sync += custom_sel_stb.eq(0)
        self.custom_data = custom_data = Signal(16)
        self.custom_addr = custom_addr = n64_addr[1:25] # 16M 16-bit words
        self.submodules += TestImageGenerator(custom_addr, custom_data, custom_sel_stb)

        self.sync += \
        If(sdram_sel,
            If(sdram_port.rdata.valid, n64_ad_out_r.eq(sdram_data))
        ).Elif(custom_sel,
            n64_ad_out_r.eq(custom_data),
        )



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

            # ------------ SDRAM
            If(sdram_sel,
                If(n64_read_active,
                    # Save one cycle latency by using rdata.valid - when this signal is high,
                    # sdram_data contains valid data. (Later on, it will not, and we need to use our register)
                    n64_ad_out.eq(Mux(sdram_port.rdata.valid, sdram_data, n64_ad_out_r)),
                    n64_ad_oe.eq(1),
                ),

                # Read access starts
                If(~n64_read,
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

                # Write access starts
                If(~n64_write,
                    # Enable the write command, if it's ready
                    # FIXME: It breaks sometimes when uncommented. Why?
                    # If(sdram_port.cmd.ready == 1,
                        sdram_port.cmd.valid.eq(1),
                        sdram_port.cmd.we.eq(1),
                        sdram_port.wdata.valid.eq(1),
                        sdram_port.wdata.we.eq(0b11), # enable both bytes
                        sdram_port.wdata.data.eq(n64_ad_in_r),

                        If(sdram_port.wdata.ready,
                            NextState("WAIT_WRITE_H"),
                        )
                    # )
                ),
            ),

            # ------------ Custom area
            If(custom_sel,
                If(n64_read_active,
                    n64_ad_out.eq(n64_ad_out_r),
                    n64_ad_oe.eq(1),
                ),

                # Read access starts
                If(~n64_read,
                    NextValue(custom_sel_stb, 1),
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

            n64_ad_out.eq(n64_ad_out_r),
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

        fsm.act("WAIT_WRITE_H",
            # The write request has been handled
            # sdram_port.flush.eq(1),

            If(n64_write,
                # Increase address
                NextValue(n64_addr, n64_addr + 2),
                NextState("WAIT_READ_WRITE"),
            ).Elif(n64_alel | n64_aleh,
                # Request done, return.
                NextValue(n64_write_active, 0),
                NextState("START"),
            ),

            # Active low. Go to INIT if low.
            If(~n64_cold_reset, NextState("INIT"))
        )

        fsm.do_finalize()
        fsm.finalized = True

#!/usr/bin/env python3
#
# This file is part of ECPKart64.
#
# Copyright (c) 2021 Konrad Beckmann <konrad.beckmann@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse
import subprocess

from math import log2, ceil

from migen import *

from litex.build.io import DDROutput

from litex.build.lattice.trellis import trellis_args, trellis_argdict

from litex.soc.cores.clock import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.interconnect import wishbone
from litex.soc.cores.led import LedChaser
from litex.soc.cores.gpio import GPIOTristate, GPIOIn

from litedram.frontend.wishbone import LiteDRAMWishbone2Native

from litedram.phy import GENSDRPHY, HalfRateGENSDRPHY

from litescope import LiteScopeAnalyzer

# Kind of a hack?
from litedram.modules import SDRAMModule, _TechnologyTimings, _SpeedgradeTimings

from ..platforms import kilsyth

from ..cart import N64Cart


# SDRAM configuration
class K4S561632J_UC75(SDRAMModule):
    memtype = "SDR"
    # geometry
    nbanks = 4
    nrows  = 8192
    ncols  = 512
    # timings
    # technology_timings = _TechnologyTimings(tREFI=64e6/8192, tWTR=(2, None), tCCD=(1, None), tRRD=(None, 15))
    # speedgrade_timings = {"default": _SpeedgradeTimings(tRP=40, tRCD=40, tWR=40, tRFC=(None, 128), tFAW=None, tRAS=100)}

    technology_timings = _TechnologyTimings(tREFI=64e6/8192, tWTR=(2, None), tCCD=(1, None), tRRD=(None, 15))
    speedgrade_timings = {"default": _SpeedgradeTimings(tRP=20, tRCD=20, tWR=15, tRFC=(None, 66), tFAW=None, tRAS=44)}
    # speedgrade_timings = {"default": _SpeedgradeTimings(tRP=10, tRCD=10, tWR=10, tRFC=(None, 65), tFAW=None, tRAS=44)}


# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq, sdram_rate):
        self.rst = Signal()
        self.clock_domains.cd_sys = ClockDomain()
        if sdram_rate == "1:2":
            self.clock_domains.cd_sys2x    = ClockDomain()
            self.clock_domains.cd_sys2x_ps = ClockDomain(reset_less=True)
        else:
            self.clock_domains.cd_sys_ps = ClockDomain(reset_less=True)

        # # #

        # Clk / Rst
        clk16 = platform.request("clk16")
        rst   = platform.request("rst")

        # PLL
        self.submodules.pll = pll = ECP5PLL()
        self.comb += pll.reset.eq(rst | self.rst)
        pll.register_clkin(clk16, 16e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)
        if sdram_rate == "1:2":
            pll.create_clkout(self.cd_sys2x,    2 * sys_clk_freq)
            pll.create_clkout(self.cd_sys2x_ps, 2 * sys_clk_freq, phase=180) # Idealy 90° but needs to be increased.
        else:
           pll.create_clkout(self.cd_sys_ps, sys_clk_freq, phase=90)
        
        # 200 MHz clock
        # self.clock_domains.cd_sys4x = ClockDomain()
        # pll.create_clkout(self.cd_sys4x, 4 * sys_clk_freq)

        # SDRAM clock
        sdram_clk = ClockSignal("sys2x_ps" if sdram_rate == "1:2" else "sys_ps")
        self.specials += DDROutput(1, 0, platform.request("sdram_clock"), sdram_clk)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    mem_map = {**SoCCore.mem_map}
    def __init__(self, device="LFE5U-45F", revision="1.0", toolchain="trellis",
        sys_clk_freq=int(50e6), sdram_rate="1:2",
        with_led_chaser=True,
        **kwargs):
        platform = kilsyth.Platform(device=device, revision=revision, toolchain=toolchain)

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq,
            ident          = "LiteX SoC on Kilsyth",
            ident_version  = True,
            uart_baudrate  = 1000000,
            **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq, sdram_rate=sdram_rate)

        # Firmware RAM (To ease initial LiteDRAM calibration support) ------------------------------
        self.add_ram("firmware_ram", 0x20000000, 0x4000)

        # SDR SDRAM --------------------------------------------------------------------------------
        # if not self.integrated_main_ram_size:
        sdrphy_cls = HalfRateGENSDRPHY if sdram_rate == "1:2" else GENSDRPHY
        self.submodules.sdrphy = sdrphy_cls(platform.request("sdram"), sys_clk_freq)
        self.add_sdram("sdram",
            phy              = self.sdrphy,
            module           = K4S561632J_UC75(sys_clk_freq, sdram_rate),
            size             = 32 * 1024 * 1024,
            # l2_cache_size    = kwargs.get("l2_size", 8192),
            # l2_cache_reverse = False

            l2_cache_size    = 0,
            # l2_cache_reverse = False
        )

        # Add an extra dedicated wishbone bus for the n64 cart
        # user_port = self.sdram.crossbar.get_port(data_width=32)
        # sdram_wb = wishbone.Interface(
        #     user_port.data_width,
        #     user_port.address_width)
        # wishbone2native = LiteDRAMWishbone2Native(sdram_wb, user_port)
        # self.submodules += wishbone2native
        sdram_port = self.sdram.crossbar.get_port(data_width=32)


        # Leds -------------------------------------------------------------------------------------

        leds = platform.request_all("user_led")

        # if with_led_chaser:
        #     self.submodules.leds = LedChaser(
        #         pads         = leds[-2],
        #         sys_clk_freq = sys_clk_freq)

        # N64 Peripheral Interface -----------------------------------------------------------------

        n64_pads = platform.request("n64")

        self.submodules.n64 = n64cart = N64Cart(
                pads         = n64_pads,
                leds         = leds,
                sdram_port   = sdram_port,
                fast_cd      = "sys",
                #fast_cd      = "sys4x",
        )
        self.bus.add_slave("n64slave", self.n64.wb_slave, region=SoCRegion(origin=0x30000000, size=0x10000))


        n64cic = self.platform.request("n64cic")
        self.submodules.n64cic_si_clk   = GPIOIn(n64cic.si_clk)
        self.submodules.n64cic_cic_dclk = GPIOIn(n64cic.cic_dclk)
        self.submodules.n64cic_cic_dio  = GPIOTristate(n64cic.cic_dio)
        self.submodules.n64cic_eep_sdat = GPIOTristate(n64cic.eep_sdat)
        self.submodules.n64_cold_reset  = GPIOIn(n64_pads.cold_reset)


        analyzer_signals = [
            # n64cic.cic_dio,
            # n64cic.cic_dclk,
            # n64_pads.aleh,
            # n64_pads.alel,
            # n64_pads.read,
            # n64_pads.write,
            # n64cart.cold_reset,
            n64cart.n64cartbus.aleh,
            n64cart.n64cartbus.alel,
            n64cart.n64cartbus.read,
            n64cart.n64cartbus.write,
            # n64cart.n64cartbus.nmi,

            n64cart.n64cartbus.ad_oe,
            n64cart.n64cartbus.ad_out,
            n64cart.n64cartbus.ad_in,

            n64cart.n64cartbus.n64_addr,
            n64cart.n64cartbus.read_active,

            n64cart.n64cartbus.state,

            # n64cart.n64cartbus.wb_data_r,
            sdram_port.cmd.addr, # might not be needed..
            sdram_port.flush,
            sdram_port.cmd.valid,
            sdram_port.cmd.ready,
            sdram_port.rdata.ready,
            sdram_port.rdata.valid,
            sdram_port.rdata.data,
        ]
        self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
            depth        = 1024 * 2,
            clock_domain = "sys",
            csr_csv      = "analyzer.csv")

        self.add_uartbone(name="serial", baudrate=1000000)
        # self.add_uartbone(name="serial", baudrate=3000000)





# Build --------------------------------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(description="ECPKart64 LiteX SoC on Kilsyth")
    parser.add_argument("--build",           action="store_true",   help="Build bitstream")
    parser.add_argument("--load",            action="store_true",   help="Load bitstream")
    parser.add_argument("--toolchain",       default="trellis",     help="FPGA toolchain: trellis (default) or diamond")
    parser.add_argument("--device",          default="LFE5U-45F",   help="FPGA device: LFE5U-12F, LFE5U-25F, LFE5U-45F (default)  or LFE5U-85F")
    parser.add_argument("--revision",        default="1.0",         help="Board revision: 1.0 (default)")
    parser.add_argument("--sys-clk-freq",    default=50e6,          help="System clock frequency  (default: 50MHz)")
    parser.add_argument("--sdram-rate",      default="1:2",         help="SDRAM Rate: 1:1 Full Rate (default), 1:2 Half Rate")
    builder_args(parser)
    soc_core_args(parser)
    trellis_args(parser)
    args = parser.parse_args()

    soc = BaseSoC(
        device                 = args.device,
        revision               = args.revision,
        toolchain              = args.toolchain,
        sys_clk_freq           = int(float(args.sys_clk_freq)),
        sdram_rate             = args.sdram_rate,
        **soc_core_argdict(args))

    soc.platform.add_extension(kilsyth._sdcard_pmod_io)
    soc.add_sdcard()

    builder = Builder(soc, **builder_argdict(args))
    builder_kargs = trellis_argdict(args) if args.toolchain == "trellis" else {}
    builder.build(**builder_kargs, run=args.build)

    if args.load:
        cmd = "openocd -f openocd/SiPEED.cfg -f openocd/kilsyth_lfe5u45.cfg " + \
              f"-c \"transport select jtag; adapter_khz 10000; init; svf -tap lfe5u45.tap -quiet -progress {os.path.join(builder.gateware_dir, soc.build_name + '.svf')}; exit\""
        subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()

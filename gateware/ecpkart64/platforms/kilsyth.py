#
# This file is part of ECPKart64.
#
# Copyright (c) 2021 Konrad Beckmann <konrad.beckmann@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause


from litex.build.generic_platform import *
from litex.build.lattice import LatticePlatform
from litex.build.lattice.programmer import UJProg

# IOs ----------------------------------------------------------------------------------------------

_io = [
    # Clk / Rst
    ("clk16", 0, Pins("G3"), IOStandard("LVCMOS33")),
    ("rst",   0, Pins("D16"), IOStandard("LVCMOS33")), # Not connected

    # Leds
    ("user_led", 0, Pins("A9 B9 B10 A10 A11 C10 B11 C11"), IOStandard("LVCMOS33")),

    ("serial", 0,
        Subsignal("tx", Pins("A12"), IOStandard("LVCMOS33")), # PMOD0_1
        Subsignal("rx", Pins("D12"), IOStandard("LVCMOS33"))  # PMOD0_2
    ),

    ("sdram_clock", 0, Pins("F19"), IOStandard("LVCMOS33")),
    ("sdram", 0,
        Subsignal("a",          Pins("M20 M19 L20 L19 K20 K19 K18 J20 J19 H20 N19 G20 G19")),
        Subsignal("dq",         Pins("U19 U17 U18 U16 R17 T18 T17 U20 E19 C20 D19 D20 E18 F18 J17 J18")),
        Subsignal("we_n",       Pins("T20")),
        Subsignal("ras_n",      Pins("P18")),
        Subsignal("cas_n",      Pins("R20")),
        Subsignal("cs_n",       Pins("P20")),
        Subsignal("cke",        Pins("F20")),
        Subsignal("ba",         Pins("P19 N20")),
        Subsignal("dm",         Pins("T19 E20")),
        IOStandard("LVCMOS33"), Misc("SLEWRATE=FAST")
    ),

    # Probably won't use this one much
    ("ft600", 0,
        Subsignal("clk",   Pins("H2")),
        Subsignal("data",  Pins("P4 P3 P2 P1 N4 N3 N2 N1 M3 M1 L3 L2 L1 K4 K3 K2")),
        Subsignal("be",    Pins("K1 J5")),
        Subsignal("rd_n",  Pins("M4")),
        Subsignal("wr_n",  Pins("J1")),
        Subsignal("gpio1", Pins("G5")),
        Subsignal("txe_n", Pins("J4")),
        Subsignal("rxf_n", Pins("J3")),
        Subsignal("oe_n",  Pins("H1")),
    ),

    ("n64", 0,
        Subsignal("cold_reset", Pins("W:3")),
        Subsignal("ad_io",      Pins("W:28 W:26 W:24 W:22 W:16 W:14 W:12 W:10 " + \
                                     "W:9  W:11 W:13 W:15 W:21 W:23 W:25 W:27 ")),
        Subsignal("aleh",       Pins("W:18")),
        Subsignal("alel",       Pins("W:20")),
        Subsignal("read",       Pins("W:17")),
        Subsignal("write",      Pins("W:19")),
        Subsignal("nmi",        Pins("W:4")),
    ),

    ("n64cic", 0,
        Subsignal("si_clk",   Pins("W:5")),
        Subsignal("cic_dio",  Pins("W:7")),
        Subsignal("cic_dclk", Pins("W:8")),
        Subsignal("eep_sdat", Pins("W:1")),
    )

]


_connectors = [
    ("W", # Wide connector
        "None",  # 0: No pin0
        # Bank 7
        "F3",    # 1
        "F2",
        "E2",
        "E1",
        "C1",
        "D1",
        "A2",
        "B1",
        "C2",
        "B2",    # 10
        "A3",
        "D2",
        "C3",
        "B3",
        "A4",
        "D3",
        "C4",
        "B4",
        "A5",
        "E4",    # 20
        "C5",
        "B5",
        "A6",
        "D5",
        # Bank 0
        "C6",    # 25
        "B6",
        "C7",
        "A7",
        "B8",
        "A8",    # 30
        "A9",    # 31: LED 0 if jumper is placed
        "C8",
        "None",  # 33: LED 0 (N/C)
        "B9",    # 34: LED 1
        "B10",   # 35: LED 2
        "A10",   # 36: LED 3
        "A11",   # 37: LED 4
        "C10",   # 38: LED 5
        "B11",   # 39: LED 6
        "C11",   # 40: LED 7
    ),
    ("PMOD0",
        "None",  # 0: N/C
        "A12",   # 1: PMOD1
        "D12",   # 2: PMOD2
        "A13",   # 3: PMOD3
        "D13",   # 4: PMOD4
        "None",  # 5: GND
        "None",  # 6: 3.3V
        "B12",   # 7: PMOD5
        "C12",   # 8: PMOD6
        "B13",   # 9: PMOD7
        "C13",   # 10: PMOD8
        "None",  # 11: GND
        "None",  # 12: 3.3v
    ),
    ("PMOD1",
        "None",  # 0: N/C
        "A14",   # 1: PMOD1
        "B15",   # 2: PMOD2
        "C15",   # 3: PMOD3
        "B16",   # 4: PMOD4
        "None",  # 5: GND
        "None",  # 6: 3.3V
        "C14",   # 7: PMOD5
        "D15",   # 8: PMOD6
        "A16",   # 9: PMOD7
        "C16",   # 10: PMOD8
        "None",  # 11: GND
        "None",  # 12: 3.3v
    ),
    ("PMOD2",
        "None",  # 0: N/C
        "A17",   # 1: PMOD1
        "C17",   # 2: PMOD2
        "B18",   # 3: PMOD3
        "B20",   # 4: PMOD4
        "None",  # 5: GND
        "None",  # 6: 3.3V
        "B17",   # 7: PMOD5
        "A18",   # 8: PMOD6
        "A19",   # 9: PMOD7
        "B19",   # 10: PMOD8
        "None",  # 11: GND
        "None",  # 12: 3.3v
    ),
]

# Platform -----------------------------------------------------------------------------------------


class Platform(LatticePlatform):
    default_clk_name   = "clk16"
    default_clk_period = 1e9/16e6

    def __init__(self, device="LFE5U-45F", revision="1.0", toolchain="trellis", **kwargs):
        assert device in ["LFE5U-12F", "LFE5U-25F", "LFE5U-45F", "LFE5U-85F"]
        LatticePlatform.__init__(self, device + "-6BG381C", _io, _connectors, toolchain=toolchain, **kwargs)

    def create_programmer(self):
        return UJProg()

    def do_finalize(self, fragment):
        LatticePlatform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request("clk16", loose=True), 1e9/16e6)

TARGET    ?= kilsyth
BUILD_DIR ?= build/$(TARGET)

PYTHON3      ?= /usr/bin/env python3
LXTERM       ?= lxterm
LITEX_SERVER ?= litex_server
ECHO         ?= echo

UARTBONE_TTY ?= /dev/ttyUSB0
UART_TTY     ?= /dev/ttyUSB1

# To enable verbose, append VERBOSE=1 to make, e.g.:
# make VERBOSE=1
ifneq ($(strip $(VERBOSE)),1)
V = @
endif

# Not 100% accurate, but most python files will affect the bitstream
GATEWARE_SRC = $(shell find gateware -name '*.py')

all: bitstream app

bitstream: $(BUILD_DIR)/gateware/$(TARGET).bit

app: $(BUILD_DIR)/software/app/app.bin

$(BUILD_DIR)/software/app/app.bin:
	$(V)$(MAKE) -C gateware/sw

$(BUILD_DIR)/gateware/$(TARGET).bit: $(GATEWARE_SRC)
	$(V)$(PYTHON3) -m gateware.ecpkart64.targets.$(TARGET) --build --csr-csv csr.csv --doc


load_bitstream: bitstream
	$(V)$(PYTHON3) -m gateware.ecpkart64.targets.$(TARGET) --load

load_app:
	$(V)$(MAKE) -C gateware/sw load


### Debug tools
lxterm: $(BUILD_DIR)/software/app/app.bin
	$(LXTERM) $(UART_TTY) --kernel=$(BUILD_DIR)/software/app/app.bin

litex_server:
	$(LITEX_SERVER) --uart --uart-port /dev/ttyUSB0 --uart-baudrate 1000000

litescope:
	litescope_cli -v main_n64cartbus_state 2

dumper:
	$(V)$(PYTHON3) -m gateware.ecpkart64.dumper


clean:
	$(V)$(ECHO) [ RM ] $(BUILD_DIR)
	$(V)-rm -fR $(BUILD_DIR)

.PHONY: all clean help load_bitstream load_app lxterm litex_server litescope dumper

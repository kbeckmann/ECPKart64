TARGET    ?= kilsyth
BUILD_DIR ?= build/$(TARGET)

PYTHON3      ?= /usr/bin/env python3
LXTERM       ?= lxterm
LITEX_SERVER ?= litex_server
ECHO         ?= echo

UARTBONE_TTY ?= /dev/ttyUSB0
UART_TTY     ?= /dev/ttyUSB1
UART_BAUD    ?= 1000000


# To enable verbose, append VERBOSE=1 to make, e.g.:
# make VERBOSE=1
ifneq ($(strip $(VERBOSE)),1)
V = @
endif

# Not 100% accurate, but most python files will affect the bitstream
GATEWARE_SRC = $(shell find gateware -name '*.py')

all: bitstream app

$(BUILD_DIR):
	$(V)$(ECHO) [ MKDIR ] $(BUILD_DIR)
	mkdir -p $(BUILD_DIR)

bitstream: $(BUILD_DIR)/gateware/$(TARGET).bit

app: $(BUILD_DIR)/software/app/app.bin

$(BUILD_DIR)/software/app/app.bin:
	$(V)$(MAKE) -C gateware/sw 2>&1 | tee $(BUILD_DIR)/app_$(shell date '+%Y%m%d_%H%M%S').log
.PHONY: $(BUILD_DIR)/software/app/app.bin

$(BUILD_DIR)/gateware/$(TARGET).bit: $(GATEWARE_SRC) $(BUILD_DIR)
	$(V)$(PYTHON3) -m gateware.ecpkart64.targets.$(TARGET) --build --csr-csv csr.csv --doc 2>&1 | tee $(BUILD_DIR)/gateware_$(shell date '+%Y%m%d_%H%M%S').log


load_bitstream: bitstream
	$(V)$(PYTHON3) -m gateware.ecpkart64.targets.$(TARGET) --load

load_app: app
	$(V)$(MAKE) -C gateware/sw load


### Debug tools
lxterm: $(BUILD_DIR)/software/app/app.bin
	$(LXTERM) $(UART_TTY) --kernel=$(BUILD_DIR)/software/app/app.bin --kernel-adr=0x20000000 --speed $(UART_BAUD)

litex_server:
	$(LITEX_SERVER) --uart --uart-port $(UARTBONE_TTY) --uart-baudrate $(UART_BAUD)

litescope:
	litescope_cli -v main_analyzer_fsm0_state 3

dumper:
	$(V)$(PYTHON3) -m gateware.ecpkart64.dumper


clean:
	$(V)$(ECHO) [ RM ] $(BUILD_DIR)
	$(V)-rm -fR $(BUILD_DIR)

.PHONY: all clean help load_bitstream load_app app lxterm litex_server litescope dumper

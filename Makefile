TARGET    ?= kilsyth
BUILD_DIR ?= build/$(TARGET)

PYTHON3 ?= /usr/bin/env python3
ECHO    ?= echo

# To enable verbose, append VERBOSE=1 to make, e.g.:
# make VERBOSE=1
ifneq ($(strip $(VERBOSE)),1)
V = @
endif

# Not 100% accurate, but most python files will affect the bitstream
GATEWARE_SRC = $(shell find gateware -name '*.py')

all: bitstream app

bitstream: $(BUILD_DIR)/gateware/$(TARGET).bit

app:
	$(V)$(MAKE) -C gateware/sw

$(BUILD_DIR)/gateware/$(TARGET).bit: $(GATEWARE_SRC)
	$(V)$(PYTHON3) -m gateware.ecpkart64.targets.$(TARGET) --build --csr-csv csr.csv

$(BUILD_DIR)/software/app/app.bin:

load_bitstream: bitstream
	$(V)$(PYTHON3) -m gateware.ecpkart64.targets.$(TARGET) --load

load_app:
	$(V)$(MAKE) -C gateware/sw load

clean:
	$(V)$(ECHO) [ RM ] $(BUILD_DIR)
	$(V)-rm -fR $(BUILD_DIR)

.PHONY: all clean help load_bitstream load_app

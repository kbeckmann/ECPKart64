TARGET    ?= kilsyth
BUILD_DIR ?= ../../build/$(TARGET)
APP_DIR   ?= $(BUILD_DIR)/software/app

# TTY for loading the application
TTYDEV    ?= /dev/ttyUSB0

# Tools
ECHO      ?= echo
LXTERM    ?= lxterm

include $(BUILD_DIR)/software/include/generated/variables.mak
include common.mak

# To enable verbose, append VERBOSE=1 to make, e.g.:
# make VERBOSE=1
ifneq ($(strip $(VERBOSE)),1)
V = @
endif


C_SOURCES =  \
	cic.c \
	isr.c \
	main.c \
	sha256.c \

OBJECTS = $(addprefix $(APP_DIR)/,$(notdir $(C_SOURCES:.c=.o)))

all: $(APP_DIR) $(APP_DIR)/app.bin

-include $(OBJECTS:.o=.d)

%.bin: %.elf
	$(V)$(ECHO) [ BIN ] $(notdir $@)
	$(V)$(OBJCOPY) -O binary $< $@
	$(V)chmod -x $@
	$(V)$(SIZE) $<

$(APP_DIR):
	$(V)mkdir $@

$(APP_DIR)/app.elf: $(OBJECTS)
	$(V)$(ECHO) [ LD ] $(notdir $@)
	$(V)$(CC) $(LDFLAGS) \
		-T linker.ld \
		-N -o $@ \
		$(BUILD_DIR)/software/libbase/crt0.o \
		$(OBJECTS) \
		-L$(BUILD_DIR)/software/libbase \
		-L$(BUILD_DIR)/software/libcompiler_rt \
		-lbase-nofloat -lcompiler_rt
	$(V)chmod -x $@

$(APP_DIR)/%.o: %.c Makefile | $(APP_DIR)
	$(V)$(ECHO) [ CC ] $(notdir $@)
	$(V)$(compile)

$(APP_DIR)/%.o: %.S Makefile | $(APP_DIR)
	$(V)$(ECHO) [ CC ] $(notdir $@)
	$(V)$(assemble)

load: $(APP_DIR)/app.bin
	$(V)$(LXTERM) $(TTYDEV) --serial-boot --kernel=$(APP_DIR)/app.bin

clean:
	$(V)$(ECHO) [ RM ] $(APP_DIR)
	$(V)-rm -fR $(APP_DIR)

.PHONY: all clean load

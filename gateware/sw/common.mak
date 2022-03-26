ifeq ($(TRIPLE),--native--)
TARGET_PREFIX=
else
TARGET_PREFIX=$(TRIPLE)-
endif

RM ?= rm -f
PYTHON ?= python3

ifeq ($(CLANG),1)
CC      := clang -target $(TRIPLE) -integrated-as
CX      := clang++ -target $(TRIPLE) -integrated-as
else
CC      := $(TARGET_PREFIX)gcc -std=gnu99
CX      := $(TARGET_PREFIX)g++
endif
AR      := $(TARGET_PREFIX)ar
LD      := $(TARGET_PREFIX)ld
OBJCOPY := $(TARGET_PREFIX)objcopy
SIZE    := $(TARGET_PREFIX)size

# http://scottmcpeak.com/autodepend/autodepend.html
# Generate *.d Makefile dependencies fragments, include using;
# -include $(OBJECTS:.o=.d)
DEPFLAGS += -MD -MP

# Toolchain options
#
INCLUDES = -I$(PICOLIBC_DIRECTORY)/newlib/libc/tinystdio \
           -I$(PICOLIBC_DIRECTORY)/newlib/libc/include \
           -I$(LIBBASE_DIRECTORY) \
           -I$(SOC_DIRECTORY)/software/include \
           -I$(SOC_DIRECTORY)/software \
           -I$(BUILDINC_DIRECTORY) \
           -I$(BUILDINC_DIRECTORY)/../libc \
           -I$(CPU_DIRECTORY)
COMMONFLAGS = $(DEPFLAGS) -Os $(CPUFLAGS) -g3 -fomit-frame-pointer -Wall -fno-builtin -fno-stack-protector -flto $(INCLUDES)
CFLAGS = $(COMMONFLAGS) -Wstrict-prototypes -Wold-style-definition -Wmissing-prototypes
CXXFLAGS = $(COMMONFLAGS) -std=c++11 -I$(SOC_DIRECTORY)/software/include/basec++ -fno-rtti -ffreestanding
LDFLAGS = -nostdlib -nodefaultlibs -Wl,--no-dynamic-linker -Wl,--build-id=none $(CFLAGS) -L$(BUILDINC_DIRECTORY)


define compilexx
$(CX) -c $(CXXFLAGS) $(1) $< -o $@
endef

define compile
$(CC) -c $(CFLAGS) $(1) $< -o $@
endef

define assemble
$(CC) -c $(CFLAGS) -o $@ $<
endef

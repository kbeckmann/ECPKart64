# ECPKart64

A Lattice ECP5 based FPGA Flash Cart for the Nintendo 64

## Build and load over serial

```

# First install FPGA toolchain and LiteX


# Build and load stuff
make bitstream
make load_bitstream
make load_app

# Manually write "reboot" in the terminal, in order to trigger the upload of the app

# Upload a ROM
python -m gateware.ecpkart64.uploader2 --port /dev/ttyUSB1 --csr-csv csr.csv --cic --file myrom.z64

# Turn on power on the N64

```

## SD-Card

Currently this doesn't work properly for some reason (sd-card driver does not manage to interact with the card properly). But these are the steps normally taken:

```
# Build
make bitstream
make app

# Format and mount an SD-Card with FAT
sudo mkfs.vfat -F32 /dev/...
sudo mount /dev/... /mnt/usb

# Mount it and copy files to it
cp build/kilsyth/software/app/app.bin /mnt/usb/
cp rom.z64 /mnt/usb/

# Create boot.json with your configuration
echo '{
	"rom.z64":	0x40000000,
	"app.bin":	0x20000000
}' > /mnt/usb/boot.json

# Unmount, insert and boot. Turn on N64.


```
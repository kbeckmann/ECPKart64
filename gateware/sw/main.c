// This file is Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
// License: BSD

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <irq.h>
#include <uart.h>
#include <console.h>
#include <generated/csr.h>
#include <generated/mem.h>

#include "sha256.h"
#include "cic.h"

/*-----------------------------------------------------------------------*/
/* Uart                                                                  */
/*-----------------------------------------------------------------------*/

static char *readstr(void)
{
	char c[2];
	static char s[64];
	static int ptr = 0;

	if(readchar_nonblock()) {
		c[0] = readchar();
		c[1] = 0;
		switch(c[0]) {
			case 0x7f:
			case 0x08:
				if(ptr > 0) {
					ptr--;
					putsnonl("\x08 \x08");
				}
				break;
			case 0x07:
				break;
			case '\r':
			case '\n':
				s[ptr] = 0x00;
				putsnonl("\n");
				ptr = 0;
				return s;
			default:
				if(ptr >= (sizeof(s) - 1))
					break;
				putsnonl(c);
				s[ptr] = c[0];
				ptr++;
				break;
		}
	}

	return NULL;
}

static char *get_token(char **str)
{
	char *c, *d;

	c = (char *)strchr(*str, ' ');
	if(c == NULL) {
		d = *str;
		*str = *str+strlen(*str);
		return d;
	}
	*c = 0;
	d = *str;
	*str = c+1;
	return d;
}

static void prompt(void)
{
	printf("\e[92;1mecpkart64-app\e[0m> ");
}

/*-----------------------------------------------------------------------*/
/* Help                                                                  */
/*-----------------------------------------------------------------------*/

static void help(void)
{
	puts("\nECPKart64 app built "__DATE__" "__TIME__"\n");
	puts("Available commands:");
	puts("help               - Show this command");
	puts("reboot             - Reboot CPU");
	puts("cic                - Start CIC emulation");
	puts("");
	puts("mem_read           - Read memory: <address> <length>");
	puts("mem_write          - Write memory: <address> <bytes> <value>");
	puts("mem_load           - Load raw bytes [32b]: <address> <length>");
	puts("mem_dump           - Hexdump [32b]: <address> <length>");
	puts("sha256             - Calculate SHA256 hash of memory: <address> <length>");
	puts("set_header         - Overrides the first word of the rom: <value>");
	puts("");
}

/*-----------------------------------------------------------------------*/
/* Commands                                                              */
/*-----------------------------------------------------------------------*/

static void reboot_cmd(void)
{
	ctrl_reset_write(1);
}

#define NUMBER_OF_BYTES_ON_A_LINE 16
static void dump_bytes(uint32_t *ptr, int count, unsigned long addr)
{
	char *data = (char *)ptr;
	int line_bytes = 0, i = 0;

	putsnonl("Memory dump:");
	while (count > 0) {
		line_bytes =
			(count > NUMBER_OF_BYTES_ON_A_LINE)?
				NUMBER_OF_BYTES_ON_A_LINE : count;

		printf("\n0x%08lx  ", addr);
		for (i = 0; i < line_bytes; i++)
			printf("%02x ", *(unsigned char *)(data+i));

		for (; i < NUMBER_OF_BYTES_ON_A_LINE; i++)
			printf("   ");

		printf(" ");

		for (i = 0; i<line_bytes; i++) {
			if ((*(data+i) < 0x20) || (*(data+i) > 0x7e))
				printf(".");
			else
				printf("%c", *(data+i));
		}

		for (; i < NUMBER_OF_BYTES_ON_A_LINE; i++)
			printf(" ");

		data += (char)line_bytes;
		count -= line_bytes;
		addr += line_bytes;
	}
	printf("\n");
}

static void mem_read(char *address_str, char *len_str)
{
	char *c;
	uint32_t *address = (uint32_t *) strtoul(address_str, &c, 0);
	uint32_t len = strtoul(len_str, &c, 0);

	dump_bytes(address, len, (uint32_t) address);
}

static void mem_write(char *address_str, char *len_str, char *value_str)
{
	char *c;
	uint32_t *address = (uint32_t *) strtoul(address_str, &c, 0);
	uint32_t len = (strtoul(len_str, &c, 0) + 3) / 4;
	uint32_t value = strtoul(value_str, &c, 0);

	for (uint32_t i = 0; i < len; i++) {
		address[i] = value;
	}
}

static void mem_load(char *address_str, char *len_str)
{
	char *c;
	uint32_t *address = (uint32_t *) strtoul(address_str, &c, 0);
	uint32_t words = (strtoul(len_str, &c, 0) + 3) / 4;

	union {
		uint32_t word;
		uint8_t  byte[4];
	} value;

	printf("Reading %ld words\n", words);

	for (int i = 0; i < words; i++) {
		value.byte[0] = readchar();
		value.byte[1] = readchar();
		value.byte[2] = readchar();
		value.byte[3] = readchar();
		address[i] = value.word;
	}
}

static void mem_dump(char *address_str, char *len_str)
{
	char *c;
	union {
		uint32_t word;
		uint8_t  byte[4];
	} value;

	uint32_t *address = (uint32_t *) strtoul(address_str, &c, 0);
	uint32_t len = strtoul(len_str, &c, 0);
	uint32_t written = 0;

	// xxd -p -c 16 < file.hex > file.bin
	for (int i = 0; i < (len + 15) / 16; i++) {
		for (int j = 0; j < 4; j++) {
			value.word = address[i * 4 + j];
			printf("%02x%02x%02x%02x",
				value.byte[0],
				value.byte[1],
				value.byte[2],
				value.byte[3]
			);
			written += 4;
			if (written >= len) {
				printf("\n");
				break;
			}
		}
		printf("\n");
	}
}

static void sha256(char *address_str, char *len_str)
{
	char *c;
	BYTE *address = (BYTE *) strtoul(address_str, &c, 0);
	uint32_t len = strtoul(len_str, &c, 0);
	BYTE hash_str[65];

	sha256_to_string(hash_str, address, len);
	puts((char *) hash_str);
}

static void set_header(char *value_str)
{
	char *c;
	uint32_t value = strtoul(value_str, &c, 0);
	n64_rom_header_write(value);
}

/*-----------------------------------------------------------------------*/
/* Console service / Main                                                */
/*-----------------------------------------------------------------------*/

static void console_service(void)
{
	char *str;
	char *token;

	str = readstr();
	if(str == NULL) return;
	token = get_token(&str);
	if(strcmp(token, "help") == 0)
		help();
	else if(strcmp(token, "reboot") == 0)
		reboot_cmd();
#ifdef CSR_LEDS_BASE
	else if(strcmp(token, "led") == 0)
		led_cmd();
#endif
	else if(strcmp(token, "cic") == 0)
		main_cic();
	else if(strcmp(token, "mem_read") == 0) {
		char *addr = get_token(&str);
		char *len = get_token(&str);
		mem_read(addr, len);
	}
	else if(strcmp(token, "mem_write") == 0) {
		char *addr = get_token(&str);
		char *len = get_token(&str);
		char *value = get_token(&str);
		mem_write(addr, len, value);
	}
	else if(strcmp(token, "mem_load") == 0) {
		char *addr = get_token(&str);
		char *len = get_token(&str);
		mem_load(addr, len);
	}
	else if(strcmp(token, "mem_dump") == 0) {
		char *addr = get_token(&str);
		char *len = get_token(&str);
		mem_dump(addr, len);
	}
	else if(strcmp(token, "sha256") == 0) {
		char *addr = get_token(&str);
		char *len = get_token(&str);
		sha256(addr, len);
	}
	else if(strcmp(token, "set_header") == 0) {
		char *value = get_token(&str);
		set_header(value);
	}
	prompt();
}

int main(void)
{
#ifdef CONFIG_CPU_HAS_INTERRUPT
	irq_setmask(0);
	irq_setie(1);
#endif
	uart_init();

	help();
	prompt();

	// Start CIC automatically (useful when booting from an SDCard)
	printf("cic\n");
	main_cic();

	while(1) {
		console_service();
	}

	return 0;
}

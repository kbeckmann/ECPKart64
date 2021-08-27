/*

This file is part of ECPKart64.

Copyright (c) 2021 Konrad Beckmann <konrad.beckmann@gmail.com>
Copyright (c) 2020 Jan Goldacker <goldacker.jan@web.de>

SPDX-License-Identifier: gpl-3.0

This is a port of:
https://github.com/jago85/Brutzelkarte_FPGA/blob/master/lm8_cic/fw/main.c

*/

#include <stdio.h>

#include <generated/csr.h>

#include "cic.h"

#define DEBUG

#ifdef DEBUG
#define WRITE_DEBUG(x) printf("%02X\n", x)
#else
#define WRITE_DEBUG(x)
#endif

void EncodeRound(unsigned char index);
void CicRound(unsigned char *);
void Cic6105Algo(void);

#define CIC6102_SEED (0x3F)
const unsigned char _CicSeed = CIC6102_SEED;

#define CIC6102_CHECKSUM 0xa, 0x5, 0x3, 0x6, 0xc, 0x0, 0xf, 0x1, 0xd, 0x8, 0x5, 0x9
const unsigned char _CicChecksum[] = {
    CIC6102_CHECKSUM
};

const unsigned char _CicRamInitNtsc[] = {
    0xE, 0x0, 0x9, 0xA, 0x1, 0x8, 0x5, 0xA, 0x1, 0x3, 0xE, 0x1, 0x0, 0xD, 0xE, 0xC,
    0x0, 0xB, 0x1, 0x4, 0xF, 0x8, 0xB, 0x5, 0x7, 0xC, 0xD, 0x6, 0x1, 0xE, 0x9, 0x8
};

const unsigned char _CicRamInitPal[] = {
    0xE, 0x0, 0x4, 0xF, 0x5, 0x1, 0x2, 0x1, 0x7, 0x1, 0x9, 0x8, 0x5, 0x7, 0x5, 0xA,
    0x0, 0xB, 0x1, 0x2, 0x3, 0xF, 0x8, 0x2, 0x7, 0x1, 0x9, 0x8, 0x1, 0x1, 0x5, 0xC
};

unsigned char _CicMem[32];
unsigned char _6105Mem[32];

unsigned char ReadBit(void)
{
    unsigned char res;

    unsigned char vin;

    // wait for DCLK to go low
    do {
        vin = n64cic_cic_dclk_in_read();
    } while (vin & 1);

    // Read the data bit
    res = n64cic_cic_dio_in_read();

    // wait for DCLK to go high
    do {
        vin = n64cic_cic_dclk_in_read();
    } while ((vin & 1) == 0);

    return res & 0x01;
}

void WriteBit(unsigned char b)
{
    unsigned char vin;

    printf("W: %d", b);

    // wait for DCLK to go low
    do {
        vin = n64cic_cic_dclk_in_read();
    } while (vin & 1);

    printf(".");

    if (b == 0)
    {
        // Drive low
        n64cic_cic_dio_out_write(0);
        n64cic_cic_dio_oe_write(1);
    }

    printf(".");

    // wait for DCLK to go high
    do {
        vin = n64cic_cic_dclk_in_read();
    } while ((vin & 1) == 0);

    // Disable output
    n64cic_cic_dio_oe_write(0);

    printf(".\n");
}

void WriteNibble(unsigned char n)
{
    WriteBit(n & 0x08);
    WriteBit(n & 0x04);
    WriteBit(n & 0x02);
    WriteBit(n & 0x01);
}

// Write RAM nibbles until index hits a 16 Byte border
void WriteRamNibbles(unsigned char index)
{
    do
    {
        WriteNibble(_CicMem[index]);
        index++;
    } while ((index & 0x0f) != 0);
}

unsigned char ReadNibble(void)
{
    unsigned char res = 0;
    unsigned char i;
    for (i = 0; i < 4; i++)
    {
        res <<= 1;
        res |= ReadBit();
    }
    return res;
}

void WriteSeed(void)
{
    _CicMem[0x0a] = 0xb;
    _CicMem[0x0b] = 0x5;
    _CicMem[0x0c] = _CicSeed >> 4;
    _CicMem[0x0d] = _CicSeed;
    _CicMem[0x0e] = _CicSeed >> 4;
    _CicMem[0x0f] = _CicSeed;

    EncodeRound(0x0a);
    EncodeRound(0x0a);
    WriteRamNibbles(0x0a);
}

void WriteChecksum(void)
{
    unsigned char i;
    for (i = 0; i < 12; i++)
        _CicMem[i + 4] = _CicChecksum[i];

    // wait for DCLK to go low
    // (doesn't seem to be necessary)
//    unsigned char vin;
//    do {
//        MICO_GPIO_READ_DATA_BYTE0(GPIO_IO_BASE, vin);
//    } while (vin & 2);

    // "encrytion" key
    // initial value doesn't matter
    //_CicMem[0x00] = 0;
    //_CicMem[0x01] = 0xd;
    //_CicMem[0x02] = 0;
    //_CicMem[0x03] = 0;

    EncodeRound(0x00);
    EncodeRound(0x00);
    EncodeRound(0x00);
    EncodeRound(0x00);

    // signal that we are done to the pif
    // (test with WriteBit(1) also worked)
    WriteBit(0);

    // Write 16 nibbles
    WriteRamNibbles(0);
}

void EncodeRound(unsigned char index)
{
    unsigned char a;

    a = _CicMem[index];
    index++;

    do
    {
        a = (a + 1) & 0x0f;
        a = (a + _CicMem[index]) & 0x0f;
        _CicMem[index] = a;
        index++;
    } while ((index & 0x0f) != 0);
}

void Exchange(unsigned char *a, unsigned char *b)
{
    unsigned char tmp;
    tmp = *a;
    *a = *b;
    *b = tmp;
}

// translated from PIC asm code (thx to Mike Ryan for the PIC implementation)
// this implementation saves program memory in LM8
void CicRound(unsigned char * m)
{
    unsigned char a;
    unsigned char b, x;

    x = m[15];
    a = x;

    do
    {
        b = 1;
        a += m[b] + 1;
        m[b] = a;
        b++;
        a += m[b] + 1;
        Exchange(&a, &m[b]);
        m[b] = ~m[b];
        b++;
        a &= 0xf;
        a += (m[b] & 0xf) + 1;
        if (a < 16)
        {
            Exchange(&a, &m[b]);
            b++;
        }
        a += m[b];
        m[b] = a;
        b++;
        a += m[b];
        Exchange(&a, &m[b]);
        b++;
        a &= 0xf;
        a += 8;
        if (a < 16)
            a += m[b];
        Exchange(&a, &m[b]);
        b++;
        do
        {
            a += m[b] + 1;
            m[b] = a;
            b++;
            b &= 0xf;
        } while (b != 0);
        a = x + 0xf;
        x = a & 0xf;
    } while (x != 15);
}

void Cic6105Algo(void)
{
    unsigned char A = 5;
    unsigned char carry = 1;
    unsigned char i;
    for (i = 0; i < 30; ++i)
    {
        if (!(_6105Mem[i] & 1))
            A += 8;
        if (!(A & 2))
            A += 4;
        A = (A + _6105Mem[i]) & 0xf;
        _6105Mem[i] = A;
        if (!carry)
            A += 7;
        A = (A + _6105Mem[i]) & 0xF;
        A = A + _6105Mem[i] + carry;
        if (A >= 0x10)
        {
            carry = 1;
            A -= 0x10;
        }
        else
        {
            carry = 0;
        }
        A = (~A) & 0xf;
        _6105Mem[i] = A;
    }
}

void Die(void)
{
    // never return
    while (1)
    {
        WRITE_DEBUG(0x20);
        WRITE_DEBUG(0x00);
    }
}

void CompareMode(unsigned char isPal)
{
    unsigned char ramPtr;
    WRITE_DEBUG(0x40);
    // don't care about the low ram as we don't check this
//  CicRound(&_CicMem[0x00]);
//  CicRound(&_CicMem[0x00]);
//  CicRound(&_CicMem[0x00]);

    // only need to calculate the high ram
    CicRound(&_CicMem[0x10]);
    CicRound(&_CicMem[0x10]);
    CicRound(&_CicMem[0x10]);

    // 0x17 determines the start index (but never 0)
    WRITE_DEBUG(0x00);
    ramPtr = _CicMem[0x17] & 0xf;
    if (ramPtr == 0)
        ramPtr = 1;
    ramPtr |= 0x10;

    do
    {
        // read the bit from PIF (don't care about the value)
        ReadBit();

        // send out the lowest bit of the currently indexed ram
        WriteBit(_CicMem[ramPtr] & 0x01);

        // PAL or NTSC?
        if (!isPal)
        {
            // NTSC
            ramPtr++;
        }
        else
        {
            // PAL
            ramPtr--;
        }

        // repeat until the end is reached
    } while (ramPtr & 0xf);
}

void Cic6105Mode(void)
{
    unsigned char ramPtr;
    WRITE_DEBUG(0x80);

    // write 0xa 0xa
    WriteNibble(0xa);
    WriteNibble(0xa);

    // receive 30 nibbles
    for (ramPtr = 0; ramPtr < 30; ramPtr++)
    {
        _6105Mem[ramPtr] = ReadNibble();
    }

    // execute the algorithm
    WRITE_DEBUG(0x00);
    Cic6105Algo();
    WRITE_DEBUG(0x80);

    // send bit 0
    WriteBit(0);

    // send 30 nibbles
    for (ramPtr = 0; ramPtr < 30; ramPtr++)
    {
        WriteNibble(_6105Mem[ramPtr]);
    }
    WRITE_DEBUG(0x00);
}

void InitRam(unsigned char isPal)
{
    unsigned char i;

    if (!isPal)
    {
        for (i = 0; i < 32; i++)
            _CicMem[i] = _CicRamInitNtsc[i];
    }
    else
    {
        for (i = 0; i < 32; i++)
            _CicMem[i] = _CicRamInitPal[i];
    }
}

void main_cic(void)
{
    unsigned char isPal;

    WRITE_DEBUG(0x01);

    // TODO: Read the region jumper (?)
    isPal = 1;

    // send out the corresponding id
    unsigned char hello = 0x1;
    if (isPal)
        hello |= 0x4;
    WriteNibble(hello);
    WRITE_DEBUG(0x03);

    // encode and send the seed
    WriteSeed();

    // encode and send the checksum
    WriteChecksum();
    WRITE_DEBUG(0x07);
    
    // init the ram corresponding to the region
    InitRam(isPal);
    
    // read the initial values from the PIF
    _CicMem[0x01] = ReadNibble();
    _CicMem[0x11] = ReadNibble();
    WRITE_DEBUG(0x0F);

    char c;
    while (1)
    {
        if (readchar_nonblock()) {
            c = readchar();
            if (c == 'A') {
                printf("CIC: Bye!\n");
                break;
            }
        }

        continue;



        // read mode (2 bit)
        unsigned char cmd = 0;
        cmd |= (ReadBit() << 1);
        cmd |= ReadBit();
        switch (cmd)
        {
        case 0:
            // 00 (compare)
            CompareMode(isPal);
            break;

        case 2:
            // 10 (6105)
            Cic6105Mode();
            break;

        case 3:
            // 11 (reset)
            WRITE_DEBUG(0x10);
            WriteBit(0);
            break;

        case 1:
            // 01 (die)
        default:
            Die();
        }
    }
}

#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals
import math
import operator
import re
import spidev
import time
import fagpio


# noinspection PyAttributeOutsideInit

class Cc1101:
    # ------------------------------------------------------------------------------------------------------
    # Settings
    scan_timeout = 8  # for scan_datarate(), scan_freq()
    spi0_gdo0 = 153  # eint9 gpn9
    spi1_gdo0 = 155  # eint11 gpn11
    #    packet_len=1500 # for Receive()
    packet_len = 1500
    livolo_packet_len = 1500
    read_threshold = 15
    command_list = ['LivoloA',
                    'LivoloB',
                    'LivoloC',
                    'LivoloD',
                    'LivoloE',
                    'LivoloH',
                    'ButtonA',
                    'ButtonC',
                    'Marcstate',
                    ]
    # ------------------------------------------------------------------------------------------------------
    # CC1101 STROBE, CONTROL AND STATUS REGSITER

    register = {
        'IOCFG2': 0x00,  # GDO2 output pin configuration
        'IOCFG1': 0x01,  # GDO1 output pin configuration
        'IOCFG0': 0x02,  # GDO0 output pin configuration
        'FIFOTHR': 0x03,  # RX FIFO and TX FIFO thresholds
        'SYNC1': 0x04,  # Sync word, high byte
        'SYNC0': 0x05,  # Sync word, low byte
        'PKTLEN': 0x06,  # Packet length
        'PKTCTRL1': 0x07,  # Packet automation control
        'PKTCTRL0': 0x08,  # Packet automation control
        'ADDR': 0x09,  # Device address
        'CHANNR': 0x0A,  # Channel number
        'FSCTRL1': 0x0B,  # Frequency synthesizer control
        'FSCTRL0': 0x0C,  # Frequency synthesizer control
        'FREQ2': 0x0D,  # Frequency control word, high byte
        'FREQ1': 0x0E,  # Frequency control word, middle byte
        'FREQ0': 0x0F,  # Frequency control word, low byte
        'MDMCFG4': 0x10,  # Modem configuration
        'MDMCFG3': 0x11,  # Modem configuration
        'MDMCFG2': 0x12,  # Modem configuration
        'MDMCFG1': 0x13,  # Modem configuration
        'MDMCFG0': 0x14,  # Modem configuration
        'DEVIATN': 0x15,  # Modem deviation setting
        'MCSM2': 0x16,  # Main Radio Control State Machine configuration
        'MCSM1': 0x17,  # Main Radio Control State Machine configuration
        'MCSM0': 0x18,  # Main Radio Control State Machine configuration
        'FOCCFG': 0x19,  # Frequency Offset Compensation configuration
        'BSCFG': 0x1A,  # Bit Synchronization configuration
        'AGCCTRL2': 0x1B,  # AGC control
        'AGCCTRL1': 0x1C,  # AGC control
        'AGCCTRL0': 0x1D,  # AGC control
        'WOREVT1': 0x1E,  # High byte Event 0 timeout
        'WOREVT0': 0x1F,  # Low byte Event 0 timeout
        'WORCTRL': 0x20,  # Wake On Radio control
        'FREND1': 0x21,  # Front end RX configuration
        'FREND0': 0x22,  # Front end TX configuration
        'FSCAL3': 0x23,  # Frequency synthesizer calibration
        'FSCAL2': 0x24,  # Frequency synthesizer calibration
        'FSCAL1': 0x25,  # Frequency synthesizer calibration
        'FSCAL0': 0x26,  # Frequency synthesizer calibration
        'RCCTRL1': 0x27,  # RC oscillator configuration
        'RCCTRL0': 0x28,  # RC oscillator configuration
        'FSTEST': 0x29,  # Frequency synthesizer calibration control
        'PTEST': 0x2A,  # Production test
        'AGCTEST': 0x2B,  # AGC test
        'TEST2': 0x2C,  # Various test settings
        'TEST1': 0x2D,  # Various test settings
        'TEST0': 0x2E,  # Various test settings

        # ------------------------------------------------------------------------------------------------------
        # Strobe commands
        'SRES': 0x30,  # Reset chip.
        'SFSTXON': 0x31,  # Enable and calibrate frequency synthesizer (if MCSM0.FS_AUTOCAL=1).
        # If in RX/TX: Go to a wait state where only the synthesizer is
        # running (for quick RX / TX turnaround).
        'SXOFF': 0x32,  # Turn off crystal oscillator.
        'SCAL': 0x33,  # Calibrate frequency synthesizer and turn it off
        # (enables quick start).
        'SRX': 0x34,  # Enable RX. Perform calibration first if coming from IDLE and
        # MCSM0.FS_AUTOCAL=1.
        'STX': 0x35,  # In IDLE state: Enable TX. Perform calibration first if
        # MCSM0.FS_AUTOCAL=1. If in RX state and CCA is enabled:
        # Only go to TX if channel is clear.
        'SIDLE': 0x36,  # Exit RX / TX, turn off frequency synthesizer and exit
        # Wake-On-Radio mode if applicable.
        'SAFC': 0x37,  # Perform AFC adjustment of the frequency synthesizer
        'SWOR': 0x38,  # Start automatic RX polling sequence (Wake-on-Radio)
        'SPWD': 0x39,  # Enter power down mode when CSn goes high.
        'SFRX': 0x3A,  # Flush the RX FIFO buffer.
        'SFTX': 0x3B,  # Flush the TX FIFO buffer.
        'SWORRST': 0x3C,  # Reset real time clock.
        'SNOP': 0x3D,  # No operation. May be used to pad strobe commands to two
        # bytes for simpler software.

        'PARTNUM': 0x30,
        'VERSION': 0x31,
        'FREQEST': 0x32,
        'LQI': 0x33,
        'RSSI': 0x34,
        'MARCSTATE': 0x35,
        'WORTIME1': 0x36,
        'WORTIME0': 0x37,
        'PKTSTATUS': 0x38,
        'VCO_VC_DAC': 0x39,
        'TXBYTES': 0x3A,
        'RXBYTES': 0x3B,
        'RCCTRL1_STATUS': 0x3C,
        'RCCTRL0_STATUS': 0x3D,
        'PATABLE': 0x3E,
        'TXFIFO': 0x3F,
        'RXFIFO': 0x3F
    }

    Marcstate_reg = {
        0x0: 'SLEEP',
        0x1: 'IDLE',
        0x2: 'XOFF',
        0x3: 'VCOON_MC',
        0x4: 'REGON_MC',
        0x5: 'MANCAL',
        0x6: 'VCOON',
        0x7: 'REGON',
        0x8: 'STARTCAL',
        0x9: 'BWBOOST',
        0xa: 'FS_LOCK',
        0xb: 'IFADCON',
        0xc: 'ENDCAL',
        0xd: 'RX',
        0xe: 'RX_END',
        0xf: 'RX_RST',
        0x10: 'TXRX_SWITCH',
        0x11: 'RXFIFO_OVERFLOW',
        0x12: 'FSTXON',
        0x13: 'TX',
        0x14: 'TX_END',
        0x15: 'RXTX_SWITCH',
        0x16: 'TXFIFO_UNDERFLOW'
    }

    WRITE_BURST = 0x40
    READ_SINGLE = 0x80
    READ_BURST = 0xC0

    # ------------------------------------------------------------------------------------------------------
    rf_settings = [
        # 0
        {
            'FSCTRL1': 0x0C,  # FSCTRL1   Frequency synthesizer control.
            'FSCTRL0': 0x00,  # FSCTRL0   Frequency synthesizer control.
            'FREQ2': 0x10,  # FREQ2     Frequency control word, high byte.
            'FREQ1': 0xA7,  # FREQ1     Frequency control word, middle byte.
            'FREQ0': 0x62,  # FREQ0     Frequency control word, low byte.
            'MDMCFG4': 0x2D,  # MDMCFG4   Modem configuration.
            'MDMCFG3': 0x3B,  # MDMCFG3   Modem configuration.
            'MDMCFG2': 0x13,  # MDMCFG2   Modem configuration.
            'MDMCFG1': 0x22,  # MDMCFG1   Modem configuration.
            'MDMCFG0': 0xF8,  # MDMCFG0   Modem configuration.
            'CHANNR': 0x00,  # CHANNR    Channel number.
            'DEVIATN': 0x62,  # DEVIATN   Modem deviation setting (when FSK modulation is enabled).
            'FREND1': 0xB6,  # FREND1    Front end RX configuration.
            'FREND0': 0x10,  # FREND0    Front end TX configuration.
            'MCSM0': 0x18,  # MCSM0     Main Radio Control State Machine configuration.
            'FOCCFG': 0x1D,  # FOCCFG    Frequency Offset Compensation Configuration.
            'BSCFG': 0x1C,  # BSCFG     Bit synchronization Configuration.
            'AGCCTRL2': 0xC7,  # AGCCTRL2  AGC control.
            'AGCCTRL1': 0x00,  # AGCCTRL1  AGC control.
            'AGCCTRL0': 0xB0,  # AGCCTRL0  AGC control.
            'FSCAL3': 0xEA,  # FSCAL3    Frequency synthesizer calibration.
            'FSCAL2': 0x2A,  # FSCAL2    Frequency synthesizer calibration.
            'FSCAL1': 0x00,  # FSCAL1    Frequency synthesizer calibration.
            'FSCAL0': 0x1F,  # FSCAL0    Frequency synthesizer calibration.
            'FSTEST': 0x59,  # FSTEST    Frequency synthesizer calibration.
            'TEST2': 0x88,  # TEST2     Various test settings.
            'TEST1': 0x31,  # TEST1     Various test settings.
            'TEST0': 0x09,  # TEST0     Various test settings.
            'FIFOTHR': 0x07,  # FIFOTHR   RXFIFO and TXFIFO thresholds.
            'IOCFG2': 0x29,  # IOCFG2    GDO2 output pin configuration.
            'IOCFG0': 0x06,  # IOCFG0D   GDO0 output pin configuration.
            'PKTCTRL1': 0x04,  # PKTCTRL1  Packet automation control.
            'PKTCTRL0': 0x05,  # PKTCTRL0  Packet automation control.
            'ADDR': 0x00,  # ADDR      Device address.
            'PKTLEN': 0xFF,  # PKTLEN    Packet length.
            'PATABLE': 0x1d
        },

        # 1 
        {
            'IOCFG0': 0x06,
            'PKTCTRL0': 0x05,
            'FSCTRL1': 0x0C,
            'FREQ2': 0x10,
            'FREQ1': 0xB0,
            'FREQ0': 0x71,
            'MDMCFG4': 0x2D,
            'MDMCFG3': 0x3B,
            'MDMCFG2': 0x3B,
            'DEVIATN': 0x62,
            'MCSM0': 0x18,
            'FOCCFG': 0x1D,
            'BSCFG': 0x1C,
            'AGCCTRL2': 0x04,
            'AGCCTRL1': 0x00,
            'AGCCTRL0': 0x92,
            'WORCTRL': 0xFB,
            'FREND1': 0xB6,
            'FREND0': 0x11,
            'FSCAL3': 0xEA,
            'FSCAL2': 0x2A,
            'FSCAL1': 0x00,
            'FSCAL0': 0x1F,
            'TEST0': 0x09
        },
        # 2 
        # Asynch with rx on GDO0
        {
            'IOCFG0': 0x0D,
            'PKTCTRL1': 0x00,
            'PKTCTRL0': 0x32,
            'FSCTRL1': 0x06,
            'FREQ2': 0x10,  # freq 433,92
            'FREQ1': 0xB0,
            'FREQ0': 0x71,
            'MDMCFG4': 0x27,  # BW 270 Data rate 3.335
            'MDMCFG3': 0x0D,
            'MDMCFG2': 0x30,
            'DEVIATN': 0x42,
            'MCSM0': 0x18,
            'FOCCFG': 0x14,
            'BSCFG': 0x1C,
            'AGCCTRL2': 0x04,
            'AGCCTRL1': 0x00,
            'AGCCTRL0': 0x92,
            'WORCTRL': 0xFB,
            'FREND1': 0xB6,
            'FREND0': 0x11,
            'FSCAL3': 0xEA,
            'FSCAL2': 0x2A,
            'FSCAL1': 0x00,
            'FSCAL0': 0x1F,
            'TEST0': 0x09,
            'TEST1': 0x35,
            'TEST2': 0x81,
            'FIFOTHR': 0x47
        },
        # 3
        # Simple naked packet for Asynch
        {
            'IOCFG0': 0x06,
            'PKTCTRL1': 0x00,
            'PKTCTRL0': 0x00,  # fixed length
            'PKTLEN': 0xFF,  # 0x40
            'FSCTRL1': 0x0C,
            'FREQ2': 0x0C,  # 315
            'FREQ1': 0x1D,
            'FREQ0': 0x89,
            'MDMCFG4': 0x26,  # BW 541 Data rate 1.666
            'MDMCFG3': 0x93,  # 2.500, 0x0D 1.666
            'MDMCFG2': 0x30,
            'DEVIATN': 0x62,
            'MCSM0': 0x18,
            'FOCCFG': 0x1D,
            'BSCFG': 0x1C,
            'AGCCTRL2': 0x04,
            'AGCCTRL1': 0x00,
            'AGCCTRL0': 0x92,
            'WORCTRL': 0xFB,
            'FREND1': 0xB6,
            'FREND0': 0x11,
            'FSCAL3': 0xEA,
            'FSCAL2': 0x2A,
            'FSCAL1': 0x00,
            'FSCAL0': 0x1F,
            'TEST0': 0x09
        },
        # 4
        # Livolo
        {
            'IOCFG0': 0x06,
            'PKTCTRL1': 0x00,
            'PKTCTRL0': 0x02,  # infinite length
            'PKTLEN': 0xFF,
            'FSCTRL1': 0x0C,
            'FREQ2': 0x10,  # 433.92
            'FREQ1': 0xB0,
            'FREQ0': 0x71,
            'MDMCFG4': 0x28,  # BW 541 Data rate 6.4468
            'MDMCFG3': 0x6e,  # | 9.090 0x6e | 6.4468 0x04
            'MDMCFG2': 0x32,
            'MCSM0': 0x18,
            'FOCCFG': 0x0,
            'AGCCTRL2': 0x04,
            'AGCCTRL1': 0x00,
            'AGCCTRL0': 0x92,
            'WORCTRL': 0xFB,
            'FREND1': 0xB6,
            'FREND0': 0x11,  # 0x17 PATABLE shaping
            'FSCAL3': 0xEA,
            'FSCAL2': 0x2A,
            'SYNC1': 0xFA,  # a6? --- EA при 6.4468
            'SYNC0': 0xAA,  # 66? --- AA при 6.4468
            'FSCAL1': 0x00,
            'FSCAL0': 0x1F,
            'TEST0': 0x09
        },
        # 5
        # motion sensor (tristatecode)
        {
            'IOCFG0': 0x06,
            'PKTCTRL1': 0x00,
            'PKTCTRL0': 0x02,  # fixed length
            'PKTLEN': 0xFF,
            'FSCTRL1': 0x0C,
            'FREQ2': 0x10,  # 433.6
            'FREQ1': 0xAD,
            'FREQ0': 0x4A,
            'MDMCFG4': 0x26,  # BW 541 0x27 0xA3 Datarate 5.19466 key 1.5
            'MDMCFG3': 0x23,  # 0x26 0x23 datarate 1.810 key 4.7
            'MDMCFG2': 0x32,
            'DEVIATN': 0x62,
            'MCSM0': 0x18,
            'FOCCFG': 0x1D,
            'BSCFG': 0x1C,
            'AGCCTRL2': 0x04,
            'AGCCTRL1': 0x00,
            'AGCCTRL0': 0x92,
            'WORCTRL': 0xFB,
            'FREND1': 0xB6,
            'FREND0': 0x11,
            'FSCAL3': 0xEA,
            'FSCAL2': 0x2A,
            'SYNC1': 0xEE,
            'SYNC0': 0x8E,
            'FSCAL1': 0x00,
            'FSCAL0': 0x1F,
            'TEST0': 0x09
        },
        # 6
        # water sensor (tristatecode)
        {
            #        'IOCFG0':0x06,
            'IOCFG0': 0x0E,
            'PKTCTRL1': 0x00,
            'PKTCTRL0': 0x02,  # infinite length
            'PKTLEN': 0xFF,
            'FSCTRL1': 0x0C,
            'FREQ2': 0x10,  # 433.92
            'FREQ1': 0xB0,
            'FREQ0': 0x71,
            'MDMCFG4': 0x26,  # BW 541 0x27 0xe8 Datarate 6.060 key 1.5M
            'MDMCFG3': 0x30,  # mdmcfg4: 0x26 mdmcfg3 0xb1 datarate 2.690 key 3.3M
            'MDMCFG2': 0x32,  # 0x26 0x30 datarate 1.890 key 4.7M
            'DEVIATN': 0x62,
            'MCSM0': 0x18,
            'FOCCFG': 0x1D,
            'BSCFG': 0x1C,
            #        'AGCCTRL2':0x04,
            #        'AGCCTRL1':0x00,
            #        'AGCCTRL0':0x92,
            'AGCCTRL2': 0xE3,
            'AGCCTRL1': 0x41,
            'AGCCTRL0': 0x92,
            'WORCTRL': 0xFB,
            'FREND1': 0xB6,
            'FREND0': 0x11,
            'FSCAL3': 0xEA,
            'FSCAL2': 0x2A,
            'SYNC1': 0xEE,
            'SYNC0': 0x8E,
            'FSCAL1': 0x00,
            'FSCAL0': 0x1F,
            'TEST0': 0x09
        },
        # 7
        # temperature sensor
        {
            #        'IOCFG0':0x06,
            'IOCFG0': 0x0E,
            'PKTCTRL1': 0x00,
            'PKTCTRL0': 0x02,  # infinite length
            'PKTLEN': 0xFF,
            'FSCTRL1': 0x0C,
            'FREQ2': 0x10,  # 433.92
            'FREQ1': 0xB0,
            'FREQ0': 0x71,
            #        'MDMCFG4':0x76,    #RX filter BW 232 kHz
            #        'MDMCFG3':0x4C,    #Datarate 2.058kBaud, 263680Hz, 1bit(period)=128*(1/263680), rate=1/period=2058
            'MDMCFG4': 0x78,  # RX filter BW 232 kHz Data rate 8.207
            'MDMCFG3': 0x4B,
            #        'MDMCFG2':0x32,
            'MDMCFG2': 0x34,
            'DEVIATN': 0x62,
            'MCSM0': 0x18,
            'FOCCFG': 0x1D,
            'BSCFG': 0x1C,
            #        'AGCCTRL2':0x04,
            #        'AGCCTRL2':0xE3,    #empirical value
            'AGCCTRL2': 0xE7,
            'AGCCTRL1': 0x41,  # empirical value
            'AGCCTRL0': 0x92,  # empirical value
            'WORCTRL': 0xFB,
            'FREND1': 0xB6,
            'FREND0': 0x11,
            'FSCAL3': 0xEA,
            'FSCAL2': 0x2A,
            'SYNC1': 0x01,
            'SYNC0': 0x84,
            'FSCAL1': 0x00,
            'FSCAL0': 0x1F,
            'TEST0': 0x09,
            'TEST2': 0x81,
            'TEST1': 0x35,
            'FIFOTHR': 0x47,
        }
    ]

    def __init__(self, num):
        self.obj = spidev.SpiDev()
        self.obj.open(num, 0)
        if num == 0:
            self.GDO0Pin = self.spi0_gdo0
        if num == 1:
            self.GDO0Pin = self.spi1_gdo0
        fagpio.unexport(self.GDO0Pin)
        self.GDO0State = False
        self.reset()

    def reset(self):
        if self.GDO0State:
            self.gdo0_close()
        self.config = 0
        r = self.strobe('SRES')
        while self.marcstate() != 'IDLE':
            pass
        self.state = 'IDLE'
        return r

    def close(self):
        self.reset()
        self.obj.close()

    def read_status(self, addr):
        attempts = 0
        while attempts < 3:
            try:
                # r=list(map(hex,self.obj.xfer2([self.REGISTER[addr] | self.READ_BURST,0])))
                return self.obj.xfer2([self.register[addr] | self.READ_BURST, 0])
            except IOError:
                self.strobe('SNOP')
                attempts += 1
        if attempts == 3:
            raise IOError('ReadStatus input/output error')

    def strobe(self, addr):
        attempts = 0
        while attempts < 3:
            try:
                r = list(map(hex, self.obj.xfer2([self.register[addr]])))
                break
            except IOError:
                time.sleep(0.5)
                attempts += 1
        if attempts == 3:
            raise IOError('Strobe input/output error')
        return r

    def read_reg(self, addr):
        attempts = 0
        while attempts < 3:
            try:
                r = list(map(hex, self.obj.xfer2([self.register[addr] | self.READ_SINGLE, 0])))
                break
            except IOError:
                self.strobe('SNOP')
                attempts += 1
        if attempts == 3:
            raise IOError('ReadReg input/output error')
        return r

    def read_burst_reg(self, addr, count):
        buf = [self.register[addr] | self.READ_BURST]
        for i in range(count):
            buf.append(0)
        attempts = 0
        while attempts < 3:
            try:
                return self.obj.xfer2(buf)
            # r=list(map(hex,self.obj.xfer2(buffer)))
            except IOError:
                self.strobe('SNOP')
                attempts += 1
        if attempts == 3:
            raise IOError('ReadBurstReg input/output error')

    def write_reg(self, addr, val):
        attempts = 0
        while attempts < 3:
            try:
                r = list(map(hex, self.obj.xfer2([self.register[addr], val])))
                break
            except IOError:
                self.strobe('SNOP')
                attempts += 1
        if attempts == 3:
            raise IOError('WriteReg input/output error')
        return r

    @staticmethod
    def status_byte(val):
        status = {
            '000': 'IDLE',
            '001': 'RX',
            '010': 'TX',
            '011': 'FSTXON',
            '100': 'CALIBRATE',
            '101': 'SETTLING',
            '110': 'RXFIFO_OVERFLOW',
            '111': 'TXFIFO_UNDERFLOW',
        }
        val_b = bin(val)[2:]
        val_h = '0' * (8 - len(val_b)) + val_b
        return [status[val_h[1:4]], int(val_h[4:8], 2)]

    def write_burst_reg(self, addr, buf):
        buf.insert(0, self.register[addr] | self.WRITE_BURST)
        attempts = 0
        while attempts < 3:
            try:
                r = list(map(hex, self.obj.xfer2(buf)))
                break
            except IOError:
                self.strobe('SNOP')
                attempts += 1
        if attempts == 3:
            raise IOError('WriteBurstReg input/output error')
        del buf[0]
        return r

    def write_settings(self, num):
        buf = []
        self.config = num
        # self.WriteBurstReg('PATABLE',[0,0x1d,0,0,0,0,0,0]) #setting 1
        # self.WriteBurstReg('PATABLE',[0,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d]) #setting 2
        set_list = self.rf_settings[num]
        self.write_burst_reg('PATABLE', [0, 0xC0, 0xC0, 0xC0, 0xC0, 0xC0, 0xC0, 0xC0])
        for key in set_list.keys():
            buf.append(key)
            self.write_reg(key, set_list[key])
            time.sleep(0.001)
            buf.append(self.read_reg(key)[1])
            time.sleep(0.001)
        return buf

    def print_settings(self):
        buf = []
        print('settings number is: ' + str(self.config))
        sort_register = sorted(self.register.items(), key=operator.itemgetter(1))
        for i in sort_register:
            buf.append(i[0])
            buf.append(self.read_reg(i[0])[1])
            if i[1] == 46:
                break
        return buf

    def gdo0_open(self):
        p = self.GDO0Pin
        fagpio.export(p)
        p_obj = fagpio.gpio(p)
        p_obj.active = 0
        p_obj.direction = 'in'
        p_obj.edge = 'rising'
        self.GDO0File = p_obj.fvalue
        self.epoll_obj = p_obj.epoll_obj
        self.GDO0State = True

    def gdo0_close(self):
        self.epoll_obj.close()
        fagpio.unexport(self.GDO0Pin)
        self.GDO0State = False

    def freq(self, x):
        if (300 < x < 348) or (387 < x < 464) or (779 < x < 928):
            hex_freq = hex(math.trunc((x * math.pow(2, 16)) / 26))
            if len(hex_freq) == 7:
                freq2 = int('0x' + hex_freq[2], 16)
                freq1 = int('0x' + hex_freq[3:5], 16)
                freq0 = int('0x' + hex_freq[5:7], 16)
            elif len(hex_freq) == 8:
                freq2 = int('0x' + hex_freq[2:4], 16)
                freq1 = int('0x' + hex_freq[4:6], 16)
                freq0 = int('0x' + hex_freq[6:8], 16)
            else:
                raise Exception("The frequency should be whithin the following ranges: 300-348, 387-464, 779-928")
        return self.write_burst_reg('FREQ2', [freq2, freq1, freq0])

    # page 35
    def datarate(self, rate=0):
        if rate > 0:
            drate_e = math.trunc((math.log((((rate / 1000.0) * math.pow(2, 20)) / 26), 2)))
            drate_m = int(round((((rate / 1000.0) * math.pow(2, 28)) / (26 * math.pow(2, drate_e))) - 256))
            if drate_m == 256:
                drate_e += 1
                drate_m = 0
            m4 = (int(self.read_reg('MDMCFG4')[1], 16) & 0xF0) + int(drate_e)
            m3 = drate_m
            print hex(m4), hex(m3)
            return self.write_burst_reg('MDMCFG4', [m4, m3])
        else:
            drate_m = int(self.read_reg('MDMCFG3')[1], 16)
            drate_e = int(self.read_reg('MDMCFG4')[1], 16) & 0xF
            rate = round((((256 + drate_m) * math.pow(2, drate_e)) * 26000) / math.pow(2, 28), 5)
            return rate

    def init(self, num):
        self.reset()
        return self.write_settings(num)

    def marcstate(self):
        return self.Marcstate_reg[self.read_status('MARCSTATE')[1]]

    def stx(self):
        self.strobe('STX')
        while self.marcstate() != 'TX':
            pass
        self.state = 'TX'

    def srx(self):
        self.strobe('SRX')
        while self.marcstate() != 'RX':
            pass
        self.state = 'RX'

    def sidle(self):
        self.strobe('SIDLE')
        while self.marcstate() != 'IDLE':
            pass
        self.state = 'IDLE'

    def flush_rx(self):
        self.sidle()
        self.strobe('SFRX')

    def flush_tx(self):
        self.sidle()
        self.strobe('SFTX')

    def send(self, buf):
        self.write_burst_reg('TXFIFO', buf)
        self.stx()

    def send2(self, buf):
        try:
            cur = 64
            len_buffer = len(buf)
            threshold = (len_buffer - (len_buffer % 64))
            self.flush_tx()
            self.write_burst_reg('TXFIFO', buf[0:64])
            self.stx()
            flag = True
            while cur < len_buffer:
                if cur > threshold and flag:
                    self.write_reg('PKTCTRL0', 0x00)
                    print("Turn to fixed packet length with threshold is %s" % threshold)
                    flag = False
                time.sleep(0.012)
                sum_bytes = 64 - int(self.read_status('TXBYTES')[1], 16)
                print(sum_bytes, cur)
                if sum_bytes > 0:
                    if (cur + sum_bytes) < len_buffer:
                        self.write_burst_reg('TXFIFO', buf[cur:cur + sum_bytes])
                    else:
                        self.write_burst_reg('TXFIFO', buf[cur:len_buffer + 1])
                        print(len_buffer - cur, len_buffer)
                        # print(self.ReadStatus('MARCSTATE'))
                        self.sidle()
                        # print(self.ReadStatus('MARCSTATE'))
                        break
                else:
                    self.flush_tx()
                    self.stx()
                    sum_bytes = 0
                cur += sum_bytes
            self.write_reg('PKTCTRL0', 0x02)
            return True
        except Exception, e:
            print(str(e))
            return False

    def button_b(self):
        self.check_settings(3)
        len_pack = 255
        self.write_reg('PKTLEN', len_pack)
        packet = [0x80, 0x00, 0x00, 0x00, 0xEE, 0xEE, 0xEE, 0x8E, 0x88, 0x8E, 0x8E, 0x88, 0x88, 0x88, 0xEE, 0x88]
        big_packet = self.inc_packet(packet, len_pack)
        return self.send2(big_packet)

    def button_a(self):
        self.check_settings(3)
        len_pack = 255
        self.write_reg('PKTLEN', len_pack)
        packet = [0x80, 0x00, 0x00, 0x00, 0xEE, 0xEE, 0xEE, 0x8E, 0x88, 0x8E, 0x8E, 0x88, 0x88, 0x88, 0x88, 0xEE]
        big_packet = self.inc_packet(packet, len_pack)
        return self.send2(big_packet)

    def button_c(self):
        self.check_settings(3)
        len_pack = 255
        self.write_reg('PKTLEN', len_pack)
        packet = [0x80, 0x00, 0x00, 0x00, 0xEE, 0xEE, 0xEE, 0x8E, 0x88, 0x8E, 0x8E, 0x88, 0x88, 0xEE, 0x88, 0x88]
        big_packet = self.inc_packet(packet, len_pack)
        return self.send2(big_packet)

    @staticmethod
    def inc_packet(pack, size):
        new_packet = []
        cur = 0
        while len(new_packet) < size:
            if cur > (len(pack) - 1):
                cur = 0
            new_packet.append(pack[cur])
            cur = cur + 1
        return new_packet

    def check_settings(self, num):
        if self.config != num:
            self.write_settings(num)

            # 5 видов сигнала: sync(11111) 550 микросек., короткая 1(1) 110 микросек., короткий 0(0) 110 микросек.,
            # длинная 1(111) 330 микросекунд, длинный 0(000) 330 микросекунд.
            # посылка повторяется много раз
            # пример кнопки пульта: 11111 01 01 01 01 01 01 01 01 000 111 000 111 000 111 000 111 01 01 01 000 10 10 10
            #                       -----_-_-_-_-_-_-_-_-___---___---___---___---_-_-_-___-_-_-_
            # если считать 01 и 10 за 0, а 000 и 111 за 1 и отбросим sync то получим: 00000000111111110 00100 0
            # начальная часть всегда повторяется, а пакет должен заканчиваться 0, следовательно код кнопки ^ вот 00100
            # и состоит из 5 бит, т.е. число от 0 до 31
            # так как посылка формируется из байт, а в пакете 60 бит, то умножим плученный пакет на 2
            # и получим (60*2/8) 15 байт

    @staticmethod
    def livolo_button(val):
        if 0 < val < 32:
            packet_start = '11111010101010101010100011100011100011100011101'
            packet_end = '10'
            packet_button = ''
            s = {'0': {1: '01', -1: '10'}, '1': {1: '000', -1: '111'}}
            # nul = {1: '01', -1: '10'}
            # one = {1: '000', -1: '111'}
            f = 1
            for i in (lambda x: '0' * (5 - bin(x)[2:].__len__()) + bin(x)[2:])(val):
                packet_button += s[i][f]
                if i == '1':
                    f *= -1
            packet_bin = 2 * (packet_start + packet_button + packet_end)
            packet = []
            for i in range(0, len(packet_bin) / 8):
                packet.append(int(packet_bin[i * 8:i * 8 + 8], 2))
            return packet
        else:
            return 0

    def livolo_a(self):
        self.check_settings(4)
        packet = self.livolo_button(4)
        big_packet = self.inc_packet(packet, self.livolo_packet_len)
        return self.send2(big_packet)

    def livolo_b(self):
        self.check_settings(4)
        packet = self.livolo_button(8)
        big_packet = self.inc_packet(packet, self.livolo_packet_len)
        return self.send2(big_packet)

    def livolo_c(self):
        self.check_settings(4)
        packet = self.livolo_button(28)
        big_packet = self.inc_packet(packet, self.livolo_packet_len)
        return self.send2(big_packet)

    def livolo_d(self):
        self.check_settings(4)
        packet = self.livolo_button(21)
        big_packet = self.inc_packet(packet, self.livolo_packet_len)
        return self.send2(big_packet)

    def livolo_e(self):
        self.check_settings(4)
        packet = self.livolo_button(16)
        big_packet = self.inc_packet(packet, self.livolo_packet_len)
        return self.send2(big_packet)

    def livolo_h(self):
        self.check_settings(4)
        packet = self.livolo_button(7)
        big_packet = self.inc_packet(packet, self.livolo_packet_len)
        return self.send2(big_packet)

    @staticmethod
    def packet_code(b):
        # Найти все последовательности 0 и 1
        p0_r = re.compile('(0+)1')
        p1_r = re.compile('(1+)0')
        g0 = p0_r.findall(b)
        g1 = p1_r.findall(b)
        g = g0 + g1
        # Найти словарь, для декодирования пакета
        # Составить список из последовательностей 0 и 1 и их количества повторений
        pack = [[x, g.count(x)] for x in set(g) if x]
        # сортировать по кол-ву повторов последовательности
        sorted_pack = sorted(pack, key=operator.itemgetter(1))
        # print sorted_pack
        # Значения отличающиеся на один символ принимать за одну последовательность
        for j in range(0, len(sorted_pack)):
            for i in range(j, len(sorted_pack)):
                if (sorted_pack[i][0][0] == sorted_pack[j][0][0]) and (
                            int(math.fabs(len(sorted_pack[i][0]) - len(sorted_pack[j][0]))) in (1,)):
                    sorted_pack[i][1] += sorted_pack[j][1]
                    break
        # еще раз сортировать на случай изменения порядка
        sorted_pack = sorted(sorted_pack, key=operator.itemgetter(1))
        print sorted_pack
        decode_dict = {}
        m_g0 = max(g0)
        m_g1 = max(g1)
        sync_sign = m_g0[0] if len(m_g0) > len(m_g1) else m_g1[0]
        # Из 4 чаще повторяющиехся послед. отобрать длинную 0(l0), короткую 0(s0), длинную 1(l1), короткую 1(s1) .
        decode_dict['s0'] = min([sorted_pack[i][0] for i in xrange(-4, 0) if sorted_pack[i][0][0] == '0'])
        decode_dict['l0'] = max([sorted_pack[i][0] for i in xrange(-4, 0) if sorted_pack[i][0][0] == '0'])
        decode_dict['s1'] = min([sorted_pack[i][0] for i in xrange(-4, 0) if sorted_pack[i][0][0] == '1'])
        decode_dict['l1'] = max([sorted_pack[i][0] for i in xrange(-4, 0) if sorted_pack[i][0][0] == '1'])
        # print decode_dict
        # Устанавливаем точность, что бы захватить сигналы ктр. длиннее или короче тех, ктр. чаще повторяются
        diff0 = len(decode_dict['l0']) - len(decode_dict['s0'])
        diff1 = len(decode_dict['l1']) - len(decode_dict['s1'])
        accuracy0 = diff0 / 2 - 1 if diff0 > 1 else 0
        accuracy1 = diff1 / 2 - 1 if diff1 > 1 else 0
        accuracy_sync = accuracy0 if sync_sign == 0 else accuracy1
        decode_dict['sync'] = decode_dict['l0'] + sync_sign * (accuracy0/2+1) if sync_sign == '0' else decode_dict['l1'] + sync_sign * (accuracy1/2+1)
        rs = re.compile(str(int(not int(decode_dict['sync'][0]))) + '+' + decode_dict['sync'] + '[' +
                        decode_dict['sync'][0] + ']{0,}')
        packet = {}
        # Если в кодировании учавствует 3 вида сигнала, то 3 и 4 последоват. по кол-ву повторений
        # будут отличаться больше, чем в 2 раза (temp)
        if sorted_pack[-3][1] / float(sorted_pack[-4][1]) > 2:
            r0 = re.compile(
                decode_dict['s1'][0] + '+' + decode_dict['s0'][accuracy0:] + '[0]{0,' + str(accuracy0 * 2) + '}')
            r1 = re.compile(
                decode_dict['s1'][0] + '+' + decode_dict['l0'][accuracy0:] + '[0]{0,' + str(accuracy0 * 2) + '}')
            packet['type'] = 'tmp'
        # Иначе в кодировании учавствует 4 вида сигнала
        else:
            # Если 4 коротких сигнала идут подряд и байт синх. состоит из 1, то s0s1=0, s1s0=0, l0=1, l1=1 (livolo)
            if decode_dict['sync'][0]=='1' and decode_dict['s0'] + decode_dict['s1'] + decode_dict['s0'] + decode_dict['s1'] in b:
                # or (decode_dict['s0']+decode_dict['s1']+decode_dict['l0']+decode_dict['l1'] in b):
                r0 = re.compile(decode_dict['s1'][
                                accuracy1:] + '[1]{0,' + str(accuracy1 * 2) + '}' + decode_dict['s0'][
                                accuracy0:] + '[0]{0,' + str(accuracy0 * 2) + '}|' + decode_dict['s0'][
                                accuracy0:] + '[0]{0,' + str(accuracy1 * 2) + '}' + decode_dict['s1'][
                                accuracy1:] + '[1]{0,' + str(accuracy0 * 2) + '}')
                r1 = re.compile(decode_dict['l1'][
                                accuracy1:] + '[1]{0,' + str(accuracy1 * 2) + '}|' + decode_dict['l0'][
                                accuracy0:] + '[0]{0,' + str(accuracy0 * 2) + '}|' + decode_dict['l0'][
                                accuracy0:] + '[0]{0,' + str(accuracy1 * 2) + '}' + decode_dict['l1'][
                                accuracy1:] + '[1]{0,' + str(accuracy0 * 2) + '}')
                rs = re.compile(decode_dict['sync'][accuracy_sync:] + '[' + decode_dict['sync'][0] + ']{0,}')
                packet['type'] = 'liv'
            else:
                # предварительно считать 0 это s1l0(11100000000), 1 это l1s0(00000000111) (car,3state)
                r0 = re.compile(decode_dict['s1'][
                                accuracy1:] + '[1]{0,' + str(accuracy1 * 2) + '}' + decode_dict['l0'][
                                accuracy0:] + '[0]{0,' + str(accuracy0 * 2) + '}')
                r1 = re.compile(decode_dict['l1'][
                                accuracy1:] + '[1]{0,' + str(accuracy1 * 2) + '}' + decode_dict['s0'][
                                accuracy0:] + '[0]{0,' + str(accuracy0 * 2) + '}')
                packet['type'] = '4st'
        rg = re.compile('[oo|ll|ol|lo]+')
        group = rg.findall(r0.sub('o', r1.sub('l', rs.sub('s', b))))
        # найти чаще всего повторяющиеся
        code_message = sorted([[x, group.count(x)] for x in set(group) if x], key=operator.itemgetter(1))
        print code_message
        packet['code'] = code_message[-1][0].replace('o', '0').replace('l', '1')
        # print message
        return packet

    @staticmethod
    def decode(b):
        packet = Cc1101.packet_code(Cc1101.human_bin(b))

        def toint(s):
            return str(int(s, 2))

        if packet['type'] == '4st':
            packet['message'] = ''
            dict = {'00': '0', '11': '1', '01': 'f', '10': 'g'}
            # Разделить весь код на список из двух символов и подставить в соответствие словарю
            for c in [packet['code'][x:x + 2] for x in range(0, len(packet['code']), 2)]:
                packet['message'] += dict[c]
        elif packet['type'] == 'liv':
            packet['message'] = int(packet['code'][17:22], 2)
        elif packet['type'] == 'tmp':
            sign = int(packet['code'][16:17])
            # Если двоичный код температуры начинается с 1, то значение отрицательное(смотри "дополнительный код")
            if sign:
                t = (~(int(packet['code'][16:28], 2) ^ 0xfff)) / 10.0
            else:
                t = int(packet['code'][16:28], 2) / 10.0
            packet['message'] = toint(packet['code'][0:4]) + ':' + toint(packet['code'][4:12]) + ':' + toint(
                packet['code'][12:13]) + ':' + toint(packet['code'][13:14]) + ':' + toint(
                packet['code'][14:16]) + ':' + str(round(t, 1)) + ':' + toint(packet['code'][28:36])
        print packet['code']
        print packet['message']
        return packet

    @staticmethod
    def human_bin(buf):
        r = ''
        l = []
        for i in range(0, len(buf)):
            l.append(bin(buf[i])[2:])
            l[i] = (8 - len(l[i])) * '0' + l[i]
            r = r + l[i]
        print r
        return r

    @staticmethod
    def rssi_dbm(x):
        rssi_offset = 74
        if x >= 128:
            rssi = (x - 256) / 2 - rssi_offset
        else:
            rssi = (x / 2) - rssi_offset
        return rssi

    def scan_datarate(self, start, end, step):
        dr = start
        while dr < end:
            self.datarate(dr)
            print(str(dr))
            dr += step
            time.sleep(self.scan_timeout)

    def scan_freq(self, start, end, step):
        freq = start
        while freq < end:
            self.freq(freq)
            print(str(freq))
            freq += step
            time.sleep(self.scan_timeout)

    def read_buffer(self):
        buf = []
        while True:
            #            Читать кол-во байт, пока не повторится. стр. 56
            #            while (bytes!=int(self.ReadStatus('RXBYTES')[1],16)) or (bytes<2):
            bytes_ = 0
            less_count = 0
            while bytes_ < 2:
                packet = self.read_status('RXBYTES')
                status_byte, bytes_ = packet[0], packet[1]
                #                status,bytes_= self.StatusByte(status_byte)
                #                print status,bytes_,bytes
                #                print status_byte,bytes
                less_count += 1
                #               page 31
                #               if less_count>5 or status=='RXFIFO_OVERFLOW':
                if less_count > self.read_threshold or status_byte >= 96:
                    # print buffer
                    self.flush_rx()
                    self.gdo0_close()
                    # return self.PackSign(self.HumanBin(buffer))
                    # return self.BufferConvert(self.config)(buffer)
                    return self.decode(buf)
            # bytes-1 потому что нельзя считывать последний байт
            # до окончания всей передачи. стр 56
            part = self.read_burst_reg('RXFIFO', bytes_ - 1)[1:]
            buf += part

    def receive(self):
        if not self.GDO0State:
            self.gdo0_open()

        def run():
            self.flush_rx()
            self.srx()
            print('start...')
            while True:
                events = self.epoll_obj.poll(1)
                # print(events,self.GDO0File.fileno())
                for fileno, event in events:
                    if fileno == self.GDO0File.fileno():
                        print(time.ctime())
                        self.RSSI = self.read_status('RSSI')[1]
                        # print(self.RSSI)
                        # print('RSSI: '+str(self.RssiDbm(int(self.RSSI,0)))+' db')
                        print('RSSI: ' + str(self.rssi_dbm(self.RSSI)) + ' db')
                        return self.read_buffer()

        try:
            rez = run()
            self.flush_rx()
            return rez
        except KeyboardInterrupt:
            self.gdo0_close()
        except IOError:
            print 'IOError'
            self.gdo0_close()
            self.receive()


if __name__ == "__main__":
    a = Cc1101(0)
    a.init(7)
    a.receive()
    a.close()

#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals
import spidev
import time
import operator
import fagpio
import select
import math

class cc1101:
    #------------------------------------------------------------------------------------------------------
    # CC1101 STROBE, CONTROL AND STATUS REGSITER

    REGISTER={
        'IOCFG2':0x00,      # GDO2 output pin configuration
        'IOCFG1':0x01,      # GDO1 output pin configuration
        'IOCFG0':0x02,      # GDO0 output pin configuration
        'FIFOTHR':0x03,     # RX FIFO and TX FIFO thresholds
        'SYNC1':0x04,       # Sync word, high byte
        'SYNC0':0x05,       # Sync word, low byte
        'PKTLEN':0x06,      # Packet length
        'PKTCTRL1':0x07,    # Packet automation control
        'PKTCTRL0':0x08,    # Packet automation control
        'ADDR':0x09,        # Device address
        'CHANNR':0x0A,      # Channel number
        'FSCTRL1':0x0B,     # Frequency synthesizer control
        'FSCTRL0':0x0C,     # Frequency synthesizer control
        'FREQ2':0x0D,       # Frequency control word, high byte
        'FREQ1':0x0E,       # Frequency control word, middle byte
        'FREQ0':0x0F,       # Frequency control word, low byte
        'MDMCFG4':0x10,     # Modem configuration
        'MDMCFG3':0x11,     # Modem configuration
        'MDMCFG2':0x12,     # Modem configuration
        'MDMCFG1':0x13,     # Modem configuration
        'MDMCFG0':0x14,     # Modem configuration
        'DEVIATN':0x15,     # Modem deviation setting
        'MCSM2':0x16,       # Main Radio Control State Machine configuration
        'MCSM1':0x17,       # Main Radio Control State Machine configuration
        'MCSM0':0x18,       # Main Radio Control State Machine configuration
        'FOCCFG':0x19,      # Frequency Offset Compensation configuration
        'BSCFG':0x1A,       # Bit Synchronization configuration
        'AGCCTRL2':0x1B,    # AGC control
        'AGCCTRL1':0x1C,    # AGC control
        'AGCCTRL0':0x1D,    # AGC control
        'WOREVT1':0x1E,     # High byte Event 0 timeout
        'WOREVT0':0x1F,     # Low byte Event 0 timeout
        'WORCTRL':0x20,     # Wake On Radio control
        'FREND1':0x21,      # Front end RX configuration
        'FREND0':0x22,      # Front end TX configuration
        'FSCAL3':0x23,      # Frequency synthesizer calibration
        'FSCAL2':0x24,      # Frequency synthesizer calibration
        'FSCAL1':0x25,      # Frequency synthesizer calibration
        'FSCAL0':0x26,      # Frequency synthesizer calibration
        'RCCTRL1':0x27,     # RC oscillator configuration
        'RCCTRL0':0x28,     # RC oscillator configuration
        'FSTEST':0x29,      # Frequency synthesizer calibration control
        'PTEST':0x2A,       # Production test
        'AGCTEST':0x2B,     # AGC test
        'TEST2':0x2C,       # Various test settings
        'TEST1':0x2D,       # Various test settings
        'TEST0':0x2E,       # Various test settings

    # Strobe commands
        'SRES':0x30,        # Reset chip.
        'SFSTXON':0x31,     # Enable and calibrate frequency synthesizer (if MCSM0.FS_AUTOCAL=1).
                     # If in RX/TX: Go to a wait state where only the synthesizer is
                     # running (for quick RX / TX turnaround).
        'SXOFF':0x32,       # Turn off crystal oscillator.
        'SCAL':0x33,        # Calibrate frequency synthesizer and turn it off
                     # (enables quick start).
        'SRX':0x34,         # Enable RX. Perform calibration first if coming from IDLE and
                     # MCSM0.FS_AUTOCAL=1.
        'STX':0x35,         # In IDLE state: Enable TX. Perform calibration first if
                     # MCSM0.FS_AUTOCAL=1. If in RX state and CCA is enabled:
                     # Only go to TX if channel is clear.
        'SIDLE':0x36,       # Exit RX / TX, turn off frequency synthesizer and exit
                     # Wake-On-Radio mode if applicable.
        'SAFC':0x37,        # Perform AFC adjustment of the frequency synthesizer
        'SWOR':0x38,        # Start automatic RX polling sequence (Wake-on-Radio)
        'SPWD':0x39,        # Enter power down mode when CSn goes high.
        'SFRX':0x3A,        # Flush the RX FIFO buffer.
        'SFTX':0x3B,        # Flush the TX FIFO buffer.
        'SWORRST':0x3C,     # Reset real time clock.
        'SNOP':0x3D,        # No operation. May be used to pad strobe commands to two
                     # bytes for simpler software.

        'PARTNUM':0x30,
        'VERSION':0x31,
        'FREQEST':0x32,
        'LQI':0x33,
        'RSSI':0x34,
        'MARCSTATE':0x35,
        'WORTIME1':0x36,
        'WORTIME0':0x37,
        'PKTSTATUS':0x38,
        'VCO_VC_DAC':0x39,
        'TXBYTES':0x3A,
        'RXBYTES':0x3B,
        'RCCTRL1_STATUS':0x3C,
        'RCCTRL0_STATUS':0x3D,

        'PATABLE':0x3E,
        'TXFIFO':0x3F,
        'RXFIFO':0x3F
    }

    Marcstate_reg={
        '0x0':'SLEEP',
        '0x1':'IDLE',
        '0x2':'XOFF',
        '0x3':'VCOON_MC',
        '0x4':'REGON_MC',
        '0x5':'MANCAL',
        '0x6':'VCOON',
        '0x7':'REGON',
        '0x8':'STARTCAL',
        '0x9':'BWBOOST',
        '0xa':'FS_LOCK',
        '0xb':'IFADCON',
        '0xc':'ENDCAL',
        '0xd':'RX',
        '0xe':'RX_END',
        '0xf':'RX_RST',
        '0x10':'TXRX_SWITCH',
        '0x11':'RXFIFO_OVERFLOW',
        '0x12':'FSTXON',
        '0x13':'TX',
        '0x14':'TX_END',
        '0x15':'RXTX_SWITCH',
        '0x16':'TXFIFO_UNDERFLOW'
    }

    WRITE_BURST=0x40
    READ_SINGLE=0x80
    READ_BURST=0xC0

    # FREQ_433_CC1101
    # Chipcon
    # Product = CC1101
    # Chip version = A   (VERSION = 0x04)
    # Crystal accuracy = 10 ppm
    # X-tal frequency = 26 MHz
    # RF output power = 0 dBm
    # RX filterbandwidth = 541.666667 kHz
    # Deviation = 127 kHz
    # Datarate = 249.938965 kBaud
    # Modulation = (1) GFSK
    # Manchester enable = (0) Manchester disabled
    # RF Frequency = 432.999817 MHz
    # Channel spacing = 199.951172 kHz
    # Channel number = 0
    # Optimization = Sensitivity
    # Sync mode = (3) 30/32 sync word bits detected
    # Format of RX/TX data = (0) Normal mode, use FIFOs for RX and TX
    # CRC operation = (1) CRC calculation in TX and CRC check in RX enabled
    # Forward Error Correction = (0) FEC disabled
    # Length configuration = (1) Variable length packets, packet length configured by the first received byte after sync word.
    # Packetlength = 255
    # Preamble count = (2)  4 bytes
    # Append status = 1
    # Address check = (0) No address check
    # FIFO autoflush = 0
    # Device address = 0
    # GDO0 signal selection = ( 6) Asserts when sync word has been sent / received, and de-asserts at the end of the packet
    # GDO2 signal selection = (41) CHIP_RDY

    RF_SETTINGS = {
        'FSCTRL1':0x0C,   # FSCTRL1   Frequency synthesizer control.
        'FSCTRL0':0x00,   # FSCTRL0   Frequency synthesizer control.
        'FREQ2':0x10,   # FREQ2     Frequency control word, high byte.
        'FREQ1':0xA7,   # FREQ1     Frequency control word, middle byte.
        'FREQ0':0x62,   # FREQ0     Frequency control word, low byte.
        'MDMCFG4':0x2D,   # MDMCFG4   Modem configuration.
        'MDMCFG3':0x3B,   # MDMCFG3   Modem configuration.
        'MDMCFG2':0x13,   # MDMCFG2   Modem configuration.
        'MDMCFG1':0x22,   # MDMCFG1   Modem configuration.
        'MDMCFG0':0xF8,   # MDMCFG0   Modem configuration.
        'CHANNR':0x00,   # CHANNR    Channel number.
        'DEVIATN':0x62,   # DEVIATN   Modem deviation setting (when FSK modulation is enabled).
        'FREND1':0xB6,   # FREND1    Front end RX configuration.
        'FREND0':0x10,   # FREND0    Front end TX configuration.
        'MCSM0':0x18,   # MCSM0     Main Radio Control State Machine configuration.
        'FOCCFG':0x1D,   # FOCCFG    Frequency Offset Compensation Configuration.
        'BSCFG':0x1C,   # BSCFG     Bit synchronization Configuration.
        'AGCCTRL2':0xC7,   # AGCCTRL2  AGC control.
        'AGCCTRL1':0x00,   # AGCCTRL1  AGC control.
        'AGCCTRL0':0xB0,   # AGCCTRL0  AGC control.
        'FSCAL3':0xEA,   # FSCAL3    Frequency synthesizer calibration.
        'FSCAL2':0x2A,   # FSCAL2    Frequency synthesizer calibration.
        'FSCAL1':0x00,   # FSCAL1    Frequency synthesizer calibration.
        'FSCAL0':0x1F,   # FSCAL0    Frequency synthesizer calibration.
        'FSTEST':0x59,   # FSTEST    Frequency synthesizer calibration.
        'TEST2':0x88,   # TEST2     Various test settings.
        'TEST1':0x31,   # TEST1     Various test settings.
        'TEST0':0x09,   # TEST0     Various test settings.
        'FIFOTHR':0x07,   # FIFOTHR   RXFIFO and TXFIFO thresholds.
        'IOCFG2':0x29,   # IOCFG2    GDO2 output pin configuration.
        'IOCFG0':0x06,   # IOCFG0D   GDO0 output pin configuration. 
        'PKTCTRL1':0x04,   # PKTCTRL1  Packet automation control.
        'PKTCTRL0':0x05,   # PKTCTRL0  Packet automation control.
        'ADDR':0x00,   # ADDR      Device address.
        'PKTLEN':0xFF,    # PKTLEN    Packet length.
        'PATABLE':0x1d
    }

    RF_SETTINGS1 = {
        'IOCFG0':0x06,
        'PKTCTRL0':0x05,
        'FSCTRL1':0x0C,
        'FREQ2':0x10,
        'FREQ1':0xB0,
        'FREQ0':0x71,
        'MDMCFG4':0x2D,
        'MDMCFG3':0x3B,
        'MDMCFG2':0x3B,
        'DEVIATN':0x62,
        'MCSM0':0x18,
        'FOCCFG':0x1D,
        'BSCFG':0x1C,
        'AGCCTRL2':0x04,
        'AGCCTRL1':0x00,
        'AGCCTRL0':0x92,
        'WORCTRL':0xFB,
        'FREND1':0xB6,
        'FREND0':0x11,
        'FSCAL3':0xEA,
        'FSCAL2':0x2A,
        'FSCAL1':0x00,
        'FSCAL0':0x1F,
        'TEST0':0x09
    }

    # Asynch with rx on GDO0
    RF_SETTINGS2 = {
        'IOCFG0':0x0D,
        'PKTCTRL1':0x00,
        'PKTCTRL0':0x32,
        'FSCTRL1':0x06,
        'FREQ2':0x10,   # freq 433,92
        'FREQ1':0xB0,
        'FREQ0':0x71,
        'MDMCFG4':0x27,    # BW 270 Data rate 3.335
        'MDMCFG3':0x0D,
        'MDMCFG2':0x30,
        'DEVIATN':0x42,
        'MCSM0':0x18,
        'FOCCFG':0x14,
        'BSCFG':0x1C,
        'AGCCTRL2':0x04,
        'AGCCTRL1':0x00,
        'AGCCTRL0':0x92,
        'WORCTRL':0xFB,
        'FREND1':0xB6,
        'FREND0':0x11,
        'FSCAL3':0xEA,
        'FSCAL2':0x2A,
        'FSCAL1':0x00,
        'FSCAL0':0x1F,
        'TEST0':0x09,
        'TEST1':0x35,
        'TEST2':0x81,
        'FIFOTHR':0x47
        }

    #RF_SETTINGS2 = {
    #    'IOCFG0':0x0D,
    #    'PKTCTRL1':0x00,
    #    'PKTCTRL0':0x32,
    #    'FSCTRL1':0x0C,
    #    'FREQ2':0x10,
    #    'FREQ1':0xB0,
    #    'FREQ0':0x71,
    #    'MDMCFG4':0x28,    # BW 500 Data rate 9.6
    #    'MDMCFG3':0x83,
    #    'MDMCFG2':0x30,
    #    'DEVIATN':0x62,
    #    'MCSM0':0x18,
    #    'FOCCFG':0x1D,
    #    'BSCFG':0x1C,
    #    'AGCCTRL2':0x04,
    #    'AGCCTRL1':0x00,
    #    'AGCCTRL0':0x92,
    #    'WORCTRL':0xFB,
    #    'FREND1':0xB6,
    #    'FREND0':0x11,
    #    'FSCAL3':0xEA,
    #    'FSCAL2':0x2A,
    #    'FSCAL1':0x00,
    #    'FSCAL0':0x1F,
    #    'TEST0':0x09
    #    }

    #RF_SETTINGS3 = {
    #    'IOCFG0':0x4D,
    #    'PKTCTRL1':0x00,
    #    'PKTCTRL0':0x32,
    #    'FSCTRL1':0x08,
    #    'FREQ2':0x10,
    #    'FREQ1':0xB0,
    #    'FREQ0':0x71,
    #    'MDMCFG4':0x87,    # BW 200 Data rate 4.8
    #    'MDMCFG3':0x83,
    #    'MDMCFG2':0x30,
    #    'DEVIATN':0x42,
    #    'MCSM0':0x18,
    #    'FOCCFG':0x1D,
    #    'BSCFG':0x1C,
    #    'AGCCTRL2':0x04,
    #    'AGCCTRL1':0x00,
    #    'AGCCTRL0':0x92,
    #    'WORCTRL':0xFB,
    #    'FREND1':0xB6,
    #    'FREND0':0x11,
    #    'FSCAL3':0xEA,
    #    'FSCAL2':0x2A,
    #    'FSCAL1':0x00,
    #    'FSCAL0':0x1F,
    #    'TEST0':0x09,
    #    'TEST1':0x35,
    #    'TEST2':0x81
    #    }

    # Simple naked packet for Asynch
    RF_SETTINGS3 = {
        'IOCFG0':0x06,
        'PKTCTRL1':0x00,
        'PKTCTRL0':0x00,    #fixed length
        'PKTLEN':0x40,
        'FSCTRL1':0x0C,
        'FREQ2':0x0C,   # 315
        'FREQ1':0x1D,
        'FREQ0':0x89,
        'MDMCFG4':0x26,    #BW 541 Data rate 1.666
        'MDMCFG3':0x93,    #2.500, 0x0D 1.666
        'MDMCFG2':0x30,
        'DEVIATN':0x62,
        'MCSM0':0x18,
        'FOCCFG':0x1D,
        'BSCFG':0x1C,
        'AGCCTRL2':0x04,
        'AGCCTRL1':0x00,
        'AGCCTRL0':0x92,
        'WORCTRL':0xFB,
        'FREND1':0xB6,
        'FREND0':0x11,
        'FSCAL3':0xEA,
        'FSCAL2':0x2A,
        'FSCAL1':0x00,
        'FSCAL0':0x1F,
        'TEST0':0x09
        }

    RF_SETTINGS4 = {
        'IOCFG0':0x06,
        'PKTCTRL1':0x00,
        'PKTCTRL0':0x02,    #infinite length
        'PKTLEN':0xFF,
        'FSCTRL1':0x0C,
        'FREQ2':0x10,   # 433.92
        'FREQ1':0xB0,
        'FREQ0':0x71,
        'MDMCFG4':0x28,    #BW 541 Data rate 6.4468
        'MDMCFG3':0x04,
        'MDMCFG2':0x32,
        'MCSM0':0x18,
        'FOCCFG':0x0,
        'AGCCTRL2':0x04,
        'AGCCTRL1':0x00,
        'AGCCTRL0':0x92,
        'WORCTRL':0xFB,
        'FREND1':0xB6,
        'FREND0':0x11,   #0x17 PATABLE shaping
        'FSCAL3':0xEA,
        'FSCAL2':0x2A,
        'SYNC1':0xEA,#a6
        'SYNC0':0xAA,#66
        'FSCAL1':0x00,
        'FSCAL0':0x1F,
        'TEST0':0x09
        }

# motion sensor
    RF_SETTINGS5 = {
        'IOCFG0':0x06,
        'PKTCTRL1':0x00,
        'PKTCTRL0':0x02,    #fixed length
        'PKTLEN':0xFF,
        'FSCTRL1':0x0C,
        'FREQ2':0x10,   # 433.6
        'FREQ1':0xAD,
        'FREQ0':0x4A,
        'MDMCFG4':0x27,    #BW 541 Data rate 5.19466
        'MDMCFG3':0xA3,
        'MDMCFG2':0x32,
        'DEVIATN':0x62,
        'MCSM0':0x18,
        'FOCCFG':0x1D,
        'BSCFG':0x1C,
        'AGCCTRL2':0x04,
        'AGCCTRL1':0x00,
        'AGCCTRL0':0x92,
        'WORCTRL':0xFB,
        'FREND1':0xB6,
        'FREND0':0x11,
        'FSCAL3':0xEA,
        'FSCAL2':0x2A,
        'SYNC1':0xEE,
        'SYNC0':0x8E,
        'FSCAL1':0x00,
        'FSCAL0':0x1F,
        'TEST0':0x09
        }

    def __init__(self,num):
        self.obj=spidev.SpiDev()
        self.obj.open(num,0)
        self.GDO0State=False
        #time.sleep(0.01)
        self.state='IDLE'
        self.config=0
        #self.Reset()
        if num==0:
            self.GDO0Pin=153
        if num==1:
            self.GDO0Pin=161

    def Close(self):
        self.Reset()
        self.obj.close()

    def ReadStatus(self,addr):
        attempts=0
        while attempts < 3:
            try:
                r=map(hex,self.obj.xfer2([self.REGISTER[addr] | self.READ_BURST,0]))
                break
            except IOError:
                self.ReturnState()
                attempts+=1
        if attempts==3:
            raise IOError('ReadStatus input/output error')
        return r

    def Strobe(self,addr):
        attempts=0
        while attempts < 3:
            try:
                r=map(hex,self.obj.xfer2([self.REGISTER[addr]]))
                break
            except IOError:
                time.sleep(0.5)
                attempts+=1
        if attempts==3:
            raise IOError('Strobe input/output error')
        return r

    def ReadReg(self,addr):
        attempts=0
        while attempts < 3:
            try:
                r=map(hex,self.obj.xfer2([self.REGISTER[addr] | self.READ_SINGLE,0]))
                break
            except IOError:
                self.ReturnState()
                attempts+=1
        if attempts==3:
           raise IOError('ReadReg input/output error')
        return r

    def ReadBurstReg(self,addr,count):
        buffer=[self.REGISTER[addr] | self.READ_BURST]
        for i in range(count):
            buffer.append(0)
        attempts=0
        while attempts < 3:
            try:
                r=map(hex,self.obj.xfer2(buffer))
                break
            except IOError:
                self.ReturnState()
                attempts+=1
        if attempts==3:
            raise IOError('ReadBurstReg input/output error')
        return r

    def WriteReg(self,addr,val):
        attempts=0
        while attempts < 3:
            try:
                r=map(hex,self.obj.xfer2([self.REGISTER[addr],val]))
                break
            except IOError:
                self.ReturnState()
                attempts+=1
        if attempts==3:
            raise IOError('WriteReg input/output error')
        return r

    def WriteBurstReg(self,addr,buffer):
        buffer.insert(0,self.REGISTER[addr] | self.WRITE_BURST)
        attempts=0
        while attempts < 3:
            try:
                r=map(hex,self.obj.xfer2(buffer))
                break
            except IOError:
                self.ReturnState()
                attempts+=1
        if attempts==3:
            raise IOError('WriteBurstReg input/output error')
        del buffer[0]
        return r

    def WriteSettings(self,num):
        buffer=[]
        self.config=num
        if num==0:
            list=self.RF_SETTINGS
        if num==1:
            list=self.RF_SETTINGS1
            self.WriteBurstReg('PATABLE',[0,0x1d,0,0,0,0,0,0])
        if num==2:
            list=self.RF_SETTINGS2
            self.WriteBurstReg('PATABLE',[0,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d])
        if num==3:
            list=self.RF_SETTINGS3
            self.WriteBurstReg('PATABLE',[0,0xC0,0xC0,0xC0,0xC0,0xC0,0xC0,0xC0])
            #self.WriteBurstReg('PATABLE',[0,0x8F,0x8E,0x8D,0x8C,0x8B,0x8A,0x89])
        if num==4:
            list=self.RF_SETTINGS4
            #self.WriteBurstReg('PATABLE',[0,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d])
            #self.WriteBurstReg('PATABLE',[0,0x8F,0x8C,0x8A,0x88,0x86,0x85,0x84])
            #self.WriteBurstReg('PATABLE',[0,0x8F,0x8A,0x87,0x84,0x82,0x80,0x78])
            self.WriteBurstReg('PATABLE',[0,0xC0,0xC0,0xC0,0xC0,0xC0,0xC0,0xC0])
        if num==5:
            list=self.RF_SETTINGS5
            self.WriteBurstReg('PATABLE',[0,0xC0,0xC0,0xC0,0xC0,0xC0,0xC0,0xC0])
            #self.WriteBurstReg('PATABLE',[0,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d])
        for key in list.keys():
            buffer.append(key)
            self.WriteReg(key,list[key])
            time.sleep(0.001)
            buffer.append(self.ReadReg(key)[1])
            time.sleep(0.001)
        return buffer

    def Reset(self):
        if self.GDO0State:
            self.GDO0Close()
        self.config=0
        r=self.Strobe('SRES')
        time.sleep(0.01)
        self.state=self.Marcstate()
        return r

    def GDO0Open(self):
        p=self.GDO0Pin
        fagpio.export(p)
        p_obj=fagpio.gpio(p)
        p_obj.edge='rising'
        self.epoll_obj=select.epoll()
        self.GDO0File=p_obj.fileobj
        self.epoll_obj.register(self.GDO0File, select.EPOLLET)
        self.GDO0State=True
        self.epoll_obj.poll(0.01)

    def GDO0Close(self):
        self.epoll_obj.close()
        fagpio.unexport(self.GDO0Pin)
        self.GDO0State=False

    def Freq(self,x):
        if (x>300 and x<348) or (x>387 and x<464) or (x>779 and x<928):
            hex_freq=hex(math.trunc((x*math.pow(2,16))/26))
            if len(hex_freq)==7:
                freq2=int('0x'+hex_freq[2],16)
                freq1=int('0x'+hex_freq[3:5],16)
                freq0=int('0x'+hex_freq[5:7],16)
            elif len(hex_freq)==8:
                freq2=int('0x'+hex_freq[2:4],16)
                freq1=int('0x'+hex_freq[4:6],16)
                freq0=int('0x'+hex_freq[6:8],16)
            else:
                raise Exception("The frequency should be whithin the following ranges: 300-348, 387-464, 779-928")
        return self.WriteBurstReg('FREQ2',[freq2,freq1,freq0])

    def DataRate(self,rate):
        drate_e=math.trunc(math.log((((rate/1000.0)*math.pow(2,20))/26),2))
        drate_m=math.trunc((((rate/1000.0)*math.pow(2,28))/(26*math.pow(2,drate_e)))-256)
        m4=int(self.ReadReg('MDMCFG4')[1][:3]+str(hex(drate_e)[2:]),16)
        m3=drate_m
        return self.WriteBurstReg('MDMCFG4',[m4,m3])

    def Init(self,num):
        self.Reset()
        time.sleep(0.01)
        return self.WriteSettings(num)

    def Marcstate(self):
        return self.Marcstate_reg[self.ReadStatus('MARCSTATE')[1]]

    def Stx(self):
        self.Strobe('STX')
        time.sleep(0.01)
        marcstate=self.ReadStatus('MARCSTATE')[1]
        if marcstate=='0x13':
            self.state='TX'
        else:
            print self.Marcstate_reg[marcstate]+' from Stx'
            self.FlushTX()
            self.Stx()

    def Srx(self):
        self.Strobe('SRX')
        time.sleep(0.01)
        marcstate=self.ReadStatus('MARCSTATE')[1]
        if marcstate=='0xd':
            self.state='RX'
        else:
            print self.Marcstate_reg[marcstate]+' from Srx'
            self.FlushRX()
            self.Srx()

    def Sidle(self):
        self.Strobe('SIDLE')
        time.sleep(0.5)
        marcstate=self.ReadStatus('MARCSTATE')[1]
        if marcstate=='0x1':
            self.state='IDLE'
        else:
            print self.Marcstate_reg[marcstate]+' from Sidle'
            self.Sidle()

    def ReturnState(self):
        st=self.state
        time.sleep(0.01)
        self.Sidle()
        if st=='RX':
            self.Srx()
        elif st=='TX':
            self.Stx()

    def FlushRX(self):
        self.Sidle()
        self.Strobe('SFRX')
        self.state='IDLE'

    def FlushTX(self):
        self.Sidle()
        self.Strobe('SFTX')
        self.state='IDLE'

    def Send(self,buffer):
        self.WriteBurstReg('TXFIFO',buffer)
        self.Stx()

    def Send2(self,buffer):
        cur=64
        len_buffer=len(buffer)
        threshold=(len_buffer-(len_buffer % 64))
        self.FlushTX()
        self.WriteBurstReg('TXFIFO',buffer[0:64])
        self.Stx()
        flag=True
        while cur<len_buffer:
            if cur>threshold and flag:
                self.WriteReg('PKTCTRL0',0x00)
                print "Turn to fixed packet length with threshold is %s" % threshold
                flag=False
            time.sleep(0.012)
            sum=64-int(self.ReadStatus('TXBYTES')[1],16)
            print sum,cur
            if sum>0:
                if (cur+sum)<len_buffer:
                    self.WriteBurstReg('TXFIFO',buffer[cur:cur+sum])
                else:
                    self.WriteBurstReg('TXFIFO',buffer[cur:len_buffer+1])
                    print len_buffer-cur,len_buffer
                    #print self.ReadStatus('MARCSTATE')
                    self.Sidle()
                    #print self.ReadStatus('MARCSTATE')
                    break
            else:
                self.FlushTX()
                self.Stx()
                sum=0
            cur+=sum
        self.WriteReg('PKTCTRL0',0x02)

    def ButtonB(self):
        self.CheckSettings(3)
        len_pack=255
        self.WriteReg('PKTLEN',len_pack)
        packet=[0x80,0x00,0x00,0x00,0xEE,0xEE,0xEE,0x8E,0x88,0x8E,0x8E,0x88,0x88,0x88,0xEE,0x88]
        big_packet=self.inc_packet(packet,len_pack)
        self.Send2(big_packet)

    def ButtonA(self):
        self.CheckSettings(3)
        len_pack=255
        self.WriteReg('PKTLEN',len_pack)
        packet=[0x80,0x00,0x00,0x00,0xEE,0xEE,0xEE,0x8E,0x88,0x8E,0x8E,0x88,0x88,0x88,0x88,0xEE]
        big_packet=self.inc_packet(packet,len_pack)
        self.Send2(big_packet)

    def ButtonC(self):
        self.CheckSettings(3)
        len_pack=255
        self.WriteReg('PKTLEN',len_pack)
        packet=[0x80,0x00,0x00,0x00,0xEE,0xEE,0xEE,0x8E,0x88,0x8E,0x8E,0x88,0x88,0xEE,0x88,0x88]
        big_packet=self.inc_packet(packet,len_pack)
        self.Send2(big_packet)

    def LevoloPreSend(self):
        self.WriteReg('MDMCFG2',0x30) #ASK, No preamble/sync
        self.WriteReg('PKTCTRL0',0x02) #Normal mode, infinite packet

    def inc_packet(self,pack,size):
        new_packet=[]
        cur=0
        while len(new_packet)<size:
            if cur>(len(pack)-1):
                cur=0
            new_packet.append(pack[cur])
            cur=cur+1
        return new_packet

    def CheckSettings(self,num):
        if self.config!=num:
            self.WriteSettings(num)

    def LevoloA2(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x6a, 0x95, 0x75, 0x55, 0x53, 0x33,
        0x35, 0x4a, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0xa5, 0xa5, 0x66,
        0x6a, 0x95, 0x75, 0x55, 0x53, 0x33, 0x35, 0x4a, 0xba, 0xaa,
        0xa9, 0x99, 0x9a, 0xa5, 0x5d, 0x55, 0x54, 0xcc, 0xcd, 0x52,
        0xae, 0xaa, 0xaa, 0x66, 0x66, 0xa9, 0x57, 0x55, 0x55, 0x33,
        0x33, 0x54, 0xab, 0xaa, 0xaa, 0x99, 0x99, 0xaa, 0x55, 0xd5,
        0x55, 0x4c, 0xcc, 0xd5, 0x2a]
        big_packet=self.inc_packet(packet,1100)
        self.Send2(big_packet)

    def LevoloA(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x6a, 0x95, 0x75, 0x55, 0x53, 0x33,
        0x35, 0x4a, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0xa5, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x52, 0xae, 0xaa, 0xaa, 0x66, 0x66, 0xa9,
        0x57, 0x55, 0x55, 0x33, 0x33, 0x54, 0xab, 0xaa, 0xaa, 0x99,
        0x99, 0xaa, 0x55, 0xd5, 0x55, 0x4c, 0xcc, 0xd5, 0x2a]
        big_packet=self.inc_packet(packet,1000)
        self.Send2(big_packet)

    def LevoloB2(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x6a, 0x55, 0x75, 0x55, 0x53, 0x33,
        0x35, 0x2a, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0x95, 0x95, 0x66,
        0x6a, 0x55, 0x75, 0x55, 0x53, 0x33, 0x35, 0x2a, 0xba, 0xaa,
        0xa9, 0x99, 0x9a, 0x95, 0x5d, 0x55, 0x54, 0xcc, 0xcd, 0x4a,
        0xae, 0xaa, 0xaa, 0x66, 0x66, 0xa5, 0x57, 0x55, 0x55, 0x33,
        0x33, 0x52, 0xab, 0xaa, 0xaa, 0x99, 0x99, 0xa9, 0x55, 0xd5,
        0x55, 0x4c, 0xcc, 0xd4, 0xaa]
        big_packet=self.inc_packet(packet,1100)
        self.Send2(big_packet)

    def LevoloB(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x6a, 0x55, 0x75, 0x55, 0x53, 0x33,
        0x35, 0x2a, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0x95, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x4a, 0xae, 0xaa, 0xaa, 0x66, 0x66, 0xa5,
        0x57, 0x55, 0x55, 0x33, 0x33, 0x52, 0xab, 0xaa, 0xaa, 0x99,
        0x99, 0xa9, 0x55, 0xd5, 0x55, 0x4c, 0xcc, 0xd4, 0xaa]
        big_packet=self.inc_packet(packet,1000)
        self.Send2(big_packet)

    def LevoloC2(self):
        self.CheckSettings(4)
        packet=[0xea,0xaa,0xa6,0x66,0x69,0x95,0x75,0x55,0x53,0x33,
        0x34,0xca,0xba,0xaa,0xa9,0x99,0x9a,0x65,0x5d,0x55,
        0x54,0xcc,0xcd,0x32,0xae,0xaa,0xaa,0x66,0x66,0x99,
        0x57,0x55,0x55,0x33,0x33,0x4c,0xab,0xaa,0xaa,0x99,
        0x99,0xa6,0x55,0xd5,0x55,0x4c,0xcc,0xd3,0x2a,0xea,
        0xaa,0xa6,0x66,0x69,0x95,0x75,0x55,0x53,0x33,0x34,
        0xca,0xba,0xaa,0xa9]
        big_packet=self.inc_packet(packet,1100)
        self.Send2(big_packet)

    def LevoloC(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x69, 0x95, 0x75, 0x55, 0x53, 0x33,
        0x34, 0xca, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0x65, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x32, 0xae, 0xaa, 0xaa, 0x66, 0x66, 0x99,
        0x57, 0x55, 0x55, 0x33, 0x33, 0x4c, 0xab, 0xaa, 0xaa, 0x99,
        0x99, 0xa6, 0x55, 0xd5, 0x55, 0x4c, 0xcc, 0xd3, 0x2a]
        big_packet=self.inc_packet(packet,784)
        self.Send2(big_packet)

    def LevoloD2(self):
        self.CheckSettings(4)
        packet=[0xea,0xaa,0xa6,0x66,0x69,0x69,0x75,0x55,0x53,0x33,
        0x34,0xb4,0xba,0xaa,0xa9,0x99,0x9a,0x5a,0x5d,0x55,
        0x54,0xcc,0xcd,0x2d,0x2e,0xaa,0xaa,0x66,0x66,0x96,
        0x97,0x55,0x55,0x33,0x33,0x4b,0x4b,0xaa,0xaa,0x99,
        0x99,0xa5,0xa5,0xd5,0x55,0x4c,0xcc,0xd2,0xd2,0xea,
        0xaa,0xa6,0x66,0x69,0x69,0x75,0x55,0x53,0x33,0x34,
        0xb4,0xba,0xaa,0xa9,0x99]
        big_packet=self.inc_packet(packet,1100)
        self.Send2(big_packet)

    def LevoloD(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x69, 0x69, 0x75, 0x55, 0x53, 0x33,
        0x34, 0xb4, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0x5a, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x2d, 0x2e, 0xaa, 0xaa, 0x66, 0x66, 0x96,
        0x97, 0x55, 0x55, 0x33, 0x33, 0x4b, 0x4b, 0xaa, 0xaa, 0x99,
        0x99, 0xa5, 0xa5, 0xd5, 0x55, 0x4c, 0xcc, 0xd2, 0xd2]
        big_packet=self.inc_packet(packet,784)
        self.Send2(big_packet)

    def Receive(self,packet_len):
        def levolo_but(b):
            buttons={'10100101':'LevoloA','10010101':'LevoloB','01100101':'LevoloC','01011010':'LevoloD'}
            a=human_bin(b).replace('11111111','') # убрать шумы если куча FF, мешает определению клавиши
            a=a.split('111')[1:]
            if a:
                dpack=dict([[x,a.count(x)] for x in set(a)])
                # сортировать по кол-ву повторов сообщения
                sorted_dpack=sorted(dpack.iteritems(), key=operator.itemgetter(1))
                # вернуть сообщение ктр чаще повторилось [35:43] - нажатая кнопка
                but=sorted_dpack[len(sorted_dpack)-1][0][35:43]
                if buttons.setdefault(but) is not None:
                    but=buttons.setdefault(but)
                return but
            else:
                return 'Bad packet'

        def TriStateCode(b):
            buttons={'10001000':'0','11101110':'1','10001110':'f'}
            a=human_bin(b).replace('11111111','')
            a=a.split('10000000000000000000000000000000')[1:]
            if a:
                dpack=dict([[x,a.count(x)] for x in set(a)])
                # сортировать по кол-ву повторов сообщения
                sorted_dpack=sorted(dpack.iteritems(), key=operator.itemgetter(1))
                # вернуть сообщение ктр чаще повторилось
                buffer=sorted_dpack[len(sorted_dpack)-1][0]
                word=''
                len_buf=len(buffer)
                if len_buf%8==0:
                    for i in range(0,len_buf/8):
                        but=buffer[i*8:i*8+8]
                        if buttons.setdefault(but) is not None:
                            word=word+buttons.setdefault(but)
                        else:
                            word=word+'?'
                return word
            else:
                return 'Bad packet'

        def human_bin(buf):
            a=''
            b=[]
            for x in buf:
                b.append(x)
            for i in range(0,len(b)):
                b[i]=bin(int(b[i],16))
                b[i]=b[i][2:]
                b[i]=(8-len(b[i]))*'0'+b[i]
                a=a+b[i]
            return a

        if not self.GDO0State:
            self.GDO0Open()

        def run():
            buffer=[]
            self.FlushRX()
            self.Srx()
            flag=True
            sum_bytes=0
            print 'start...'
            events=self.epoll_obj.poll()
            print('RSSI: '+self.ReadStatus('RSSI')[1])
            while True:
                bytes=int(self.ReadStatus('RXBYTES')[1],16)
                if sum_bytes+bytes>=packet_len:
                    kol=packet_len-len(buffer)
                    buffer+=self.ReadBurstReg('RXFIFO',kol)[1:]
                    print buffer
                    #print len(buffer)
                    #print levolo_but(buffer)
                    return TriStateCode(buffer)
                    #print time.ctime()
                    #return levolo_but(buffer)
                    break
                else:
                    buffer+=self.ReadBurstReg('RXFIFO',bytes)[1:]
                    sum_bytes+=bytes
                time.sleep(0.015)
        try:
            rez=run()
            self.FlushRX()
            return rez
        except KeyboardInterrupt:
            self.GDO0Close()
            #epoll.unregister(f)
            #fagpio.unexport(p)
            #self.GDO0state='close'

CommandList = ['LevoloA',
'LevoloB',
'LevoloC',
'LevoloD',
'Marcstate']

if __name__ == "__main__":
    a=cc1101(1)
    a.Init(3)
    a.ButtonA()
    #a.Init(4)
    #a.LevoloPreSend()
    #a.LevoloB2()
    #a.Receive()

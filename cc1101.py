#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals
import spidev
import time
import operator
import fagpio
import select
import math
import re

class cc1101:
    #------------------------------------------------------------------------------------------------------
    # Settings
    scan_timeout=8 # for scan_datarate(), scan_freq()
    spi0_gdo0=153 # eint9 gpn9
    spi1_gdo0=155 # eint11 gpn11
    packet_len=1500 # for Receive()
    command_list = ['LevoloA',
        'LevoloB',
        'LevoloC',
        'LevoloD',
        'LevoloE',
        'ButtonA',
        'ButtonC',
        'Marcstate',
        ]
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

    #------------------------------------------------------------------------------------------------------
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

    #------------------------------------------------------------------------------------------------------
    RF_SETTINGS = [
        # 0
        {
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
        },

        # 1 
        {
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
        },
        # 2 
        #Asynch with rx on GDO0
        {
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
        },
        # 3
        # Simple naked packet for Asynch
        {
        'IOCFG0':0x06,
        'PKTCTRL1':0x00,
        'PKTCTRL0':0x00,    #fixed length
        'PKTLEN':0xFF,      # 0x40
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
        },
        # 4
        # Levolo
        {
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
        },
        # 5
        # motion sensor (tristatecode)
        {
        'IOCFG0':0x06,
        'PKTCTRL1':0x00,
        'PKTCTRL0':0x02,    #fixed length
        'PKTLEN':0xFF,
        'FSCTRL1':0x0C,
        'FREQ2':0x10,   # 433.6
        'FREQ1':0xAD,
        'FREQ0':0x4A,
        'MDMCFG4':0x26,    #BW 541 0x27 0xA3 Datarate 5.19466 key 1.5 
        'MDMCFG3':0x23,    #0x26 0x23 datarate 1.810 key 4.7
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
        },
        # 6
        # water sensor (tristatecode)
        {
        'IOCFG0':0x06,
        'PKTCTRL1':0x00,
        'PKTCTRL0':0x02,    #fixed length
        'PKTLEN':0xFF,
        'FSCTRL1':0x0C,
        'FREQ2':0x10,   # 433.92
        'FREQ1':0xB0,
        'FREQ0':0x71,
        'MDMCFG4':0x26,    #BW 541 0x27 0xe8 Datarate 6.060 key 1.5M
        'MDMCFG3':0x30,    #mdmcfg4: 0x26 mdmcfg3 0xb1 datarate 2.690 key 3.3M
        'MDMCFG2':0x32,    #0x26 0x30 datarate 1.890 key 4.7M
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
        },
        # 7
        # temperature sensor
        {
        'IOCFG0':0x06,
        'PKTCTRL1':0x00,
        'PKTCTRL0':0x02,    #fixed length
        'PKTLEN':0xFF,
        'FSCTRL1':0x0C,
        'FREQ2':0x10,   # 433.92
        'FREQ1':0xB0,
        'FREQ0':0x71,
        'MDMCFG4':0x26,    #BW 541 Data rate 2.250
        'MDMCFG3':0x6B,
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
        'SYNC1':0x01,
        'SYNC0':0x84,
        'FSCAL1':0x00,
        'FSCAL0':0x1F,
        'TEST0':0x09,
        #'MDMCFG4':0x29,    #BW 541 Data rate 2.250
        #'MDMCFG3':0x6A,
        #'SYNC1':0x00,
        #'SYNC0':0xFF,
        }
    ]

    def __init__(self,num):
        self.obj=spidev.SpiDev()
        self.obj.open(num,0)
        if num==0:
            self.GDO0Pin=self.spi0_gdo0
        if num==1:
            self.GDO0Pin=self.spi1_gdo0
        fagpio.unexport(self.GDO0Pin)
        self.GDO0State=False
        self.Reset()

    def Reset(self):
        if self.GDO0State:
            self.GDO0Close()
        self.config=0
        r=self.Strobe('SRES')
        while (self.Marcstate()!='IDLE'):
            pass;
        self.state='IDLE'
        return r

    def Close(self):
        self.Reset()
        self.obj.close()

    def ReadStatus(self,addr):
        attempts=0
        while attempts < 3:
            try:
                r=list(map(hex,self.obj.xfer2([self.REGISTER[addr] | self.READ_BURST,0])))
                break
            except IOError:
                self.Strobe('SNOP')
                attempts+=1
        if attempts==3:
            raise IOError('ReadStatus input/output error')
        return r

    def Strobe(self,addr):
        attempts=0
        while attempts < 3:
            try:
                r=list(map(hex,self.obj.xfer2([self.REGISTER[addr]])))
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
                r=list(map(hex,self.obj.xfer2([self.REGISTER[addr] | self.READ_SINGLE,0])))
                break
            except IOError:
                self.Strobe('SNOP')
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
                r=list(map(hex,self.obj.xfer2(buffer)))
                break
            except IOError:
                self.Strobe('SNOP')
                attempts+=1
        if attempts==3:
            raise IOError('ReadBurstReg input/output error')
        return r

    def WriteReg(self,addr,val):
        attempts=0
        while attempts < 3:
            try:
                r=list(map(hex,self.obj.xfer2([self.REGISTER[addr],val])))
                break
            except IOError:
                self.Strobe('SNOP')
                attempts+=1
        if attempts==3:
            raise IOError('WriteReg input/output error')
        return r

    def WriteBurstReg(self,addr,buffer):
        buffer.insert(0,self.REGISTER[addr] | self.WRITE_BURST)
        attempts=0
        while attempts < 3:
            try:
                r=list(map(hex,self.obj.xfer2(buffer)))
                break
            except IOError:
                self.Strobe('SNOP')
                attempts+=1
        if attempts==3:
            raise IOError('WriteBurstReg input/output error')
        del buffer[0]
        return r

    def WriteSettings(self,num):
        buffer=[]
        self.config=num
        #self.WriteBurstReg('PATABLE',[0,0x1d,0,0,0,0,0,0]) #setting 1
        #self.WriteBurstReg('PATABLE',[0,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d,0x1d]) #setting 2
        list=self.RF_SETTINGS[num]
        self.WriteBurstReg('PATABLE',[0,0xC0,0xC0,0xC0,0xC0,0xC0,0xC0,0xC0])
        for key in list.keys():
            buffer.append(key)
            self.WriteReg(key,list[key])
            time.sleep(0.001)
            buffer.append(self.ReadReg(key)[1])
            time.sleep(0.001)
        return buffer

    def PrintSettings(self):
        buffer=[]
        print('settings number is: '+str(self.config))
        sort_register=sorted(self.REGISTER.items(), key=operator.itemgetter(1))
        for i in sort_register:
            buffer.append(i[0])
            buffer.append(self.ReadReg(i[0])[1])
            if i[1]==46:
                break
        return buffer

    def GDO0Open(self):
        p=self.GDO0Pin
        fagpio.export(p)
        p_obj=fagpio.gpio(p)
        p_obj.active=0
        p_obj.direction='in'
        p_obj.edge='rising'
        self.GDO0File=p_obj.fvalue
        self.epoll_obj=p_obj.epoll_obj
        self.GDO0State=True

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
        return self.WriteSettings(num)

    def Marcstate(self):
        return self.Marcstate_reg[self.ReadStatus('MARCSTATE')[1]]

    def Stx(self):
        self.Strobe('STX')
        while (self.Marcstate()!='TX'):
            pass
        self.state='TX'

    def Srx(self):
        self.Strobe('SRX')
        while (self.Marcstate()!='RX'):
            pass
        self.state='RX'

    def Sidle(self):
        self.Strobe('SIDLE')
        while (self.Marcstate()!='IDLE'):
            pass
        self.state='IDLE'

    def FlushRX(self):
        self.Sidle()
        self.Strobe('SFRX')

    def FlushTX(self):
        self.Sidle()
        self.Strobe('SFTX')

    def Send(self,buffer):
        self.WriteBurstReg('TXFIFO',buffer)
        self.Stx()

    def Send2(self,buffer):
        try:
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
                    print("Turn to fixed packet length with threshold is %s" % threshold)
                    flag=False
                time.sleep(0.012)
                sum=64-int(self.ReadStatus('TXBYTES')[1],16)
                print(sum,cur)
                if sum>0:
                    if (cur+sum)<len_buffer:
                        self.WriteBurstReg('TXFIFO',buffer[cur:cur+sum])
                    else:
                        self.WriteBurstReg('TXFIFO',buffer[cur:len_buffer+1])
                        print(len_buffer-cur,len_buffer)
                        #print(self.ReadStatus('MARCSTATE'))
                        self.Sidle()
                        #print(self.ReadStatus('MARCSTATE'))
                        break
                else:
                    self.FlushTX()
                    self.Stx()
                    sum=0
                cur+=sum
            self.WriteReg('PKTCTRL0',0x02)
            return True
        except Exception, e:
            print(str(e))
            return False

    def ButtonB(self):
        self.CheckSettings(3)
        len_pack=255
        self.WriteReg('PKTLEN',len_pack)
        packet=[0x80,0x00,0x00,0x00,0xEE,0xEE,0xEE,0x8E,0x88,0x8E,0x8E,0x88,0x88,0x88,0xEE,0x88]
        big_packet=self.IncPacket(packet,len_pack)
        return self.Send2(big_packet)

    def ButtonA(self):
        self.CheckSettings(3)
        len_pack=255
        self.WriteReg('PKTLEN',len_pack)
        packet=[0x80,0x00,0x00,0x00,0xEE,0xEE,0xEE,0x8E,0x88,0x8E,0x8E,0x88,0x88,0x88,0x88,0xEE]
        big_packet=self.IncPacket(packet,len_pack)
        return self.Send2(big_packet)

    def ButtonC(self):
        self.CheckSettings(3)
        len_pack=255
        self.WriteReg('PKTLEN',len_pack)
        packet=[0x80,0x00,0x00,0x00,0xEE,0xEE,0xEE,0x8E,0x88,0x8E,0x8E,0x88,0x88,0xEE,0x88,0x88]
        big_packet=self.IncPacket(packet,len_pack)
        return self.Send2(big_packet)

    def IncPacket(self,pack,size):
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

    def LevoloA(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x6a, 0x95, 0x75, 0x55, 0x53, 0x33,
        0x35, 0x4a, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0xa5, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x52, 0xae, 0xaa, 0xaa, 0x66, 0x66, 0xa9,
        0x57, 0x55, 0x55, 0x33, 0x33, 0x54, 0xab, 0xaa, 0xaa, 0x99,
        0x99, 0xaa, 0x55, 0xd5, 0x55, 0x4c, 0xcc, 0xd5, 0x2a]
        big_packet=self.IncPacket(packet,1000)
        return self.Send2(big_packet)

    def LevoloB(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x6a, 0x55, 0x75, 0x55, 0x53, 0x33,
        0x35, 0x2a, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0x95, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x4a, 0xae, 0xaa, 0xaa, 0x66, 0x66, 0xa5,
        0x57, 0x55, 0x55, 0x33, 0x33, 0x52, 0xab, 0xaa, 0xaa, 0x99,
        0x99, 0xa9, 0x55, 0xd5, 0x55, 0x4c, 0xcc, 0xd4, 0xaa]
        big_packet=self.IncPacket(packet,1000)
        return self.Send2(big_packet)

    def LevoloC(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x69, 0x95, 0x75, 0x55, 0x53, 0x33,
        0x34, 0xca, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0x65, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x32, 0xae, 0xaa, 0xaa, 0x66, 0x66, 0x99,
        0x57, 0x55, 0x55, 0x33, 0x33, 0x4c, 0xab, 0xaa, 0xaa, 0x99,
        0x99, 0xa6, 0x55, 0xd5, 0x55, 0x4c, 0xcc, 0xd3, 0x2a]
        big_packet=self.IncPacket(packet,1000)
        return self.Send2(big_packet)

    def LevoloD(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x69, 0x69, 0x75, 0x55, 0x53, 0x33,
        0x34, 0xb4, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0x5a, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x2d, 0x2e, 0xaa, 0xaa, 0x66, 0x66, 0x96,
        0x97, 0x55, 0x55, 0x33, 0x33, 0x4b, 0x4b, 0xaa, 0xaa, 0x99,
        0x99, 0xa5, 0xa5, 0xd5, 0x55, 0x4c, 0xcc, 0xd2, 0xd2]
        big_packet=self.IncPacket(packet,1000)
        return self.Send2(big_packet)

    def LevoloE(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x6b, 0x55, 0x75, 0x55, 0x53, 0x33,
        0x35, 0xaa, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0xd5, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x6a, 0xae, 0xaa, 0xaa, 0x66, 0x66, 0xb5,
        0x57, 0x55, 0x55, 0x33, 0x33, 0x5a, 0xab, 0xaa, 0xaa, 0x99,
        0x99, 0xad, 0x55, 0xd5, 0x55, 0x4c, 0xcc, 0xd6, 0xaa]
        big_packet=self.IncPacket(packet,1000)
        return self.Send2(big_packet)

    def LevoloH(self):
        self.CheckSettings(4)
        packet=[0xea, 0xaa, 0xa6, 0x66, 0x6a, 0xd5, 0x75, 0x55, 0x53, 0x33,
        0x35, 0x6a, 0xba, 0xaa, 0xa9, 0x99, 0x9a, 0xb5, 0x5d, 0x55,
        0x54, 0xcc, 0xcd, 0x5a, 0xae, 0xaa, 0xaa, 0x66, 0x66, 0xad,
        0x57, 0x55, 0x55, 0x33, 0x33, 0x56, 0xab, 0xaa, 0xaa, 0x99,
        0x99, 0xab, 0x55, 0xd5, 0x55, 0x4c, 0xcc, 0xd5, 0xaa]
        big_packet=self.IncPacket(packet,1000)
        return self.Send2(big_packet)

    def LevoloButton(self,b):
        buttons={'10100101':'LevoloA','10010101':'LevoloB','01100101':'LevoloC','01011010':'LevoloD'}
        a=self.HumanBin(b).replace('11111111','') # убрать шумы если куча FF, мешает определению клавиши
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
            return 0

    def TriStateCode(self,b):
        buttons={'10001000':'0','11101110':'1','10001110':'f'}
        a=self.HumanBin(b).replace('11111111','')
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
            return 0

    class temperature:
        def __init__(self):
            self.t=0
            self.h=0

    def TempDecode(self,b):
        p=re.compile('1+')
        ps=re.compile('10{20,22}')
        p1=re.compile('10{4,6}')
        p0=re.compile('10{8,10}')
        a=p1.sub('one',p0.sub('null',ps.sub('s',p.sub('1',self.HumanBin(b))))).replace('null','0').replace('one','1').split('s')
        temp=self.temperature()
        if a:
            dpack=dict([[x,a.count(x)] for x in set(a)])
            # сортировать по кол-ву повторов сообщения
            sorted_dpack=sorted(dpack.iteritems(), key=operator.itemgetter(1))
            # вернуть сообщение ктр чаще повторилось
            buffer=sorted_dpack[len(sorted_dpack)-1][0][4:]
            len_buf=len(buffer)
            rez=[]
            for i in range(0,len_buf/8):
                b=buffer[i*8:i*8+8]
                rez.append(int(b,2))
            if len(rez)==4:
                if rez[1]==112:
                    temp.t=(0-rez[2])/10.0
                elif rez[1]==127:
                    temp.t=(255-rez[2])/10.0
                elif rez[1]==126:
                    temp.t=(511-rez[2])/10.0
                else:
                    temp.t=(-255-rez[2])/10.0
                temp.h=255-rez[3]
                #print(rez)
            #return temp
            return str(temp.t)+':'+str(temp.h)
        else:
            return 0

    # mapping settings and functions for receive
    recv_func_dict={
        4: LevoloButton,
        5: TriStateCode,
        6: TriStateCode,
        7: TempDecode,
        }

    def HumanBin(self,buf):
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

    # Соответствие номеру конфигурации и функции обработки сообщения
    def BufferConvert(self,x):
        recv_func_dict={
            4: self.LevoloButton,
            5: self.TriStateCode,
            6: self.TriStateCode,
            7: self.TempDecode,
            }
        return recv_func_dict.get(x, self.TriStateCode)

    def RssiDbm(self,x):
        rssi_offset=74
        if x>=128:
            rssi=(x-256)/2-rssi_offset
        else:
            rssi=(x/2)-rssi_offset
        return rssi

    def ScanDataRate(self,start,end,step):
        dr=start
        while dr<end:
            self.DataRate(dr)
            print(str(dr))
            dr+=step
            time.sleep(self.scan_timeout)

    def ScanFreq(self,start,end,step):
        freq=start
        while freq<end:
            self.Freq(freq)
            print(str(freq))
            freq+=step
            time.sleep(self.scan_timeout)

    def ReadBuffer(self):
        buffer=[]
        sum_bytes=0
        while True:
            bytes=int(self.ReadStatus('RXBYTES')[1],16)
            #Читать кол-во байт, пока не повторится. стр. 56
            while bytes!=int(self.ReadStatus('RXBYTES')[1],16):
                bytes=int(self.ReadStatus('RXBYTES')[1],16)
            if sum_bytes+bytes>=self.packet_len:
                kol=self.packet_len-len(buffer)
                buffer+=self.ReadBurstReg('RXFIFO',kol)[1:]
                print(self.HumanBin(buffer))
                return self.BufferConvert(self.config)(buffer)
                break
            else:
            #bytes-1 потому что нельзя считывать последний байт 
            #до окончания всей передачи. стр 56
                part=self.ReadBurstReg('RXFIFO',bytes-1)[1:]
                #print(part)
                part_str=''
                for i in part:
                    part_str+=i
                if ('0xff0xff0xff' in part_str):
                    #print('ff')
                    print(self.HumanBin(buffer))
                    return self.BufferConvert(self.config)(buffer)
                    break
                buffer+=part
                sum_bytes+=bytes-1
                time.sleep(0.015)

    def Receive(self):
        if not self.GDO0State:
            self.GDO0Open()

        def run():
            self.FlushRX()
            self.Srx()
            print('start...')
            while True:
                events=self.epoll_obj.poll(1)
                #print(events,self.GDO0File.fileno())
                for fileno,event in events:
                    if fileno==self.GDO0File.fileno():
                        self.RSSI=self.ReadStatus('RSSI')[1]
                        #print(self.RSSI)
                        print('RSSI: '+str(self.RssiDbm(int(self.RSSI,0)))+' db')
                        return self.ReadBuffer()
                        break
        try:
            rez=run()
            self.FlushRX()
            return rez
        except KeyboardInterrupt:
            self.GDO0Close()

if __name__ == "__main__":
    a=cc1101(1)
    a.Init(3)
    a.ButtonA()
    #a.Init(4)
    #a.LevoloPreSend()
    #a.LevoloB2()
    #a.Receive()

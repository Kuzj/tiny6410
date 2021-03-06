#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals
import os
import re
import select
from subprocess import call

# eint0 gpn0 - eint5 gpn5 eint16 gpl8 - eint20 gpl12
# eint17 gpio130
# global var for gpiochip
clist = []
# global var for gpio
glist = []
gpiochip_path = "/sys/class/gpio/gpiochip"
gpio_path = "/sys/class/gpio/gpio"


class gpiochip:
    def __init__(self, num):
        num = str(num)
        self.error = False
        self.name = num
        if os.access(gpiochip_path + num, os.R_OK):
            fbase = open(gpiochip_path + num + '/base')
            self.base = fbase.read().rstrip()
            fbase.close()
            flabel = open(gpiochip_path + num + '/label')
            self.label = flabel.read().rstrip()
            flabel.close()
            fngpio = open(gpiochip_path + num + '/ngpio')
            self.ngpio = fngpio.read().rstrip()
            fngpio.close()
        else:
            print(num + ' is not exist')
            self.error = True


class gpio(object):
    def __init__(self, num):
        self.name = str(num)
        if not isexport(int(num)):  # not os.access(gpio_path+num, os.R_OK):
            print(self.name + ' is not export or do not exist')
        else:
            if os.access(gpio_path + self.name + '/value', os.W_OK):
                self.fvalue = open(gpio_path + self.name + '/value')
            if os.access(gpio_path + self.name + '/edge', os.W_OK):
                self.epoll_obj = select.epoll()
                self.epoll_obj.register(self.fvalue, select.EPOLLPRI | select.EPOLLET)

    def getactive(self):
        if os.access(gpio_path + self.name + '/active_low', os.R_OK):
            factive = open(gpio_path + self.name + '/active_low')
            self._active = int(factive.read().rstrip())
            factive.close()
            return self._active

    def setactive(self, val):
        if val in range(0, 2):
            val = str(val)
            if os.access(gpio_path + self.name + '/active_low', os.W_OK):
                factive = open(gpio_path + self.name + '/active_low', 'w+', 0)
                factive.write(val)
                factive.close()
                return True
            else:
                print('Access denied')
                return False
        else:
            print('Error: value must be 0 or 1')
            return False

    active = property(getactive, setactive)

    def getdirection(self):
        if os.access(gpio_path + self.name + '/direction', os.R_OK):
            fdir = open(gpio_path + self.name + '/direction')
            self._direction = fdir.read().rstrip()
            fdir.close()
            return self._direction

    def setdirection(self, val):
        if val in ['in', 'out']:
            if os.access(gpio_path + self.name + '/direction', os.W_OK):
                fdir = open(gpio_path + self.name + '/direction', 'w+', 0)
                fdir.write(val)
                fdir.close()
                try:
                    self.epoll_obj.unregister(self.fvalue)
                    self.fvalue.close()
                except:
                    pass
                if val == 'in' and os.access(gpio_path + self.name + '/value', os.W_OK):
                    self.fvalue = open(gpio_path + self.name + '/value')
                if val == 'out' and os.access(gpio_path + self.name + '/value', os.W_OK):
                    self.fvalue = open(gpio_path + self.name + '/value', 'w+', 0)
                if os.access(gpio_path + self.name + '/edge', os.W_OK) and val == 'in':
                    self.epoll_obj = select.epoll()
                    self.epoll_obj.register(self.fvalue, select.EPOLLPRI | select.EPOLLET)
                return True
            else:
                print('Access denied')
                return False
        else:
            print('Error value must be "in" or "out"')
            return False

    direction = property(getdirection, setdirection)

    def getvalue(self):
        self._value = int(self.fvalue.read(1))
        self.fvalue.seek(0)
        return self._value

    def setvalue(self, val):
        if self.direction == 'out' and self.fvalue.mode != 'w+':
            self.fvalue.close()
            self.fvalue = open(gpio_path + self.name + '/value', 'w+', 0)
        if val in range(0, 2):
            val = str(val)
            self.fvalue.write(val)
            self.fvalue.seek(0)
            return True
        else:
            print('Error: value must be 0 or 1')
            return False

    value = property(getvalue, setvalue)

    def getedge(self):
        if os.access(gpio_path + self.name + '/edge', os.R_OK):
            fedge = open(gpio_path + self.name + '/edge')
            self._edge = fedge.read().rstrip()
            fedge.close()
            return self._edge
        else:
            return ''

    def setedge(self, val):
        if val in ['none', 'rising', 'falling', 'both']:
            val = str(val)
            if os.access(gpio_path + self.name + '/edge', os.W_OK):
                fedge = open(gpio_path + self.name + '/edge', 'w+', 0)
                fedge.write(val)
                fedge.close()
                # Только после этого начинает ловить события
                self.epoll_obj.poll(0.01)
                return True
            else:
                print('Do not exist edge file in ' + self.name)
                return False
        else:
            print('Error: value must be -  none, rising, falling, both')
            return False

    edge = property(getedge, setedge)

    @property
    def fileobj(self):
        if os.access(gpio_path + self.name + '/value', os.W_OK):
            f = open(gpio_path + self.name + '/value', 'w+')
            return f


def export(num):
    if not isexport(num):
        call(["gpio-admin", "export", str(num)])


def unexport(num):
    if isexport(num):
        call(["gpio-admin", "unexport", str(num)])


def isexport(num):
    if (num in range(0, 203)) and (os.access(gpio_path + str(num), os.R_OK)):
        return True
    else:
        return False


def printlist():
    global glist
    global clist
    getlist()
    print(46 * '-')
    print('chip:      label:      ngpio:')
    for chip in clist:
        print(chip + (11 - len(chip)) * ' ' + gpiochip(chip).label + 9 * ' ' + gpiochip(chip).ngpio)
    print(46 * '-')
    print('gpio:   direction:   active:   value:   [edge]')
    for g in glist:
        print(g + (8 - len(g)) * ' ' + gpio(g).direction + (13 - len(gpio(g).direction)) * ' ' + str(
            gpio(g).active) + 9 * ' ' + str(gpio(g).value) + 9 * ' ' + gpio(g).edge)
    print(46 * '-')


def getlist():
    global clist
    global glist
    clist = []
    glist = []
    filelist = os.listdir(gpio_path[:15])
    for name in filelist:
        if name[:8] == 'gpiochip':
            chip_num = re.findall(r'\d+', name)[0]
            clist.append(chip_num)
        elif name[:4] == 'gpio':
            gpio_num = re.findall(r'\d+', name)[0]
            glist.append(gpio_num)


def initial():
    printlist()


def main():
    initial()


if __name__ == "__main__":
    main()

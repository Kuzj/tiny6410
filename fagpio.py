#!/usr/bin/python
import os
from subprocess import call
import re


#global var for gpiochip
clist=[]
#global var for gpio
glist=[]
gpiochip_path = "/sys/class/gpio/gpiochip"
gpio_path = "/sys/class/gpio/gpio"

class gpiochip:
    def __init__(self,num):
        num=str(num)
        self.error=False
        self.name=num
        if os.access(gpiochip_path+num, os.R_OK):
            fbase=open(gpiochip_path+num+'/base')
            self.base=fbase.read().rstrip()
            fbase.close()
            flabel=open(gpiochip_path+num+'/label')
            self.label=flabel.read().rstrip()
            flabel.close()
            fngpio=open(gpiochip_path+num+'/ngpio')
            self.ngpio=fngpio.read().rstrip()
            fngpio.close()
        else:
            print(num+' is not exist')
            self.error=True

class gpio(object):
    def __init__(self,num):
        num=str(num)
        self.name=num
        if not os.access(gpio_path+num, os.R_OK):
            print(num+' is not export or do not exist')
#            factive=open(gpio_path+num+'/active_low')
#            self._active=int(factive.read().rstrip())
#            factive.close()
#            fdir=open(gpio_path+num+'/direction')
#            self._direction=fdir.read().rstrip()
#            fdir.close()
        else:
            if os.access(gpio_path+num+'/value', os.W_OK):
                self.fvalue=open(gpio_path+num+'/value')
#            self._value=int(fvalue.read().rstrip())
#            fvalue.close()
#            if os.access(gpio_path+num+'/edge', os.R_OK):
#                fedge=open(gpio_path+num+'/edge')
#                self._edge=fedge.read().rstrip()
#                fedge.close()

    def getactive(self):
        if os.access(gpio_path+self.name+'/active_low', os.R_OK):
            factive=open(gpio_path+self.name+'/active_low')
            self._active=int(factive.read().rstrip())
            factive.close()
            return self._active

    def setactive(self,val):
        if val in range(0,2):
            val=str(val)
            if os.access(gpio_path+self.name+'/active_low', os.W_OK):
                factive=open(gpio_path+self.name+'/active_low','w+',0)
                factive.write(val)
                factive.close()
                return True
            else:
                print('Access denied')
                return False
        else:
            print('Error: value must be 0 or 1')
            return False

    active=property(getactive,setactive)

    def getdirection(self):
        if os.access(gpio_path+self.name+'/direction', os.R_OK):
            fdir=open(gpio_path+self.name+'/direction')
            self._direction=fdir.read().rstrip()
            fdir.close()
            return self._direction

    def setdirection(self,val):
        if val in ['in','out']:
            if os.access(gpio_path+self.name+'/direction', os.W_OK):
                fdir=open(gpio_path+self.name+'/direction','w+',0)
                fdir.write(val)
                fdir.close()
                try: 
                    self.fvalue.close()
                except:
                    pass
                if val=='in' and os.access(gpio_path+self.name+'/value', os.W_OK):
                    self.fvalue=open(gpio_path+self.name+'/value')
                if val=='out' and os.access(gpio_path+self.name+'/value', os.W_OK):
                    self.fvalue=open(gpio_path+self.name+'/value','w+',0)
                return True
            else:
                print('Access denied')
                return False
        else:
            print('Error value must be "in" or "out"')
            return False

    direction=property(getdirection,setdirection)

    def getvalue(self):
        #if os.access(gpio_path+self.name+'/value', os.R_OK):
        #    fvalue=open(gpio_path+self.name+'/value')
            self._value=int(self.fvalue.read(1))
            self.fvalue.seek(0)
        #    fvalue.close()
            return self._value

    def setvalue(self,val):
        if val in range(0,2):
            val=str(val)
            self.fvalue.write(val)
            self.fvalue.seek(0)
            return True
        else:
            print('Error: value must be 0 or 1')
            return False

    value=property(getvalue,setvalue)

    def getedge(self):
        if os.access(gpio_path+self.name+'/edge', os.R_OK):
            fedge=open(gpio_path+self.name+'/edge')
            self._edge=fedge.read().rstrip()
            fedge.close()
            return self._edge
        else:
            return ''

    def setedge(self,val):
        if val in ['none','rising','falling','both']:
            val=str(val)
            if os.access(gpio_path+self.name+'/edge', os.W_OK):
                fedge=open(gpio_path+self.name+'/edge','w+',0)
                fedge.write(val)
                fedge.close()
                return True
            else:
                print('Do not exist edge file in '+ self.name)
                return False
        else:
            print('Error: value must be -  none, rising, falling, both')
            return False

    edge=property(getedge,setedge)

    @property
    def fileobj(self):
        f=open(gpio_path+self.name+'/value','w+')
        return f

def export(num):
    num=str(num)
    if os.access(gpio_path+num, os.R_OK):
        print('gpio'+num+' already export.')
        return True
    elif int(num) not in range(0,203):
        print('gpio'+num+' absent.')
        return False
    else:
        call(["gpio-admin","export",num])
        return True

def unexport(num):
    num=str(num)
    if os.access(gpio_path+num, os.R_OK):
        call(["gpio-admin","unexport",num])
        return True
    else:
        print('gpio absent or not export')
        return False

def printlist():
    global glist
    global clist
    getlist()
    print(46*'-')
    print('chip:      label:      ngpio:')
    for chip in clist:
        print(chip+(11-len(chip))*' '+gpiochip(chip).label+9*' '+gpiochip(chip).ngpio)
    print(46*'-')
    print('gpio:   direction:   active:   value:   [edge]')
    for g in glist:
        print(g+(8-len(g))*' '+gpio(g).direction+(13-len(gpio(g).direction))*' '+str(gpio(g).active)+9*' '+str(gpio(g).value)+9*' '+gpio(g).edge)
    print(46*'-')


def getlist():
    global clist
    global glist
    clist=[]
    glist=[]
    filelist=os.listdir(gpio_path[:15])
    for name in filelist:
        if name[:8] == 'gpiochip':
            chip_num=re.findall(r'\d+',name)[0]
            clist.append(chip_num)
        elif name[:4] == 'gpio':
            gpio_num=re.findall(r'\d+',name)[0]
            glist.append(gpio_num)

def initial():
    printlist()

def main():
    initial()

if __name__ == "__main__":
    main()

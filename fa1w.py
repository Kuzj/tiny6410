#!/usr/bin/python
import os
import re

dev_path='/sys/bus/w1/devices'
master_path=dev_path+'/w1 bus master'
NO_re=re.compile('NO')
temp_re=re.compile('[0-9]{5}')
class master(object):
    @property
    def slave_count(self):
        if os.access(master_path+'/w1_master_slave_count', os.R_OK):
            fcount=open(master_path+'/w1_master_slave_count')
            c=int(fcount.read().rstrip())
            fcount.close()
            return c

    @property
    def slaves(self):
        if os.access(master_path+'/w1_master_slaves', os.R_OK):
            id=[]
            fcount=open(master_path+'/w1_master_slaves')
            for line in fcount:
                id.append(line.rstrip())
            fcount.close()
            return id

class slave(object):
    def __init__(self,id):
        if os.path.isdir(dev_path+'/'+id):
            self.id=id
        else:
            print 'Incorrect slave id.'

    @property
    def value(self):
        if os.access(dev_path+'/'+self.id+'/w1_slave', os.R_OK):
            fvalue=open(dev_path+'/'+self.id+'/w1_slave')
            val=fvalue.read()
            fvalue.close()
            return val


    @property
    def temp(self):
        if self.id[:2] in ['10','28']:
            val=self.value
            while NO_re.search(val):
                val=self.value
            return temp_re.search(val).group()
        else:
            print 'Is not a temperature sensor' 

def main():
    #print(master().slave_count)
    #print(master().slaves)
    for i in master().slaves:
        #print(slave(i).value)
        print (i+' - '+slave(i).temp)
if __name__=='__main__':
    main()

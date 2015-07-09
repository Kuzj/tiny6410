#!/usr/bin/python
from daemon import Daemon
from cc1101 import *
import sys
import time
import logging
import os
import socket
import threading
import Queue
import fagpio
import sqlite3
import traceback
from os.path import isfile

PIDFILE = '/var/run/daqd/daqd.pid'
LOGFILE = '/var/log/daqd/daqd.log'
SOCKFILE = '/var/run/daqd/daqd.sock'
SOCKFILE_OUT = '/var/run/daqd/daqd_out.sock'
DBFILE = './MainSt.db'
# Configure logging
FORMAT="%(asctime)-15s %(message)s"
logging.basicConfig(filename=LOGFILE,level=logging.DEBUG,format=FORMAT)
#debug=False
debug=True

def status():
    try:
        pf = file(PIDFILE,'r')
        pid = int(pf.read().strip())
        pf.close()
    except IOError:
        pid = None
    except SystemExit:
        pid = None
    if pid:
        return True
    else:
        return False

class ProcessThread(threading.Thread):
    def __init__(self):
        super(ProcessThread, self).__init__()
        self.running = True
        self.q = Queue.Queue()

    def add(self, data):
        self.q.put(data)

    def stop(self):
        self.running = False

    def run(self):
        q = self.q
        while self.running:
            try:
                # block for 1 second only:
                value = q.get(block=True, timeout=1)
                process(value)
            except Queue.Empty:
                sys.stdout.write('.')
                sys.stdout.flush()
        #
        if not q.empty():
            print "Elements left in the queue:"
            while not q.empty():
                print q.get()

#t = ProcessThread()
#t.start()

def process(value):
    """
    Implement this. Do something useful with the received data.
    """
    print value
    sleep(randint(1,9))    # emulating processing time

class sock_thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.running=True

    def stop(self):
        self.running=False

    def run(self):
        sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.remove(SOCKFILE)
        except OSError:
            pass
        sock.bind(SOCKFILE)
        sock.listen(1)
        conn, addr=sock.accept()
        data='dummy'
        while len(data):
            data=conn.recv(1024)
            logging.info('Receive from socket: '+data)
            t=time.ctime()
            rez=''
            if data in cc1101.command_list:
                methodToCall=getattr(mod1,data)
                methodToCall()
                conn.send(t+': Ok')
                logging.info('Send on cc1101: '+data)
            else:
                conn.send(t+': Not in command list')
                logging.info('Command from socket not in command list')

class sock_thread_out(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.running=True

    def stop(self):
        self.running=False

    def run(self):
        if not mod0.GDO0State:
            mod0.GDO0Open()
        mod0.FlushRX()
        mod0.Srx()
        while self.running:
            if debug:logging.info('Before poll')
            events=mod0.epoll_obj.poll(5)
            for fileno,event in events:
                if debug:logging.info('event file:'+str(fileno)+' event:'+str(event)+' GDO0File:'+str(mod0.GDO0File.fileno()))
                if fileno==mod0.GDO0File.fileno():
                    data=mod0.ReadBuffer()
                    logging.info('Receive from cc1101: '+data)
                    try:
                        sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        sock.connect(SOCKFILE_OUT)
                        sock.send(data)
                        sock.recv(1024)
                        sock.close()
                        logging.info('Send to socket: '+data)
                    except Exception,e:
                        logging.info('OpenSCADA socket error: '+str(e))
                    mod0.FlushRX()
                    mod0.Srx()
                    #raise Exception(e)
            if mod0.Marcstate()<>'RX':
                if debug:logging.info('Flush with out read buffer')
                mod0.FlushRX()
                mod0.Srx()

class sock_thread_gpio(threading.Thread):

    def __init__(self,id,gpio,edge):
        threading.Thread.__init__(self)
        self.running=True
        self.id=id
        self.gpio=gpio
        self.edge=edge

    def stop(self):
        self.running=False

    def run(self):
        gpio=fagpio.gpio(self.gpio)
        gpio.edge=self.edge
        gpio.direction='out'
        s_id=str(self.id)
        s_gpio=str(self.gpio)
        while self.running:
            events=gpio.epoll_obj.poll(5)
            if debug:logging.info('sensor id ' + s_id + ': no event')
            for fileno,event in events:
                if debug:logging.info('event file:'+str(fileno)+' event:'+str(event)+' file:'+str(gpio.fvalue.fileno()))
                if fileno==gpio.fvalue.fileno():
                    data=s_id+':'+str(gpio.value)
                    logging.info('sensor id ' + s_id + ' gpio ' + s_gpio + ': ' + data)
                    try:
                        sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        sock.connect(SOCKFILE_OUT)
                        sock.send(data)
                        sock.recv(1024)
                        sock.close()
                        logging.info('Send to socket: '+data)
                    except Exception,e:
                        logging.info('OpenSCADA socket error: '+str(e))
        logging.info('Stop thread for sensor '+s_id+' on gpio '+s_gpio+' with edge '+ self.edge)

class daqd(Daemon):

    def run(self):
        try:
            sock=sock_thread()
            sock.start()
            #sock.join()
            sock_out_list=[]
            for id,num,edge in int_daqd_gpio:
                sock_out=sock_thread_gpio(id,num,edge)
                sock_out_list.append(sock_out)
                sock_out.start()
                #sock_out.join()
                logging.info('Start thread for sensor '+str(id)+' on gpio '+str(num)+' with edge '+edge)
                time.sleep(0.5)
            #sock_out.start()
            #sock_out.join()
        # Logging errors and exceptions
        except Exception, e:
            logging.exception('Exception will be captured and added to the log file automaticaly')

if __name__ == "__main__":
    daemon = daqd(PIDFILE)
    if isfile(DBFILE):
        conn=sqlite3.connect(DBFILE)
    else:
        print(DBFILE+' file is not exist')
        logging.info(DBFILE+' file is not exist')
        raise
    int_daqd_gpio=[]
    cur=conn.cursor()
    cur.execute('select t.sensor_id,t.gpio_number,e.value from interface_daqd_gpio t, gpio_edge e, sensors s where t.sensor_id=s.id and t.edge_id=e.id and s.enable=1')
    for row in cur:
        int_daqd_gpio.append(row)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            print "Starting..."
            logging.info('Starting...')
            for row in int_daqd_gpio:
                fagpio.export(row[1])
                logging.info('Export '+str(row[1])+' gpio')
            mod0=cc1101(0)
            mod0.Init(7)
            mod1=cc1101(1)
            mod1.Init(4)
            daemon.start()
        elif 'stop' == sys.argv[1]:
                print "Stoping ..."
                conn.close()
                try:
                    for row in int_daqd_gpio:
                        fagpio.unexport(row[1])
                        logging.info('Unxport '+str(row[1])+' gpio')
                    os.remove(SOCKFILE)
                    mod0=cc1101(0)
                    mod0.Close()
                    mod1=cc1101(1)
                    mod1.Close()
                except OSError:
                    pass
                daemon.stop()
                logging.info('Stoping...')
        elif 'restart' == sys.argv[1]:
                print "Restaring ..."
                daemon.restart()
                logging.info('Restart...')
        elif 'status' == sys.argv[1]:
            try:
                pf = file(PIDFILE,'r')
                pid = int(pf.read().strip())
                pf.close()
            except IOError:
                pid = None
            except SystemExit:
                pid = None
            if pid:
                print 'daqd is running as pid %s' % pid
            else:
                print 'daqd is not running.'
        else:
            print "Unknown command"
            sys.exit(2)
            sys.exit(0)
    else:
        print "usage: %s start|stop|restart|status" % sys.argv[0]
        sys.exit(2)

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

PIDFILE = '/var/run/cc1101d/cc1101d.pid'
LOGFILE = '/var/log/cc1101d/cc1101d.log'
SOCKFILE = '/var/run/cc1101d/cc1101d.sock'
SOCKFILE_OUT = '/var/run/cc1101d/cc1101d_out.sock'
# Configure logging
FORMAT="%(asctime)-15s %(message)s"
logging.basicConfig(filename=LOGFILE,level=logging.DEBUG,format=FORMAT)

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
            logging.info('Send: '+data)
            t=time.ctime()
            rez=''
            if data in cc1101.command_list:
                methodToCall=getattr(mod1,data)
                methodToCall()
                conn.send(t+': Ok')
                logging.info('Succed: '+data)
            else:
                conn.send(t+': Bad command')
                logging.info('Bad command')

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
            logging.info('before poll')
            events=mod0.epoll_obj.poll(5)
            for fileno,event in events:
                logging.info('event file:'+str(fileno)+' event:'+str(event)+' GDO0File:'+str(mod0.GDO0File.fileno()))
                if fileno==mod0.GDO0File.fileno():
                    data=mod0.ReadBuffer()
                    logging.info('Read buffer: '+data)
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
                logging.info('Flush with out read buffer')
                mod0.FlushRX()
                mod0.Srx()

class cc1101d(Daemon):

    def run(self):
        try:
            sock=sock_thread()
            sock.start()
            sock_out=sock_thread_out()
            sock_out.start()
            sock.join()
            sock_out.join()
        # Logging errors and exceptions
        except Exception, e:
            logging.exception('Exception will be captured and added to the log file automaticaly')

if __name__ == "__main__":
    daemon = cc1101d(PIDFILE)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            try:
                print "Starting..."
                logging.info('Starting...')
                mod0=cc1101(0)
                mod0.Init(7)
                mod1=cc1101(1)
                mod1.Init(4)
                #mod1.LevoloPreSend()
                daemon.start()
            except:
                pass
        elif 'stop' == sys.argv[1]:
                print "Stopping ..."
                try:
                    os.remove(SOCKFILE)
                    mod0=cc1101(0)
                    mod0.Close()
                    mod1=cc1101(1)
                    mod1.Close()
                except OSError:
                    pass
                daemon.stop()
                logging.info('Stopping...')

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
                print 'cc1101d is running as pid %s' % pid
            else:
                print 'cc1101d is not running.'
        else:
            print "Unknown command"
            sys.exit(2)
            sys.exit(0)
    else:
        print "usage: %s start|stop|restart|status" % sys.argv[0]
        sys.exit(2)

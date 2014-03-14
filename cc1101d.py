#!/usr/bin/python
from daemon import Daemon
from cc1101 import *
import sys
import time
import logging
import os
import socket
import threading

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

class sock_thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

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
            if data in CommandList:
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

    def run(self):
        while 1:
            data=mod0.Receive(1100)
            try:
                sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(SOCKFILE_OUT)
            except Exception,e:
                logging.info('OpenSCADA socket connect error: '+e)
                raise Exception(e)
            logging.info('Receive: '+data)
            sock.send(data)
            sock.recv(1024)
            sock.close()

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
                mod0.Init(4)
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
                    mod1=cc1101(1)
                    mod0.Close()
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

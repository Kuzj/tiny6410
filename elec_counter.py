#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals
import fagpio
import time
import sqlite3
import threading
import socket
import os
import time
import sys

num=131
init_value=6701.5
main_value=init_value
signal_step=0.0003125
ELECFILE = '/var/run/daqd/elec.sock'

class electric_counter():
    def __init__(self,v):
        self.value=v
        self.act_pow=0
    def inc(self):
        self.value+=signal_step
    def sectokw(self,t):
        return round(9/(8*t),3)
    def period(self,t):
        self.act_pow=self.sectokw(t)

ec=electric_counter(main_value)

class elec_control_thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.running=True

    def stop(self):
        self.running=False

    def run(self):
        print('elec control thread start')
        sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            os.remove(ELECFILE)
        except OSError:
            pass
        try:
            sock.bind(ELECFILE)
            sock.listen(1)
        except Exception,e:
            pass
            print(str(e))
            #logging.info(str(e))
        while self.running:#len(data):
            try:
                conn, addr=sock.accept()
                conn.settimeout(1)
                print('elec control socket connect')
            except socket.timeout,e:
                continue
            except Exception,e:
                print('elec control socket error: '+str(e))
                self.running=False
                break
            while self.running:
                try:
                    data=conn.recv(16)
                except socket.timeout,e:
                    continue
                except Exception,e:
                    print(e)
                else:
                    print('elec control receive: '+data)
                    t=time.ctime()
                    try:
                        if data == '?':
                            conn.send(str(ec.act_pow))
                        else:
                            conn.send(t+'send `?`'+data)
                    except Exception,e:
                        print('elec control send error: '+str(e))
                        break
        print('elec control thread stop')

class elec_com_thread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running=True

    def stop(self):
        self.running=False

    def run(self):
        print('elec communication thread start')
        try:
            fagpio.export(num)
            gpio=fagpio.gpio(num)
            gpio.edge='rising'
            gpio.direction='in'
            gpio.active=1
            t=time.time()
            i=0
            while self.running:
                events=gpio.epoll_obj.poll(1)
                for fileno,event in events:
                    if fileno==gpio.fvalue.fileno():
                        now=time.time()
                        diff=round(now-t,2)
                        t=now
                        if i>1:
                            ec.inc()
                            ec.period(diff)
                            print(str(ec.value)+' '+str(diff)+' '+ str(ec.act_pow))
                        else:
                            i+=1
                            print('.')
        except Exception,e:
            print('elec communication error: '+str(e))
        finally:
            fagpio.unexport(num)
            print('elec communication thread stop')
main=elec_com_thread()
main.start()
elec=elec_control_thread()
elec.start()
while True:
    try:
        time.sleep(1)
    except:
        print('stop')
        elec.stop()
        main.stop()
        sys.exit(0)

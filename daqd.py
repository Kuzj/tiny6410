#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals
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
import signal
from os.path import isfile

PIDFILE = '/var/run/daqd/daqd.pid'
LOGFILE = '/var/log/daqd/daqd.log'
SOCKFILE = '/var/run/daqd/daqd.sock'
SOCKFILE_OUT = '/var/run/daqd/daqd_out.sock'
ELECFILE = '/var/run/daqd/elec.sock'
DBFILE = './MainSt.db'
# Настройка электро-счетчика
elec_gpio=131
init_value=6701.5
main_value=init_value
signal_step=0.0003125
sock_buffer=32
# Configure logging
FORMAT="%(asctime)-15s %(message)s"
#CRITICAL=50 ERROR=40 WARNING=30 INFO=20 DEBUG=10 NOTSET=0
#logging.basicConfig(filename=LOGFILE,level=logging.WARNING,format=FORMAT)
logging.basicConfig(filename=LOGFILE,level=logging.INFO,format=FORMAT)
#debug=False
#debug=True

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
# Поток для очереди куда добавляются все сообщения
# для отправки в openscada
# испльзуется daemon.send_sock_queue
class queue_thread(threading.Thread):
    def __init__(self):
        super(queue_thread, self).__init__()
        self.running = True
        self.q = Queue.Queue()

    def add(self, data):
        self.q.put(data)

    def stop(self):
        self.running = False

    def run(self):
        logging.critical('queue: start')
        while self.running:
            try:
                # block for 1 second only:
                value = self.q.get(block=True, timeout=1)
                send2scada(value)
            except Queue.Empty:
                pass
        logging.critical('queue: stop')
        if not q.empty():
            logging.warning("queue: elements left in the queue")
            while not q.empty():
                logging.warning('queue: element in queue: '+q.get())


def send2scada(value):
    def xml_str(sensor_id,data,action_id):
        return '<?xml version="1.0" encoding="utf-8"?>\n<PACKAGE>\n<SENSOR sensor_id="'+str(sensor_id)+'" message="'+data+'" action_id="'+str(action_id)+'"/>\n</PACKAGE>'
    def send(sensor_id,value,action_id):
        try:
            sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(SOCKFILE_OUT)
            sock.send(xml_str(sensor_id,value,action_id))
            sock.recv(sock_buffer)
            sock.close()
            logging.info('send to OpenSCADA: '+str(sensor_id)+'|'+value+'|'+str(action_id))
        except Exception,e:
            logging.error('OpenSCADA socket error: '+str(e))
    try:
        # Так как датчик может передовать только информацию, без опозновательных сигналов:
        # Считать количество датчиков на одной настройке cc1101 
        cur.execute('select count(*) from interface_daqd_cc1101 where config_num=?',str(mod1.config))
        count=cur.fetchone()[0]
        # Если настройка cc1101 используется только для одного датчика, то брать sensor_id по номеру настройки
        if count==1:
            cur.execute('select s.id, s.action_id from sensors s, interface_daqd_cc1101 c where s.id=c.sensor_id and c.config_num=?',str(mod1.config))
            sensor_id,action_id=cur.fetchone()
            send(sensor_id,value,action_id)
        # Если больше одного датчика используют одну настройку, то брать sensor_id по сообщению передоваемого датчиком 
        elif count>1:
            cur.execute('select s.id, s.action_id from sensors s, interface_daqd_cc1101 c where s.id=c.sensor_id and c.message=? and c.config_num=?',data,str(mod1.config))
            sensor_id,action_id=cur.fetchone()
            send(sensor_id,value,action_id)
    except Exception,e:
        logging.error('send2scada: '+str(e))

# Обработчик команд для CC1101
# Команды полученные в сокет SOCKFILE,
# если они содержаться в cc1101.commandlist
# будут отправлены через модуль сс1101: mod0
class cc1101_control_thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.running=True

    def stop(self):
        self.running=False

    def run(self):
        logging.critical('cc1101 control: start')
        sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            os.remove(SOCKFILE)
        except OSError:
            pass
        try:
            sock.bind(SOCKFILE)
            sock.listen(1)
        except Exception,e:
            logging.error('cc1101 control: socket error: '+str(e))
        while self.running:
            try:
                conn, addr=sock.accept()
                conn.settimeout(1)
            except socket.timeout,e:
                logging.debug('cc1101 control: socket timeout')
                continue
            except Exception,e:
                logging.error('cc1101 control: socket error: '+str(e))
                break
            while self.running:
                try:
                    data=conn.recv(sock_buffer)
                except socket.timeout,e:
                    continue
                except Exception,e:
                    logging.error(str(e))
                else:
                    logging.info('cc1101 control: receive: '+data)
                    t=time.ctime()
                    rez=''
                    try:
                        if data in cc1101.command_list:
                            methodToCall=getattr(mod0,data)
                            methodToCall()
                            conn.send(t+': Ok')
                            logging.info('cc1101 control: send on cc1101: '+data)
                        else:
                            conn.send(t+': not in command list')
                            logging.error('cc1101 control: not in command list')
                    except Exception,e:
                        logging.error('cc1101 control: send error:'+str(e))
                        break
        logging.critical('cc1101 control: stop')

# Прослушивание частоты настроенной на модуле CC1101
# mod1, все что получено(data)(определяется функциями в зависимости
# от настройки CC1101) отсылается в очередь на передачу
# в сокет SOCKFILE_OUT для передачи в Openscada.
class cc1101_com_thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.running=True

    def stop(self):
        self.running=False

    def run(self):
        logging.critical('cc1101 communication: start')
        if not mod1.GDO0State:
            mod1.GDO0Open()
        mod1.FlushRX()
        mod1.Srx()
        while self.running:
            logging.debug('cc1101 communication: before poll')
            events=mod1.epoll_obj.poll(1)
            for fileno,event in events:
                logging.debug('cc1101 communication: event file:'+str(fileno)+' event:'+str(event)+' GDO0File:'+str(mod1.GDO0File.fileno()))
                if fileno==mod1.GDO0File.fileno():
                    data=mod1.ReadBuffer()
                    logging.info('cc1101 communication: receive: '+data)
                    daemon.queue.add(data)
                    mod1.FlushRX()
                    mod1.Srx()
            if mod1.Marcstate()!='RX':
                logging.error('cc1101 communication: flush with out read buffer')
                mod1.FlushRX()
                mod1.Srx()
        logging.critical('cc1101 communication: stop')
# Для каждого включенного датчика gpio
# запускается свой поток
class gpio_com_thread(threading.Thread):

    def __init__(self,id,gpio,dir,act,edge):
        threading.Thread.__init__(self)
        self.running=True
        self.id=id
        self.gpio=gpio
        self.dir=dir
        self.act=act
        self.edge=edge
        fagpio.export(gpio)
        logging.critical('gpio communication: export '+str(gpio)+' gpio')

    def stop(self):
        self.running=False

    def run(self):
        gpio=fagpio.gpio(self.gpio)
        gpio.edge=self.edge
        gpio.direction=self.dir
        gpio.active=self.act
        s_id=str(self.id)
        s_gpio=str(self.gpio)
        logging.critical('gpio communication: start sensor '+s_id+' on gpio '+s_gpio+' with edge '+ self.edge)
        while self.running:
            events=gpio.epoll_obj.poll(1)
            logging.debug('gpio communication: sensor id ' + s_id + ': no event')
            for fileno,event in events:
                logging.debug('gpio communication: event file:'+str(fileno)+' event:'+str(event)+' file:'+str(gpio.fvalue.fileno()))
                if fileno==gpio.fvalue.fileno():
                    data=s_id+':'+str(gpio.value)
                    logging.info('gpio communication: sensor id ' + s_id + ' gpio ' + s_gpio + ': ' + data)
                    daemon.queue.add(data)
        fagpio.unexport(self.gpio)
        logging.critical('gpio communication: unexport '+str(self.gpio)+' gpio')
        logging.critical('gpio communication: stop sensor '+s_id+' on gpio '+s_gpio+' with edge '+ self.edge)

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
        logging.critical('elec control: start')
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
            logging.error('elec control: socket error: '+str(e))
        while self.running:
            try:
                conn, addr=sock.accept()
                conn.settimeout(1)
                logging.info('elec control: socket connect')
            except socket.timeout,e:
                continue
            except Exception,e:
                logging.error('elec control: socket error: '+str(e))
                break
            while self.running:
                try:
                    data=conn.recv(sock_buffer)
                except socket.timeout,e:
                    continue
                except Exception,e:
                    logging.error(str(e))
                else:
                    logging.info('elec control: receive: '+data)
                    t=time.ctime()
                    try:
                        if data == '?':
                            conn.send(str(ec.act_pow))
                        else:
                            conn.send(t+'send `?`'+data)
                    except Exception,e:
                        logging.error('elec control: send error: '+str(e))
                        break
        logging.critical('elec control: stop')

class elec_com_thread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running=True

    def stop(self):
        self.running=False

    def run(self):
        logging.critical('elec communication: start')
        try:
            fagpio.export(elec_gpio)
            gpio=fagpio.gpio(elec_gpio)
            gpio.edge='rising'
            gpio.direction='in'
            gpio.active=1
            t=time.time()
            i=0
            while self.running:
                logging.debug('elec communication: before poll')
                events=gpio.epoll_obj.poll(1)
                for fileno,event in events:
                    if fileno==gpio.fvalue.fileno():
                        now=time.time()
                        diff=round(now-t,2)
                        t=now
                        if i>1:
                            ec.inc()
                            ec.period(diff)
                            logging.info('elec communication: '+str(ec.value)+' '+str(diff)+' '+ str(ec.act_pow))
                        else:
                            i+=1
                            logging.info('elec communication: init..')
        except Exception,e:
            logging.error('elec communication: '+str(e))
        finally:
            fagpio.unexport(elec_gpio)
            logging.critical('elec communication: stop')


class daqd(Daemon):

    def run(self):
        try:
            self.queue = queue_thread()
            self.queue.start()
            self.cc1101_control=cc1101_control_thread()
            self.cc1101_control.start()
            self.cc1101_com=cc1101_com_thread()
            self.cc1101_com.start()
            self.elec_control=elec_control_thread()
            self.elec_control.start()
            self.elec_com=elec_com_thread()
            self.elec_com.start()
            self.gpio_com_list=[]
            for id,num,dir,act,edge in int_daqd_gpio:
                gpio_com=gpio_com_thread(id,num,dir,act,edge)
                self.gpio_com_list.append(gpio_com)
                gpio_com.start()
                time.sleep(0.5)
        except Exception, e:
            logging.error('daqd exception: '+str(e))

def sigterm_handler(signal,frame):
    logging.critical('catch SIGTERM')
    daemon.queue.stop()
    daemon.cc1101_control.stop()
    daemon.cc1101_com.stop()
    daemon.elec_control.stop()
    daemon.elec_com.stop()
    for gpio_com in daemon.gpio_com_list:
        gpio_com.stop()
    sys.exit(0)

if __name__ == "__main__":
    daemon = daqd(PIDFILE)
    if isfile(DBFILE):
        conn=sqlite3.connect(DBFILE,check_same_thread=False)
    else:
        print(DBFILE+' file is not exist')
        logging.error(DBFILE+' file is not exist')
        raise
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            print("Starting...")
            logging.critical('Starting...')
            signal.signal(signal.SIGTERM, sigterm_handler)
            int_daqd_gpio=[]
            cur=conn.cursor()
            cur.execute('select t.sensor_id,t.gpio_number,t.direction,t.active,e.value from interface_daqd_gpio t, gpio_edge e, sensors s where t.sensor_id=s.id and t.edge_id=e.id and s.enable=1')
            for row in cur:
                int_daqd_gpio.append(row)
            mod1=cc1101(1)
            mod1.Init(7)
            mod0=cc1101(0)
            mod0.Init(4)
            daemon.start()
            # Основной поток должен остоваться, чтобы ловить сигнал SIGTERM
            while True:
                time.sleep(1)
        elif 'stop' == sys.argv[1]:
            print("Stop...")
            logging.critical('Stop...')
            conn.close()
            try:
                os.remove(SOCKFILE)
            except OSError:
                pass
            try:
                os.remove(ELECFILE)
            except OSError:
                pass
            mod1=cc1101(1)
            mod1.Close()
            mod0=cc1101(0)
            mod0.Close()
            daemon.stop()
        elif 'restart' == sys.argv[1]:
                print("Restart...")
                daemon.restart()
                logging.critical('Restart...')
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
                print('daqd is running as pid %s' % pid)
            else:
                print('daqd is not running.')
        else:
            print("Unknown command")
            sys.exit(2)
            sys.exit(0)
    else:
        print("usage: %s start|stop|restart|status" % sys.argv[0])
        sys.exit(2)

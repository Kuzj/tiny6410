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
sock_buffer=32
# Configure logging
FORMAT="%(asctime)-15s %(message)s"
#CRITICAL=50 ERROR=40 WARNING=30 INFO=20 DEBUG=10 NOTSET=0
#logging.basicConfig(filename=LOGFILE,level=logging.WARNING,format=FORMAT)
logging.basicConfig(filename=LOGFILE,level=logging.INFO,format=FORMAT)

class counter():
    def __init__(self,init_val,step,id):
        self.init_value=init_val
        self.value=init_val
        self.step=step
        self.id=id
        self.vih=0
        self.vid=0

    def inc(self):
        self.value+=self.step

    def val_in_hour(self,t):
        return round(3600/t*self.step,3)

    def val_in_day(self,t):
        return round(3600*24/t*self.step,3)

    def period(self,t):
        self.vih=self.val_in_hour(t)
        self.vid=self.val_in_day(t)

    def save(self):
        if self.ischange():
            try:
                cur=conn.cursor()
                cur.execute('update daqd_sensors set count_value='+str(self.value)+' where id=?',str(self.id))
                conn.commit()
                logging.debug('counter: save '+str(self.id)+' sensor counter value: '+str(self.value))
            except Exception,e:
                logging.error('counter: error update count_value: '+str(e))

    def reset(self):
        self.value=0
        self.save()

    def ischange(self):
        if self.value <> self.init_value:
            return True

class sensor():
    def __init__(self,id,interface_id,enabled,count):
        try:
            self.id=id
            self.interface_id=interface_id
            self.enabled=enabled
            cur=conn.cursor()
            if int(count):
                cur.execute('select count_value, count_step from daqd_sensors where id=?',str(self.id))
                value,step=cur.fetchone()
                self.counter=counter(value,step,self.id)
            if self.isgpio():
                cur.execute('select t.gpio_number,t.direction,t.active,e.value from daqd_interface_gpio t, daqd_gpio_edge e where t.sensor_id=? and t.edge_id=e.id',str(self.id))
                num,dir,act,edge=cur.fetchone() 
                self.thread=gpio_com_thread(self.id,num,dir,act,edge,count)
        except Exception, e:
            logging.error('sensor init error: '+str(e))
            
    def enable(self):
        if not self.enabled:
            try:
                cur.execute('update daqd_sensors set enabled=1 where id=?',str(self.id))
                conn.commit()
                self.enabled=1
            except Exception, e:
                logging.error('sensor enable error: '+str(e))

    def disable(self):
        if self.enabled:
            try:
                cur.execute('update daqd_sensors set enabled=0 where id=?',str(self.id))
                conn.commit()
                self.enabled=0
            except Exception, e:
                logging.error('sensor disable error: '+str(e))
    
    def start(self):
        if self.enabled and hasattr(self,'thread'):
            self.thread.start()
        else:
            logging.error('sensor '+str(self.id)+' don`t start')
                
    def stop(self):
        if hasattr(self,'thread'):
            self.thread.stop()
        else:
            logging.error('sensor '+str(self.id)+' don`t stop')
    
    def isgpio(self):
        if int(self.interface_id)==2:
            return True
        return False

class rf_module(cc1101):
    def __init__(self,id,config,rx):
        cc1101.__init__(self,id)
        self.Init(config)
        self.rx=rx
        self.thread=cc1101_com_thread(id)
        
# Поток для очереди входящих(in) и исходящих(out) сообщений
class queue_thread(threading.Thread):
    def __init__(self,direction):
        super(queue_thread, self).__init__()
        self.running = True
        self.q = Queue.Queue()
        self.direction=direction

    def add(self, data):
        self.q.put(data)

    def stop(self):
        self.running = False

    def run(self):
        logging.critical('queue '+self.direction+': start')
        while self.running:
            try:
                value = self.q.get(block=True, timeout=1)
                logging.debug('queue "'+self.direction+'" size: '+str(self.q.qsize()))
                if self.direction=='out':
                    send2scada(value)
                elif self.direction=='in':
                    exec_control(value)
            except Queue.Empty:
                pass
        logging.critical('queue "'+self.direction+'": stop')
        if not q.empty():
            logging.warning('queue "'+self.direction+'": elements left in the queue')
            while not q.empty():
                logging.warning('queue "'+self.direction+'": element in queue: '+q.get())

def exec_control(value):
    methodToCall=getattr(rf_modules[1],value)
    methodToCall()

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
        cur.execute('select count(*) from daqd_interface_cc1101 where config_num=?',str(rf_modules[1].config))
        count=cur.fetchone()[0]
        # Если настройка cc1101 используется только для одного датчика, то брать sensor_id по номеру настройки
        if count==1:
            cur.execute('select s.id, s.action_id from daqd_sensors s, daqd_interface_cc1101 c where s.id=c.sensor_id and c.config_num=?',str(rf_modules[1].config))
            sensor_id,action_id=cur.fetchone()
            send(sensor_id,value,action_id)
        # Если больше одного датчика используют одну настройку, то брать sensor_id по сообщению передоваемого датчиком 
        elif count>1:
            cur.execute('select s.id, s.action_id from daqd_sensors s, daqd_interface_cc1101 c where s.id=c.sensor_id and c.message=? and c.config_num=?',data,str(rf_modules[1].config))
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
                            daemon.queue_in.add(data)
                            conn.send(t+': Ok')
                            logging.info('cc1101 control: send on cc1101: '+data)
                        else:
                            conn.send(t+': not in command list')
                            logging.error('cc1101 control: not in command list')
                    except Exception,e:
                        logging.error('cc1101 control: send error:'+str(e))
                        break
        logging.critical('cc1101 control: stop')

class daqd_control_thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.running=True

    def stop(self):
        self.running=False

    def run(self):
        logging.critical('daqd control: start')
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
            logging.error('daqd control: socket error: '+str(e))
        while self.running:
            try:
                conn, addr=sock.accept()
                conn.settimeout(1)
            except socket.timeout,e:
                logging.debug('daqd control: socket timeout')
                continue
            except Exception,e:
                logging.error('daqd control: socket error: '+str(e))
                break
            while self.running:
                try:
                    data=conn.recv(sock_buffer)
                except socket.timeout,e:
                    continue
                except Exception,e:
                    logging.error(str(e))
                else:
                    logging.info('daqd control: receive: '+data)
                    t=time.ctime()
                    rez=''
                    try:
                        if data in cc1101.command_list:
                            daemon.queue_in.add(data)
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
# все что получено(data)(определяется функциями в зависимости
# от настройки CC1101) отсылается в очередь на передачу
# в сокет для передачи в Openscada.
class cc1101_com_thread(threading.Thread):

    def __init__(self,id):
        threading.Thread.__init__(self)
        self.running=True
        self.id=id

    def stop(self):
        self.running=False

    def run(self):
        logging.critical('cc1101('+str(self.id)+') communication: start')
        try:
            if not rf_modules[self.id].GDO0State:
                rf_modules[self.id].GDO0Open()
            rf_modules[self.id].FlushRX()
            rf_modules[self.id].Srx()
            while self.running:
                logging.debug('cc1101('+str(self.id)+') communication: before poll')
                events=rf_modules[self.id].epoll_obj.poll(1)
                for fileno,event in events:
                    logging.debug('cc1101('+str(self.id)+') communication: event file:'+str(fileno)+' event:'+str(event)+' GDO0File:'+str(rf_modules[self.id].GDO0File.fileno()))
                    if fileno==rf_modules[self.id].GDO0File.fileno():
                        data=rf_modules[self.id].ReadBuffer()
                        logging.info('cc1101('+str(self.id)+') communication: receive: '+data)
                        daemon.queue_out.add(data)
                        rf_modules[self.id].FlushRX()
                        rf_modules[self.id].Srx()
                if rf_modules[self.id].Marcstate()!='RX':
                    logging.error('cc1101('+str(self.id)+') communication: flush with out read buffer')
                    rf_modules[self.id].FlushRX()
                    rf_modules[self.id].Srx()
            rf_modules[self.id].Close()
        except Exception,e:
            logging.error('cc1101('+str(self.id)+') communication: '+str(e))
        logging.critical('cc1101('+str(self.id)+') communication: stop')
       
# Для каждого включенного датчика gpio
# запускается свой поток
class gpio_com_thread(threading.Thread):

    def __init__(self,id,gpio,dir,act,edge,counter):
        threading.Thread.__init__(self)
        self.running=True
        self.id=id
        self.gpio=gpio
        self.dir=dir
        self.act=act
        self.edge=edge
        self.counter=counter
        fagpio.export(gpio)
        logging.critical('gpio communication: export '+str(gpio)+' gpio')

    def stop(self):
        if self.counter and sensors[self.id].counter.ischange():
            sensors[self.id].counter.save()
        self.running=False

    def run(self):
        try:
            gpio=fagpio.gpio(self.gpio)
            gpio.edge=self.edge
            gpio.direction=self.dir
            gpio.active=self.act
            s_id=str(self.id)
            s_gpio=str(self.gpio)
            logging.critical('gpio communication: start sensor:'+s_id+' gpio:'+s_gpio+' edge:'+ self.edge+' counter:'+ str(self.counter))
            #Если включен счетчик на датчике
            if self.counter:
                t=time.time()
                i=0
                while self.running:
                    events=gpio.epoll_obj.poll(1)
                    logging.debug('gpio communication: sensor id ' + s_id + ': no event')
                    for fileno,event in events:
                        if fileno==gpio.fvalue.fileno():
                            now=time.time()
                            diff=round(now-t,2)
                            t=now
                            if i>1:
                                sensors[self.id].counter.inc()
                                sensors[self.id].counter.period(diff)
                                logging.info('gpio communication: sensor '+ s_id + ' value:'+str(sensors[self.id].counter.value)+' '+str(diff)+' '+ str(sensors[self.id].counter.vih)+' '+ str(sensors[self.id].counter.vid))
                            else:
                                i+=1
                                logging.info('gpio communication: sensor '+ s_id + ' counter init..')
            else:
                while self.running:
                    events=gpio.epoll_obj.poll(1)
                    logging.debug('gpio communication: sensor id ' + s_id + ': no event')
                    for fileno,event in events:
                        logging.debug('gpio communication: event file:'+str(fileno)+' event:'+str(event)+' file:'+str(gpio.fvalue.fileno()))
                        if fileno==gpio.fvalue.fileno():
                            #data=s_id+':'+str(gpio.value)
                            logging.info('gpio communication: sensor ' + s_id + ' signal')
                            daemon.queue_out.add(s_id)
        except Exception,e:
            logging.error('gpio communication: '+str(e))
        finally:
            fagpio.unexport(self.gpio)
            logging.critical('gpio communication: unexport '+str(self.gpio)+' gpio')
            logging.critical('gpio communication: stop sensor:'+s_id+' gpio:'+s_gpio+' edge:'+ self.edge+' counter:'+ str(self.counter))
            
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
                        if data[0] == '?':
                            conn.send(str(sensors[data[1:]].counter.value))
                        else:
                            conn.send(t+'send `?`'+data)
                    except Exception,e:
                        logging.error('elec control: send error: '+str(e))
                        break
        logging.critical('elec control: stop')

class daqd(Daemon):

    def run(self):
        try:
            self.queue_out = queue_thread('out')
            self.queue_out.start()
            self.queue_in = queue_thread('in')
            self.queue_in.start()
            self.cc1101_control=cc1101_control_thread()
            self.cc1101_control.start()
            self.elec_control=elec_control_thread()
            self.elec_control.start()
            for s in sensors:
                if sensors[s].isgpio():
                    sensors[s].start()
            for r in rf_modules:
                if rf_modules[r].rx:
                    rf_modules[r].thread.start()
        except Exception, e:
            logging.error('daqd exception: '+str(e))

def sigterm_handler(signal,frame):
    logging.critical('catch SIGTERM')
    daemon.queue_out.stop()
    daemon.queue_in.stop()
    daemon.cc1101_control.stop()
    daemon.elec_control.stop()
    for s in sensors:
        if sensors[s].isgpio():
            sensors[s].stop()
    for r in rf_modules:
        if rf_modules[r].rx:
            rf_modules[r].thread.stop()
            time.sleep(1)
        rf_modules[r].Close()
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
            cur=conn.cursor()
            sensors = dict()
            cur.execute('select id, interface_id, enabled, counter from daqd_sensors')
            for row in cur:
                sensors[row[0]]=sensor(row[0],row[1],row[2],row[3])
            rf_modules = dict()
            cur.execute('select id,config,rx from daqd_config_cc1101')
            for row in cur:
                rf_modules[row[0]]=rf_module(row[0],row[1],row[2])
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
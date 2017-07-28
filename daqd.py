#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals
import Queue
import logging
import os
import signal
import socket
import sqlite3
import sys
import threading
import fagpio
import time
import re
from os.path import isfile

from cc1101 import Cc1101
from daemon import Daemon

PIDFILE = '/var/run/daqd/daqd.pid'
LOGFILE = '/var/log/daqd/daqd.log'
SOCKFILE = '/var/run/daqd/daqd.sock'
SOCKFILE_OUT = '/var/run/daqd/daqd_out.sock'
DBFILE = './daqd.db'
sock_buffer = 32
# Configure logging
FORMAT = "%(asctime)-15s %(message)s"


# CRITICAL=50 ERROR=40 WARNING=30 INFO=20 DEBUG=10 NOTSET=0
# logging.basicConfig(filename=LOGFILE,level=logging.ERROR,format=FORMAT)
# logging.basicConfig(filename=LOGFILE,level=logging.WARNING,format=FORMAT)
# logging.basicConfig(filename=LOGFILE,level=logging.INFO,format=FORMAT)

def error_logger(decorated):
    def decorator(*args, **kwargs):
        try:
            return decorated(*args, **kwargs)
        except:
            logging.critical("error in %s:", decorated.__name__, exc_info=True)
    return decorator

class Counter:
    def __init__(self, init_val, step, id_):
        self.save_value = init_val
        self.value = init_val
        self.step = step
        self.id = id_
        self.vih = 0
        self.vid = 0

    def inc(self):
        self.value += self.step

    def val_in_hour(self, t):
        if t>0 and self.step>0:
            return round(3600 / t * self.step, 3)
        else:
            return 0

    def val_in_day(self, t):
        if t > 0 and self.step > 0:
            return round(3600 * 24 / t * self.step, 3)
        else:
            return 0

    def period(self, t):
        self.vih = self.val_in_hour(t)
        self.vid = self.val_in_day(t)

    @error_logger
    def save(self):
        if self.ischange():
            cur = sql.cursor()
            cur.execute("""
                        UPDATE daqd_sensors 
                        SET count_value=? 
                        WHERE id=?
                        """, (str(self.value), str(self.id)))
            sql.commit()
            self.save_value = self.value
            logging.debug('counter: save ' + str(self.id) + ' sensor counter value: ' + str(self.value))

    def reset(self):
        self.value = 0

    @error_logger
    def update(self, value=0):
        self.value = float(value)

    def ischange(self):
        if self.value != self.save_value:
            return True

    def join(self):
        return str(self.value) + ' ' + str(self.vih) + ' ' + str(self.vid)

class Sensor:
    @error_logger
    def __init__(self, id_, interface_id, enabled, count, action_id):
        self.id = id_
        self.interface_id = interface_id
        self.enabled = enabled
        self.action_id=action_id
        cur = sql.cursor()
        self.command_list = ['enable', 'disable']
        if int(count):
            cur.execute("""
                        SELECT count_value, count_step 
                        FROM daqd_sensors 
                        WHERE id=?
                        """, str(self.id))
            value, step = cur.fetchone()
            self.counter = Counter(value, step, self.id)
            self.save = self.counter.save
            self.count = self.counter.join
            self.reset = self.counter.reset
            self.update = self.counter.update
            self.command_list.extend(['count', 'reset', 'save', 'update'])
        if self.isgpio():
            cur.execute("""
                        SELECT t.gpio_number,t.direction,t.active,e.value 
                        FROM daqd_interface_gpio t, daqd_gpio_edge e 
                        WHERE t.sensor_id=? AND t.edge_id=e.id
                        """, str(self.id))
            self.gpio = dict()
            self.gpio['count'] = count
            self.gpio['num'], self.gpio['dir'], self.gpio['act'], self.gpio['edge'] = cur.fetchone()
            self.starting = False
            self.command_list.extend(['start', 'stop'])

    @error_logger
    def enable(self):
        if not self.enabled:
            cur.execute("""
                        UPDATE daqd_sensors 
                        SET enabled=1 
                        WHERE id=?
                        """, str(self.id))
            sql.commit()
            self.enabled = 1

    @error_logger
    def disable(self):
        if self.enabled:
            cur.execute("""
                        UPDATE daqd_sensors 
                        SET enabled=0 
                        WHERE id=?
                        """, str(self.id))
            sql.commit()
            self.enabled = 0

    def start(self):
        if not self.starting:
            if self.enabled:
                self.thread = GpioComThread(self.id, self.gpio['num'], self.gpio['dir'], self.gpio['act'],
                                            self.gpio['edge'], self.gpio['count'])
                self.thread.start()
                self.starting = True
            else:
                logging.info('sensor ' + str(self.id) + ' disabled')
        else:
            logging.info('sensor ' + str(self.id) + ' thread already start')

    def stop(self):
        if self.starting:
            self.thread.stop()
            self.starting = False
        else:
            logging.info('sensor ' + str(self.id) + ' not starting')

    def isgpio(self):
        if int(self.interface_id) == 2:
            return True
        return False

class RfModule(Cc1101):
    def __init__(self, id_, config, rx):
        self.id = id_
        Cc1101.__init__(self, self.id)
        self.rx = rx
        self.config = config
        #self.thread = Cc1101ComThread(self.id)
        self.init(self.config)
        self.starting = False

    def start(self):
        if not self.starting:
            #Cc1101.__init__(self, self.id)
            #self.init(self.config)
            self.thread = Cc1101ComThread(self.id)
            self.thread.start()
            self.starting = True
        else:
            logging.info('cc1101(' + str(self.id) + ') thread already start')

    def stop(self):
        if self.starting:
            self.thread.stop()
            self.starting = False
        else:
            logging.info('cc1101(' + str(self.id) + ') not starting')

# Поток для очереди входящих(in) и исходящих(out) сообщений
class QueueThread(threading.Thread):
    def __init__(self, direction):
        super(QueueThread, self).__init__()
        self.running = True
        self.q = Queue.Queue()
        self.direction = direction

    def add(self, data, conn=False):
        self.q.put(data)
        self.conn = conn

    def stop(self):
        self.running = False

    def run(self):
        logging.critical('queue ' + self.direction + ': start')
        while self.running:
            try:
                value = self.q.get(block=True, timeout=1)
                if self.direction == 'out':
                    send2scada(value)
                elif self.direction == 'in':
                    exec_control(value, self.conn)
            except Queue.Empty:
                pass
        logging.critical('queue "' + self.direction + '": stop')
        if not self.q.empty():
            logging.warning('queue "' + self.direction + '": elements left in the queue')
            while not self.q.empty():
                logging.warning('queue "' + self.direction + '": element in queue: ' + self.q.get())
@error_logger
def exec_control(value, conn):

    def send(ans):
        try:
            conn.send(ans)
        except IOError, e:
            if e.errno == 32: #errno.EPIPE (Broken pipe)
                logging.error('daqd control: broken pipe')
                daemon.daqd_control.stop()
                time.sleep(1)
                daemon.daqd_control.start()

    def valid(value):
        data = value.split()
        try:
            data[0] = int(data[0])
        except ValueError:
            logging.error('daqd control: command format error')
            send('daqd control: command format error')
            return False
        if data.__len__() == 2:
            return data
        elif data.__len__() == 3:
            try:
                data[2] = float(data[2])
                return data
            except ValueError:
                logging.error('daqd control: command format error')
                send('daqd control: command format error')
                return False
        else:
            logging.error('daqd control: command format error')
            send('daqd control: command format error')
            return False

    # 100 это сс1101(0). 101 это cc1101(1)
    data = valid(value)
    if data:
        if data[0] in [100, 101]:
            if (data[1] in Cc1101.command_list) or (data[1] in ['stop', 'start']):
                command = getattr(rf_modules[data[0] % 100], data[1])
                answer = command()
                send(str(answer))
                logging.debug('daqd control: sensor ' + str(data[0]) + ' command: "' + data[1] + '"')
            else:
                logging.error('daqd control: sensor ' + str(data[0]) + ' command "' + data[1] + '" not found')
                send('daqd control: sensor ' + str(data[0]) + ' command "' + data[1] + '" not found')
        elif data[0] in sensors.keys():
            if data[1] in sensors[data[0]].command_list:
                command = getattr(sensors[data[0]], data[1])
                if data.__len__() == 2:
                    answer = command()
                elif data.__len__() == 3:
                    answer = command(data[2])
                send(str(answer))
                logging.debug('daqd control: sensor ' + str(data[0]) + ' command: "' + data[1] + '"')
            else:
                logging.error('daqd control: sensor ' + str(data[0]) + ' command "' + data[1] + '" not found')
                send('daqd control: sensor ' + str(data[0]) + ' command "' + data[1] + '" not found')
        else:
            logging.error('daqd control: sensor ' + str(data[0]) + ' not found')
            send('daqd control: sensor ' + str(data[0]) + ' not found')

@error_logger
def packet_identefy(packet):
    for s in rf_sensors:
        if re.match(rf_sensors[s]['message'],packet['message']):
            packet['sensor_id'] = s
            #location = rf_sensors[s]['value_location'].split(':')
            #packet['value'] = packet['message'][int(location[0]):int(location[1])]
            packet['value'] = re.search(rf_sensors[s]['value_location'],packet['message']).group(1)
            packet['action_id'] = rf_sensors[s]['action_id']
            return packet
    return False

@error_logger
def send2scada(packet):
    def xml_str(packet):
        return '<?xml version="1.0" encoding="utf-8"?>\n<PACKAGE>\n<SENSOR sensor_id="' + str(
            packet['sensor_id']) + '" value="' + str(packet['value']) + '" action_id="' + str(packet['action_id']) + '"/>\n</PACKAGE>'

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(SOCKFILE_OUT)
    sock.send(xml_str(packet))
    sock.recv(sock_buffer)
    sock.close()
    logging.critical('send to OpenSCADA: s-' + str(packet['sensor_id']) + ' v-' + str(packet['value']) + ' a-' + str(packet['action_id']))

class DaqdControlThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        logging.critical('daqd control: start')
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            os.remove(SOCKFILE)
        except OSError:
            pass
        sock.bind(SOCKFILE)
        sock.listen(1)
        while self.running:
            try:
                conn, addr = sock.accept()
                conn.settimeout(1)
            except socket.timeout:
                # logging.debug('daqd control: socket timeout')
                continue
            while self.running:
                try:
                    data = conn.recv(sock_buffer)
                except socket.timeout:
                    continue
                else:
                    if data:
                        logging.debug('daqd control: receive: ' + data)
                        # t = time.ctime()
                        # rez = ''
                        daemon.queue_in.add(data, conn)
                        logging.debug('daqd control: "' + data + '" in queue')
        logging.critical('daqd control: stop')

# Прослушивание частоты настроенной на модуле CC1101
# все что получено(data)(определяется функциями в зависимости
# от настройки CC1101) отсылается в очередь на передачу
# в сокет для передачи в Openscada.
class Cc1101ComThread(threading.Thread):
    def __init__(self, id_):
        threading.Thread.__init__(self)
        self.running = True
        self.id = id_

    def stop(self):
        self.running = False

    def run(self):
        logging.critical('cc1101(' + str(self.id) + ') communication: start')
        try:
            cur.execute("""
                     SELECT sensor_id, message, type, value_location, action_id
                     FROM daqd_interface_cc1101, daqd_sensors
                     WHERE sensor_id=id
                     """)
            for row in cur:
                rf_sensors[row[0]]={'message':row[1], 'type':row[2], 'value_location':row[3], 'action_id':row[4]}
            rf_modules[self.id].flush_rx()
            rf_modules[self.id].srx()
            while self.running:
                if not rf_modules[self.id].GDO0State:
                    logging.debug('gdo_open')
                    rf_modules[self.id].gdo0_open()
                logging.debug('cc1101(' + str(self.id) + ') communication: before poll')
                events = rf_modules[self.id].epoll_obj.poll(1)
                for fileno, event in events:
                    if fileno == rf_modules[self.id].GDO0File.fileno():
                        rssi=rf_modules[self.id].rssi
                        packet = rf_modules[self.id].read_buffer()
                        if packet:
                            packet['rssi']=rssi
                            logging.critical('cc1101(' + str(self.id) + ') communication: receive: ' + packet['type'] +':'+packet['message']+':'+str(packet['rssi']))
                            #if packet['message']: daemon.queue_out.add(packet_identefy(packet))
                            id_packet=packet_identefy(packet)
                            if id_packet: daemon.queue_out.add(id_packet)
                            else: logging.critical('unknown packet')
                            rf_modules[self.id].flush_rx()
                            rf_modules[self.id].srx()
                        else:
                            logging.error('cc1101(' + str(self.id) + ') communication: receive error')
                if rf_modules[self.id].marcstate() != 'RX':
                    logging.error('cc1101(' + str(self.id) + ') communication: flush with out read buffer')
                    rf_modules[self.id].flush_rx()
                    rf_modules[self.id].srx()
        except Exception, e:
            logging.error('cc1101(' + str(self.id) + ') communication: ', exc_info=True)
        finally:
            rf_modules[self.id].starting = False
            rf_modules[self.id].reset()
            logging.critical('cc1101(' + str(self.id) + ') communication: stop')


# Для каждого включенного датчика gpio
# запускается свой поток
class GpioComThread(threading.Thread):
    def __init__(self, id_, gpio, dir_, act, edge, counter):
        threading.Thread.__init__(self)
        self.running = True
        self.id = id_
        self.gpio = gpio
        self.dir = dir_
        self.act = act
        self.edge = edge
        self.counter = counter
        fagpio.export(gpio)
        logging.critical('gpio communication: export ' + str(gpio) + ' gpio')

    def stop(self):
        if self.counter and sensors[self.id].counter.ischange():
            sensors[self.id].counter.save()
        self.running = False

    def run(self):
        try:
            gpio = fagpio.gpio(self.gpio)
            gpio.edge = self.edge
            gpio.direction = self.dir
            gpio.active = self.act
            s_id = str(self.id)
            s_gpio = str(self.gpio)
            logging.critical('gpio communication: start sensor:' + s_id + ' gpio:' + s_gpio + ' \
edge:' + self.edge + ' counter:' + str(self.counter))
            # Если включен счетчик на датчике
            if self.counter:
                t = time.time()
                i = 0
                while self.running:
                    events = gpio.epoll_obj.poll(1)
                    # logging.debug('gpio communication: sensor id ' + s_id + ': no event')
                    for fileno, event in events:
                        if fileno == gpio.fvalue.fileno():
                            now = time.time()
                            diff = round(now - t, 2)
                            t = now
                            if i > 1:
                                sensors[self.id].counter.inc()
                                sensors[self.id].counter.period(diff)
                                logging.debug('gpio communication: sensor ' + s_id + ' value:' + str(
                                    sensors[self.id].counter.value) + ' ' + str(diff) + ' ' + str(
                                    sensors[self.id].counter.vih) + ' ' + str(sensors[self.id].counter.vid))
                            else:
                                i += 1
                                logging.info('gpio communication: sensor ' + s_id + ' counter init..')
            else:
                while self.running:
                    events = gpio.epoll_obj.poll(1)
                    # logging.debug('gpio communication: sensor id ' + s_id + ': no event')
                    for fileno, event in events:
                        # logging.debug('gpio communication: event file:'+str(fileno)+' event:'+str(event)+' \
                        # file:'+str(gpio.fvalue.fileno()))
                        if fileno == gpio.fvalue.fileno():
                            # data=s_id+':'+str(gpio.value)
                            logging.debug('gpio communication: sensor ' + s_id + ' signal')
                            daemon.queue_out.add({'sensor_id':s_id,'value':1,'action_id':sensors[self.id].action_id})
        except Exception, e:
            logging.error('gpio communication: ', exc_info=True)
        finally:
            fagpio.unexport(self.gpio)
            sensors[self.id].starting = False
            #logging.critical('gpio communication: unexport ' + str(self.gpio) + ' gpio')
            logging.critical('gpio communication: stop sensor:' + s_id + ' gpio:' + s_gpio + ' \
edge:' + self.edge + ' counter:' + str(self.counter))


class Daqd(Daemon):
    @error_logger
    def run(self):
        self.queue_out = QueueThread('out')
        self.queue_out.start()
        self.queue_in = QueueThread('in')
        self.queue_in.start()
        self.daqd_control = DaqdControlThread()
        self.daqd_control.start()
        for s in sensors:
            if sensors[s].enabled and sensors[s].isgpio():
                sensors[s].start()
        for r in rf_modules:
            if rf_modules[r].rx:
                rf_modules[r].start()

def sigterm_handler(signal, frame):
    global sql
    logging.critical('catch SIGTERM')
    daemon.queue_out.stop()
    daemon.queue_in.stop()
    daemon.daqd_control.stop()
    for s in sensors:
        if sensors[s].isgpio() and sensors[s].starting:
            sensors[s].stop()
    for r in rf_modules:
        if rf_modules[r].rx:
            rf_modules[r].stop()
            time.sleep(1)
        rf_modules[r].close()
    sql.close()
    sys.exit(0)

if __name__ == "__main__":
    daemon = Daqd(PIDFILE)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            print("Starting...")
            if isfile(DBFILE):
                sql = sqlite3.connect(DBFILE, check_same_thread=False)
            else:
                print(DBFILE + ' file is not exist')
                logging.error(DBFILE + ' file is not exist')
                raise
            logging.basicConfig(filename=LOGFILE, level=logging.INFO, format=FORMAT)
            logging.critical('Starting...')
            signal.signal(signal.SIGTERM, sigterm_handler)
            cur = sql.cursor()
            sensors = dict()
            cur.execute("""
                        SELECT id, interface_id, enabled, counter, action_id 
                        FROM daqd_sensors
                        """)
            for row in cur:
                sensors[row[0]] = Sensor(row[0], row[1], row[2], row[3], row[4])
            rf_modules = dict()
            cur.execute("""
                        SELECT id,config,rx 
                        FROM daqd_config_cc1101
                        """)
            for row in cur:
                rf_modules[row[0]] = RfModule(row[0], row[1], row[2])
            rf_sensors = {}
            daemon.start()
            # Основной поток должен остоваться, чтобы ловить сигнал SIGTERM
            while True:
                time.sleep(1)
        elif 'stop' == sys.argv[1]:
            print("Stop...")
            logging.basicConfig(filename=LOGFILE, level=logging.INFO, format=FORMAT)
            logging.critical('Stop...')
            try:
                os.remove(SOCKFILE)
            except OSError:
                pass
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            print("Restart...")
            logging.basicConfig(filename=LOGFILE, level=logging.INFO, format=FORMAT)
            daemon.restart()
            logging.critical('Restart...')
        elif 'status' == sys.argv[1]:
            try:
                pf = file(PIDFILE, 'r')
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
            #    else:
            #        print("usage: %s start|stop|restart|status" % sys.argv[0])
            #        sys.exit(2)
    if len(sys.argv) == 3:
        if 'start' == sys.argv[1] and 'debug' == sys.argv[2]:
            print("Starting...debug")
            logging.basicConfig(filename=LOGFILE, level=logging.DEBUG, format=FORMAT)
            logging.critical('Starting...')
            signal.signal(signal.SIGTERM, sigterm_handler)
            cur = sql.cursor()
            sensors = dict()
            cur.execute("""
                        SELECT id, interface_id, enabled, counter 
                        FROM daqd_sensors
                        """)
            for row in cur:
                sensors[row[0]] = Sensor(row[0], row[1], row[2], row[3])
            rf_modules = dict()
            cur.execute("""
                        SELECT id,config,rx 
                        FROM daqd_config_cc1101
                        """)
            for row in cur:
                rf_modules[row[0]] = RfModule(row[0], row[1], row[2])
            daemon.start()
            # Основной поток должен остоваться, чтобы ловить сигнал SIGTERM
            while True:
                time.sleep(1)
        else:
            print("usage: %s start|start debug|stop|restart|status" % sys.argv[0])
        sys.exit(2)

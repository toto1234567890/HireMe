#!/usr/bin/env python
# coding:utf-8
#FIXME problem with Processes on stop with send_msg_in_now ... at first run or with MAIN_BEAT_QUEUE < 0.01

from os import name as osName 
from time import sleep
from collections import deque
from uuid import uuid4
from threading import Thread
from multiprocessing import Pipe, set_start_method, Process


# to prevent "context has already been set"
try:
    if osName != 'nt':
        set_start_method("fork")
    else: 
        set_start_method("spawn")
except:
    pass

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.Database.database import Database
from common.TeleRemote.tele_command import Telecommand
from common.ThreadQs.routing_rules import starQ_route_msg, LostQmsg
from common.Helpers.helpers import Singleton, threadIt, getOrDefault
from common.Helpers.network_helpers import SafePipe

DEFAULT_WAIT_RATIO = 3 # multiply by heart beat
DEFAULT_MESSAGE_QUEUE_BEAT= 0.01
DEFAULT_RETRY_PERIOD = 1

class Qmsg:
    def __init__(self, msg, frome, too, ackw=None, priority=False):
        self.id = uuid4()
        self.msg = msg
        self.frome = frome
        self.too = too
        self.ackw = ackw
        self.priority = priority

#@singleton
class StarQs(Telecommand, metaclass=Singleton):
    Name = "StarQs"
    QueuesIn = {}
    QueuesOut = {}
    Subscribers = {}
    Route_msg = starQ_route_msg
    def __init__(self, logger:MyLogger, config:Config, name:str=None):
        if not name is None:
            self.Name = name
        self.logger = logger
        self.config = config
        self.main_queue_beat = getOrDefault(self.config.MAIN_QUEUE_BEAT, DEFAULT_MESSAGE_QUEUE_BEAT)
        self.run = True ; self.StarQlocked = False
        self.SafeQ = None ; self.state = '#N/A'
        self.TeleBufQ = deque()
        Thread(target=self.TeleCommand).start()
        Thread(target=self.starQ_msg_in).start()

    def starte(self):
        if not self.run:
            Thread(target=self.starQ_msg_in).start()
            self.run = True
            self.StarQlocked = False
            return False
        else:
            self.logger.error("StarQs : received 'start' message but it's already running !")
            return True

    def append_paired(self, queueName:str, subscriber):
        self.QueuesOut[queueName] = self.__dict__[queueName+"_out"] = deque()
        self.QueuesIn[queueName] = self.__dict__[queueName+"_in"] = deque()
        self.Subscribers[queueName] = subscriber
        #subscriber.logger = self.logger
        self.SafeQ = self.QueuesIn.copy()
        self.logger.info("StarQs : '{0}' has subscribe to Threads Queues '{1}' !".format(queueName, self.Name))
        return self.__dict__[queueName+"_in"], self.__dict__[queueName+"_out"], self.run, self._send_priority_msg, self.main_queue_beat

    def remove_linked(self, name):
        del self.QueuesOut[name]
        del self.QueuesIn[name]
        del self.Subscribers[name]

    def _send_priority_msg(self, cur_msg):
        self.StarQlocked = True
        (self.Subscribers[cur_msg.too]).locked = True
        self.QueuesOut[cur_msg.too].appendleft(cur_msg)
        (self.Subscribers[cur_msg.too]).locked = False
        self.StarQlocked = False

    def starQ_msg_in(self):
        try:
            self.SafeQ = self.QueuesIn.copy()
            while self.run:
                for key, Que in self.SafeQ.items():
                    if len(Que) > 0:
                        if self.StarQlocked:
                            while True:
                                self.logger.info("StarQs : '{0}' received lock signal, waiting '{1}s' before reading 'in' queue...".format(self.Name, self.main_queue_beat))
                                sleep(self.main_queue_beat)
                                if not self.run:
                                    exit(0)
                                if not self.StarQlocked:
                                    break
                        try :
                            cur_msg = Que.popleft()
                            self.logger.info("StarQs : message id '{0}' received from '{1}' to '{2}'".format(cur_msg.id, key, cur_msg.too))
                            self.Route_msg(cur_msg, self.QueuesOut)#, logger=self.logger)
                        except Exception as e:
                            self.logger.critical("StarQs : critical error while trying to get message id '{0}' from Threads Queues '{1}' : {2}".format(getOrDefault(cur_msg.id, "#None"), Que, e))
                            self.SafeQ = self.QueuesIn.copy()
                            LostQmsg(cur_msg)
                            pass
                    sleep(self.main_queue_beat)
        except Exception as e:
            self.logger.critical("StarQs : critical error in main loop '{0}'".format(e))
            exit(1)

        self.logger.info("StarQs : main queue has been stopped.")
        self.logger.ends_srv_notif_loop()
        sleep(self.main_queue_beat)
        return

##############################################################################################################################################################################################

class SubsQ:
    router_run = None
    logger = None
    def __init__(self, name, mainQueue, default_recv:str=None, ChildProc=None, **kwargs):
        self.__dict__[name+"_out"], self.__dict__[name+"_in"], self.router_run, self._send_priority_msg, self.main_queue_beat = mainQueue.append_paired(name, self) 
        self.waite = self.main_queue_beat * DEFAULT_WAIT_RATIO
        self.name = name    ;   self.logger = mainQueue.logger
        self.default_recv = default_recv
        self.run = True ; self.locked = False ; self.ends = False; self.process = False  
        Thread(target=self.recv_msg_in).start()

    # Child Process
        if not ChildProc is None: 
            self.process = True
            self.parent = None
            self.intBufQ = deque() ; self.extBufQ = deque() 
            self.initProc(ChildProc, **kwargs)
    
    def initProc(self, ChildProc, kwargs):
        parent, child = Pipe()
        self.parent = SafePipe(parent)
        Thread(target=self.treat_ext_msg).start()
        Thread(target=self.treat_int_msg).start()
        kwargs["name"] = self.name
        ChildProc(child=child, kwargs=kwargs)

    # method replaced in child, if not child is a process
    def treat_int_msg(self, cur_msg=None):
        if self.process:
            while True:
                if len(self.intBufQ) > 0:
                    cur_msg = self.intBufQ[-1]
                    if cur_msg == '0':
                        self.parent.send_data(cur_msg)
                        break
                    self.parent.send_data(cur_msg)
                    self.intBufQ.popleft() 
                    sleep(self.main_queue_beat/4)
              
    # method replaced in child, if not child is a process
    def treat_ext_msg(self, cur_msg=None):
        if self.process:
            while True:
                data = self.parent.receive_data()
                try:  
                    if data != '0':
                        if isinstance(data, Qmsg):
                            self.extBufQ.append(data)
                            while len(self.extBufQ) > 0:
                                data = self.extBufQ[-1]
                                self.send_msg_in(data.msg, data.too, data.ackw)
                                self.extBufQ.popleft()
                        else:
                            self.logger.error("Thread '{0}' received unknown message from Process '{0}' : {1}".format(self.name, data))
                            LostQmsg(cur_msg)
                    else:
                        self.logger.info("Thread '{0}' received unsubscribe message from Process !".format(self.name))
                        self.parent.conn.close()       
                        self.run = False
                        self.locked = False
                        break
                    if not data:
                        # dead parent socket
                        self.logger.error("BrokenPipe parent Thread '{0}'".format(self.Name))
                        self.parent.conn.close()
                        break  
                except Exception as e:
                    self.logger.critical("Critical error while trying to get message id '{0}' from Process '{1}'".format(self.name, e))
                    LostQmsg(data)
                    pass             

    # Child Thread
    def unSubs(self): 
        self.locked = True
        if self.process:
            self.intBufQ.append('0')
        else:
            self.run = False
            self.locked = False

    def send_msg_in_now(self, msg, too:str=None, ackw:bool=False):
        if too is None : too = self.default_recv
        msg = Qmsg(msg, self.name, too, ackw)
        self.logger.info("Thread '{0}' sending priority message id '{1}' to '{2}'".format(self.name, msg.id, msg.too))
        self._send_priority_msg(msg)

    @threadIt
    def send_msg_in(self, msg, too:str=None, ackw:bool=False):
        if self.locked:
            while True:
                self.logger.info("Thread '{0}' received lock signal, waiting '{1}s' before reading 'in' queue...".format(self.name, self.waite))
                sleep(self.waite)
                if not self.run:
                    exit(0)
                if not self.locked:
                    break
        if not self.run:
            exit(0)            
        if too is None : too = self.default_recv
        msg = Qmsg(msg, self.name, too, ackw)
        (self.__dict__[self.name+"_out"]).append(msg)
        self.logger.info("Thread '{0}' sent message id '{1}' to '{2}'".format(self.name, msg.id, msg.too))

    def recv_msg_in(self):
        Que = self.__dict__[self.name+"_in"]
        while self.run and self.router_run:
            sleep(self.main_queue_beat)
            if len(Que) > 0:
                if not self.locked:
                    try :
                        cur_msg = Que.popleft()
                        self.logger.info("Thread '{0}' received message id '{1}' from '{2}'".format(self.name, cur_msg.id, cur_msg.frome))
                        if cur_msg.ackw:
                            self.logger.info("Thread '{0}' send back acknow id '{1}' to '{2}'...".format(self.name, cur_msg.id, cur_msg.frome))
                            self.send_msg_in(Qmsg(msg=cur_msg.id, frome=self.name, too=cur_msg.frome))
                        if self.process:
                            self.intBufQ.append(cur_msg)
                        else:
                            self.treat_int_msg(cur_msg)
                    except Exception as e:
                        self.logger.critical("Critical error while trying to get message id '{0}' from Threads Queues, on Thread {1} : {2}".format(getOrDefault(cur_msg.id, "#None"), self.name, e))
                        LostQmsg(cur_msg)
                        pass 
                else:
                    while self.locked:
                        self.logger.info("Thread '{0}' received lock signal, waiting '{1}s' before reading 'in' queue...".format(self.name, self.waite))
                        sleep(self.waite)           
        
        if self.run and not self.router_run:
            self.logger.critical("{0} The Threads Queues is stopped !!! Stopping Thread '{0}' immediately... Please check.".format(self.name))
            exit(1)
        self.logger.info("Thread '{0}' has unsubscribed to Threads Queues !".format(self.name))
        self.ends = True

##############################################################################################################################################################################################

class ProcessAdapter(Process):
        def __init__(self, child=None, kwargs=None):
            self.child = SafePipe(child)
            self.Name = kwargs["name"]
            self.config = kwargs["config"]
            self.logger = kwargs["logger"]
            super(Process, self).__init__()
            self.start()
            
        def run(self):
            x = 0
            while True:
                try:
                    data = self.child.receive_data()
                    if data != '0':
                        if isinstance(data, Qmsg):
                            self.logger.info("Process '{0}' received message id '{1}' from '{2}'".format(self.Name, data.id, data.frome))
                            msg = Qmsg(msg="{0} => {1}".format(data.msg, x), frome=self.Name, too="SwissQ", ackw=None, priority=None)
                            self.child.send_data(msg)
                            self.logger.info("Process '{0}' sent message id '{1}' to '{2}'".format(self.Name, msg.msg, msg.too))
                            x += 1
                        else:
                            self.logger.error("Process '{0}' received unknown message : {1}".format(self.Name, data))
                    else:
                        # Normal end
                        self.logger.info("Process '{0}' received 'unsubscribe' signal !".format(self.Name))
                        self.child.send_data('0')
                        self.child.conn.close()
                        break   
                    if not data:
                        # dead parent socket
                        self.logger.error("BrokenPipe child Process '{0}'".format(self.Name))
                        self.child.conn.close()
                        break                    
                except Exception as e:
                    self.logger.critical("Critical error while trying to get message from Threads Queues on Child Process '{0}' : {1}".format(self.Name, e))
                    try:
                        LostQmsg(data)
                    except:
                        pass


#================================================================
if __name__ == "__main__":
    # init
    config = Config(name="thread_Qs")
    logger = MyLogger("thread_Qs", config)
    dblog = Database(logger, config)

    # late binding
    logger.DBlog = dblog

    # main highlevel quote interface
    tradeQueues = StarQs(logger, config)

    def_kwargs={"config":config, "logger":logger}

    SwissQ = SubsQ("SwissQ", tradeQueues, default_recv="SwissquoteAPI")
    Swissquote = SubsQ("SwissquoteAPI", tradeQueues, default_recv="SwissQ")

    SwissQT = SubsQ(name="SwissQT", mainQueue=tradeQueues, default_recv="SwissquoteAPIT")
    SwissquoteT = SubsQ("SwissquoteAPIT", tradeQueues, default_recv="SwissQT")
    # 
    #def_kwargs = {"logger":logger, "config":config}
    SwissQT.send_msg_in("test1", ackw=True)
    #toto = SubsQ("toto", tradeQueues, default_recv="titi", ChildProc=ProcessAdapter, kwargs=def_kwargs)
    #titi = SubsQ("titi", tradeQueues, default_recv="toto", ChildProc=ProcessAdapter, kwargs=def_kwargs)
    Swissquote.send_msg_in("charge")
    #SwissQ.send_msg_in_now("????priority message!!!")
    import time
    t = time.perf_counter()
    x = 1
    while True:
        for x in range(10000):
            if tradeQueues.run:
                Swissquote.send_msg_in("charge")
                SwissQ.send_msg_in("????priority message!!!") 
                Swissquote.send_msg_in("charge") 
                Swissquote.send_msg_in("charge") 
                #titi.send_msg_in("coucou")
                SwissQT.send_msg_in("test1") 
                #toto.send_msg_in("coucou")
            if x == 8000:
                break
        break


    t1 = time.perf_counter()
 
    print("Elapsed time: {0}".format(t1-t))
    #tradeQueues.stop()
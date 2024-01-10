#!/usr/bin/env python
# coding:utf-8


import threading
from time import sleep
from collections import deque

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.ThreadQs.thread_Qs import StarQs, SubsQ, Qmsg
from common.Helpers.network_helpers import MySocket, MyStickySocket


DEFAULT_RETRY_PERIOD = 1
DEFAULT_SLEEP_RATIO = 100
xSocketSender = deque()

###########################################################################################################

class TCPFeeder:
    Name="TCP Feeder"
    def __init__(self, logger, config:Config, name:str=None, default_recv:str=None, FeederReceiver="ARBITRE"):
        if not name is None:
            self.Name = name.capitalize()
        self.logger = logger
        self.config = config
        self.default_recv = default_recv
        self.main_queue_beat = config.MAIN_QUEUE_BEAT
        
        self.logger.info("{0} : TCP Feeder is starting.. .  . ".format(self.Name)) 
        self.linkFeeder(FeederReceiver)

    def linkFeeder(self, FeederReceiver):
        for analystName, conf in self.config.parser.items():
            if analystName.endswith(FeederReceiver):
                try:
                    server="" ; port="" ; mem_port=""
                    prefixe = analystName.split('_')[0]
                    for name_sec, conf_sec in conf.items(): 
                        if name_sec == "{0}_DB_SERVER".format(prefixe):
                            server = conf_sec
                        if name_sec == "{0}_DB_PORT".format(prefixe):
                            port = conf_sec
                        #if name_sec == "{0}_DB_MEM_PORT".format(prefixe):
                        #    mem_port = conf_sec
                        if server != "" and port != "":
                            threading.Thread(target=self.create_MySocket, args=(analystName, server, port,)).start()
                            self.logger.info("{0} : Data feeding started for section '{1}' !".format(self.Name, analystName.capitalize()))
                            break
                        #if server != "" and mem_port != "":
                        #    threading.Thread(target=self.create_MySocket, args=("{0}_MEM".format(analystName), server, mem_port,)).start()
                        #if port != "" and server != "": #and mem_port != ""
                        #    break
                    if port == "" and server == "": # and mem_port == ""
                        if server == "" or port == "":
                            self.logger.info("{0} : missing address:port for section '{1}', this section will not be load as a feeder Receiver...".format(self.Name, analystName))
                        #if server == "" or mem_port == "":
                        #    self.logger.info("{0} : missing address:mem_port for section '{1}', this section will not be load as a feeder Receiver...".format(self.Name, analystName))
                except Exception as e:
                    self.logger.error("{0} : error while trying to load address:(port|mem_port) for Analyst '{1}', please check config file : {2}".format(self.Name, analystName, e))
                    continue

    @MyStickySocket(delay=10, backoff=1, tries=-1) 
    @MyStickySocket(delay=DEFAULT_RETRY_PERIOD, backoff=1, tries=10, jitter=1)
    def create_MySocket(self, analystName:str, server:str, port):
        with MySocket(name=analystName, server=server, port=int(port)) as FeederSocket:
            FeederPort = FeederSocket.conn.getsockname()[1] 
            if server == "127.0.0.1" or server.lower() == "localhost":
                self.logger.info("{0} : connection established without encryption to '{1}' destport '{2}' srcport '{3}'".format(self.Name, server, port, FeederPort))
            else:
                self.logger.info("{0} : connection established with encryption '{1}' to '{2}' destport '{3}' srcport '{4}'".format(self.Name, FeederSocket.conn.version(), server, port, FeederPort))
            
            FeederSocket.send_data("{0}:{1}:{2}".format(self.Name, server, FeederPort))
            global xSocketSender ; xSocketSender.append(FeederSocket)
            sockIndex = xSocketSender.index(FeederSocket)
            
            while xSocketSender[sockIndex] != None:
                sleep(self.main_queue_beat*DEFAULT_SLEEP_RATIO)
            xSocketSender.remove(FeederSocket)
            
    # send msg to socket databases
    def TCP_feed(self, msg):
        global xSocketSender
        for sock in range(len(xSocketSender)):
            try:
                curr_sock = xSocketSender[sock]
                if type(msg) == Qmsg:
                    curr_sock.send_data(msg.msg)
                    self.logger.debug("{0} : message id '{1}' has been sent to '{2}'".format(self.Name, msg.id, curr_sock.Name))
                else:
                    curr_sock.send_data(msg)
                    self.logger.debug("{0} : message type '{1}' has been sent to '{2}'".format(self.Name, type(msg), curr_sock.Name))
            except Exception as e:
                self.logger.error("{0} : error while trying to send message to '{1}' : {2}".format(self.Name, curr_sock.Name, e))
                continue

    # send Async msg to socket databases
    async def TCP_asyncFeed(self, msg):
        global xSocketSender
        for sock in range(len(xSocketSender)):
            try:
                curr_sock = xSocketSender[sock]
                if type(msg) == Qmsg:
                    curr_sock.send_data(msg.msg)
                    self.logger.asyncDebug("{0} : message id '{1}' has been sent to '{2}'".format(self.Name, msg.id, curr_sock.Name))
                else:
                    curr_sock.send_data(msg)
                    self.logger.asyncDebug("{0} : message type '{1}' has been sent to '{2}'".format(self.Name, type(msg), curr_sock.Name))
            except Exception as e:
                self.logger.error("{0} : error while trying to send message to '{1}' : {2}".format(self.Name, curr_sock.Name, e))
                continue

###########################################################################################################

class TCPFeederSubsQ(SubsQ):
    Name="TCP Feeder SubsQ"
    def __init__(self, name, mainQueue:StarQs, logger:MyLogger, config:Config, default_recv:str=None, FeederReceiver="ARBITRE", ChildProc=None, **kwargs):
        if not name is None:
            self.Name = name.capitalize()
        self.logger = logger
        self.config = config
        self.default_recv = default_recv

        self.logger.info("{0} : TCP Feeder is starting.. .  . ".format(self.Name))
        SubsQ.__init__(self, name=self.Name, mainQueue=mainQueue, default_recv=default_recv, ChildProc=ChildProc, **kwargs)
        self.linkFeeder(FeederReceiver)

    def linkFeeder(self, FeederReceiver):
        for analystName, conf in self.config.parser.items():
            if analystName.endswith(FeederReceiver):
                try:
                    server="" ; port="" ; mem_port=""
                    prefixe = analystName.split('_')[0]
                    for name_sec, conf_sec in conf.items(): 
                        if name_sec == "{0}_DB_SERVER".format(prefixe):
                            server = conf_sec
                        if name_sec == "{0}_DB_PORT".format(prefixe):
                            port = conf_sec
                        #if name_sec == "{0}_DB_MEM_PORT".format(prefixe):
                        #    mem_port = conf_sec
                        if server != "" and port != "":
                            threading.Thread(target=self.create_MySocket, args=(analystName, server, port,)).start()
                        #if server != "" and mem_port != "":
                        #    threading.Thread(target=self.create_MySocket, args=("{0}_MEM".format(analystName), server, mem_port,)).start()
                        if port != "" and server != "": #and mem_port != ""
                            break
                    if port == "" and server == "": # and mem_port == ""
                        if server == "" or port == "":
                            self.logger.info("{0} : missing address:port for section '{1}', this section will not be load as a feeder Receiver...".format(self.Name, analystName))
                        #if server == "" or mem_port == "":
                        #    self.logger.info("{0} : missing address:mem_port for section '{1}', this section will not be load as a feeder Receiver...".format(self.Name, analystName))
                except Exception as e:
                    self.logger.error("{0} : error while trying to load address:(port|mem_port) for Analyst '{1}', please check config file...".format(self.Name, analystName))
                    continue

    @MyStickySocket(delay=10, backoff=1, tries=-1) 
    @MyStickySocket(delay=DEFAULT_RETRY_PERIOD, backoff=1, tries=10, jitter=1)
    def create_MySocket(self, name:str, server:str, port:str):
        with MySocket(name=name, server=server, port=int(port)) as FeederSocket:
            FeederPort = FeederSocket.conn.getsockname()[1] 
            if server == "127.0.0.1" or server.lower() == "localhost":
                self.logger.info("{0} : connection established without encryption to '{1}' destport '{2}' srcport '{3}'".format(self.Name, server, port, FeederPort))
            else:
                self.logger.info("{0} : connection established with encryption '{1}' to '{2}' destport '{3}' srcport '{4}'".format(self.Name, FeederSocket.conn.version(), server, port, FeederPort))
            FeederSocket.send_data("{0}:{1}:{2}".format(self.Name, server, FeederPort))

            global xSocketSender ; xSocketSender.append(FeederSocket)
            sockIndex = xSocketSender.index(FeederSocket)
            while xSocketSender[sockIndex] != None:
                sleep(self.main_queue_beat*DEFAULT_SLEEP_RATIO)
            xSocketSender.remove(FeederSocket)

    def treat_int_msg(self, cur_msg):
        self.TCP_feed(cur_msg)

    def TCP_feed(self, msg):
        global xSocketSender
        for sock in range(len(xSocketSender)):
            try:
                curr_sock = xSocketSender[sock]
                if type(msg) == Qmsg:
                    curr_sock.send_data(msg.msg)
                    self.logger.info("{0} : message id '{1}' has been sent to '{2}'".format(self.Name, msg.id, curr_sock.Name))
                else:
                    curr_sock.send_data(msg)
                    self.logger.info("{0} : message type '{1}' has been sent to '{2}'".format(self.Name, type(msg), curr_sock.Name))
            except Exception as e:
                self.logger.error("{0} : error while trying to send message to '{1}' : {2}".format(self.Name, curr_sock.Name, e))
                continue


#================================================================
if __name__ == "__main__":
    from common.Helpers.helpers import init_logger
    # TCP_feeder subscriber
    name = "TCP Feeder"
    configStr="trading"
    config, logger = init_logger(name="{0}_ThreadQs".format(name), config=configStr)

    mainQueue = StarQs(logger=logger, config=config, name="{0}_streamQ".format(name))
    
    _newSubQsTCPFeder = TCPFeederSubsQ(name=name, mainQueue=mainQueue, logger=logger, config=config)
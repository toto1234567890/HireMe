#!/usr/bin/env python
# coding:utf-8

import socket
from time import sleep
from threading import Thread
from collections import deque
from retry import retry

# relative import
from sys import int_info, path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.Database.database import Database
from common.ThreadQs.thread_Qs import StarQs, SubsQ, Qmsg
from common.Helpers.network_helpers import SSL_client_context, SSL_test_context


#default
DEFAULT_RETRY_DELAY=1


class SslTunnel(SubsQ):
    Name = "SslTunnel" # to overload in child class
    def __init__(self, StarQ:StarQs, logger:MyLogger, config:Config, name:str=None, sandbox:bool=True, default_recv:str=None):

        if not name is None:
            self.Name = name 
        self.logger = logger
        self.config = config
        self.broker_config = dict(config.parser.items(self.Name.upper()))

        self.sandbox = sandbox    
        self.id = 0 ; self.que = deque()

        SubsQ.__init__(self, name=self.Name, mainQueue=StarQ, default_recv=default_recv)
        Thread(target=self.send_recv_msg_out).start()
        

    # overide in Child
    def treat_int_msg(self, cur_msg:Qmsg):
        # do something here if needed in child 
        self.que.append((cur_msg.msg).encode())

    # overide in Child not needed here => only for testing purposes
    def treat_ext_msg(self, cur_msg):
        self.send_msg_in(msg=cur_msg, too="Essai")

    @retry(delay=10, backoff=1, tries=-1) 
    @retry(delay=DEFAULT_RETRY_DELAY, backoff=1, tries=10, jitter=1)
    def send_recv_msg_out(self):
        if self.sandbox:
            context = SSL_test_context()
        else:
            context = SSL_client_context()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.SOL_TCP) as Sock:
            with context.wrap_socket(sock=Sock) as SslSock: 
                SslSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                SslSock.connect((self.broker_config["BR_URI"], int(self.broker_config["BR_PORT"])))
                self.id = SslSock.getsockname()[1] 
                self.logger.info("{0} : connection established with encryption : '{1}' to '{2}' destport '{3}' srcport '{4}'".format(self.Name, SslSock.version(), self.broker_config["BR_URI"], self.broker_config["BR_PORT"], self.id))
                
                while self.run and self.router_run:
                    if len(self.que) > 0:
                        msg = self.que.popleft()
                        SslSock.sendall(msg)
                        self.logger.info("{0} : message sent on SSL socket {1} to '{2}' : '{3}'".format(self.Name, self.id, self.broker_config["BR_URI"], msg))

                        data = SslSock.recv(1024)
                        if not data:
                            break
                        self.logger.info("{0} : received message from {1}:{2} : '{3}'".format(self.Name, self.broker_config["BR_URI"], self.broker_config["BR_PORT"], data))
                        self.treat_ext_msg(data.decode())

        self.logger.info("{0} : '{1}' connection to '{2}' closed on destport '{3}' srcport '{4}'".format(self.Name, SslSock.version(), self.broker_config["BR_URI"], self.broker_config["BR_PORT"], self.id))


#================================================================
if __name__ == "__main__":
    # does my env support SSL : TLS 1.1 ??
    # from urllib.request import urlopen
    # urlopen('https://www.howsmyssl.com/a/check').read()
    # print("TLS 1.1 supported...")

        # Wireshark :
    #	192.168.1.102	91.220.23.128	TLSv1.2	204	Certificate, Client Key Exchange, Change Cipher Spec, Encrypted Handshake Message
    #   91.220.23.128	192.168.1.102	TLSv1.2	117	Change Cipher Spec, Encrypted Handshake Message
    #	192.168.1.102	91.220.23.128	TCP	66	50515 → 21000 [ACK] Seq=785 Ack=4582 Win=130880 Len=0 TSval=1933594032 TSecr=909560684
    #   192.168.1.102	91.220.23.128	TCP	66	50515 → 21000 [FIN, ACK] Seq=785 Ack=4582 Win=131072 Len=0 TSval=1933594032 TSecr=909560684
    #	91.220.23.128	192.168.1.102	TLSv1.2	97	Encrypted Alert
    from common.Helpers.helpers import init_logger

    name = "Broker"
    configStr = "common"
    #config = "trading"

    config, logger = init_logger(name=name, config=configStr)

    StreamQ = StarQs(logger=logger, config=config, name="mainQ")

    SwissQuoteBinding = SslTunnel(StreamQ, logger, config, sandbox=True, name=name) # to manage self signed certificate...

    Subscriber = SubsQ("Essai", StreamQ, name)

    Subscriber.send_msg_in("coucou")
    from time import sleep
    sleep(1)
    while True:
        Subscriber.send_msg_in("hello")
        sleep(2)




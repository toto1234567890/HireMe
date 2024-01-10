#!/usr/bin/env python
# coding:utf-8

from os import getpid as osGetpid, getcwd as osGetcwd
from os.path import join as osPathjoin
from sys import argv
from uuid import uuid4
from collections import deque
from asyncio import run as asyncioRun, start_server as asyncioStart_server, \
                    Lock as asyncioLock, get_event_loop as asyncioGet_event_loop


# relative import
from sys import path;path.extend("..")
from common.ThreadQs.routing_rules import LostQmsg
from common.ThreadQs.aStarQ import aQSocket
from common.TeleRemote.tele_command import ATelecommand
from common.Helpers.helpers import Singleton, init_logger, getOrDefault
from common.Helpers.os_helpers import is_process_running, launch_monitoring_server, launch_watch_dog_server
from common.Helpers.network_helpers import SafeAsyncSocket, SSL_server_context, get_my_public_ip
#from trading.trading_helpers import refresh_trading_component


###########################################
# IP_INTERNAL is FIXED and HARD_CODED     #
# IP_EXTERNAL is FIXED and HARD_CODED     #
###########################################
# This variables are set in environ variable also
AMATRIXQ_IP_INTERNAL = '127.0.0.1'
AMATRIXQ_IP_EXTERNAL = '0.0.0.0'
# This variables are set in environ variable also

AMATRIXQ_NAME = "AMatrixQ"
DEFAULT_INTERNAL_PORT = 9001
DEFAULT_EXTERNAL_PORT = 9002


asyncLock = asyncioLock()

class Qmsg:
    def __init__(self, msg, frome, too, ackw=False, priority=False):
        self.id = uuid4()
        self.msg = msg
        self.frome = frome
        self.too = too
        self.ackw = ackw
        self.priority = priority


########################################################################################################################################
class Peer:
    def __init__(self, name, ip, port, writer, cmdLine=None, logPath=None, pid=None):
        self.name = name
        self.ip = ip
        self.port = port
        self.writer = writer
        self.cmdLine = cmdLine
        self.logPath = logPath
        self.pid = pid
    def __call__(self, *args, **kwargs):
        for x in args:
            self.__dict__.update({x:None})
        self.__dict__.update(kwargs)


class AMatrixQ(ATelecommand, metaclass=Singleton):
    Name = AMATRIXQ_NAME
    Peers = {}
    LocalPeers = {}
    LocalMonitored = {}
    clients = {} # traders
    asyncLoop = None
    def __init__(self, config, logger, name:str=None, asyncLoop=None, internal_port:int=DEFAULT_INTERNAL_PORT, external_port:int=DEFAULT_EXTERNAL_PORT, autorun=True, *args, **kwargs):
        if not name is None:
            self.Name = name
        
        self.config = config
        self.logger = logger
        self.watch_dog = None
        self.teleAsyncHook = None
        self.state = "inited"

        # async loop
        if not asyncLoop is None: self.asyncLoop = asyncLoop
        else: self.asyncLoop = asyncioGet_event_loop()
        
        # internal connection server
        self.async_tcp_server = None
        self.internal_port = internal_port

        # external connection server
        self.async_tcp_ssl_server = None
        self.external_port = external_port

        # telecommand
        self.TeleBufQ = deque()

        if autorun:
            self.run_forever(internal_port, external_port)

    ####################################################################
    # Run servers forever
    def run_forever(self, internal_port=DEFAULT_INTERNAL_PORT, external_port=DEFAULT_EXTERNAL_PORT):
        # telecommand part
        self.teleAsyncHook = self.asyncLoop.create_task(self.TeleCommand())
        # manage message to aMatrixQ
        self.MatrixQSocket = aQSocket(forward_message=self.forward_message, process_my_message=self.process_my_message)
        # internal communication
        internal_TCP_server = self.asyncLoop.create_task(self.run_TCP_server(host=AMATRIXQ_IP_INTERNAL, port=internal_port))
        # external communication
        external_TCP_SSL_server = self.asyncLoop.create_task(self.run_TCP_SSL_server(host=AMATRIXQ_IP_EXTERNAL, port=external_port))
        # run aMatrixQ socket
        self.asyncLoop.create_task(self._register_subs(name=self.Name, ip="_._._._", port=-1, writer=self.MatrixQSocket, cmdLine=" ".join(argv), logPath=osPathjoin(osGetcwd(),"logs", "{0}.log".format(self.Name.lower())), pid=osGetpid()))
        self.asyncLoop.create_task(self.MatrixQSocket.received_data())
        # watch_dog
        self.asyncLoop.create_task(self.start_watch_dog())
        # monitoring if not already runs...
        self.asyncLoop.create_task(self.start_monitoring())
        # run_forever
        self.asyncLoop.run_forever()

    ####################################################################
    # AMatrixQ methods
    async def _register_subs(self, name, ip, port, writer, cmdLine=None, logPath=None, pid=None):
        global asyncLock
        async with asyncLock:
            self.Peers[name] = Peer(name=name, ip=ip, port=port, writer=writer, cmdLine=cmdLine, logPath=logPath, pid=pid)
            if ip == "127.0.0.1":
                self.LocalPeers[name] = self.Peers[name]

    async def _unregister_subs(self, name):
        global asyncLock
        async with asyncLock:
            self.Peers.pop(name)
            if name in self.LocalPeers: 
                self.LocalPeers.pop(name)

    # manage messages coming to aMatrixQ
    async def process_my_message(self, data):
        #if data.msg==...
        message="coucou"
        return Qmsg(msg=message, frome=self.Name, too=data.frome)

    ####################################################################
    # message transfert part
    async def get_response(self, msg):
        global asyncLock
        async with asyncLock:
            try:
                writer = self.Peers[msg.too].writer
            except Exception as e:
                LostQmsg(msg)
                await self.logger.asyncError("{0} : error while trying to get response message : {1}".format(self.Name, e))
        return await writer.send_data(msg)
    
    async def forward_message(self, msg):
        global asyncLock
        async with asyncLock:
            try:
                writer = self.Peers[msg.too].writer
            except Exception as e:
                LostQmsg(msg) 
                await self.logger.asyncError("{0} : error while trying to forward message : {1}".format(self.Name, e))     
        await writer.send_data(msg)

    ####################################################################
    # internal TCP communication
    @staticmethod
    async def handle_TCP_client(reader, writer, iAMatrixQ):
        asyncSock = SafeAsyncSocket(reader=reader, writer=writer)
        data = await asyncSock.receive_data()
        if not data:
            asyncSock.writer.close()
            await asyncSock.writer.wait_closed()
            return
        clientName, host, port, cmdLine, logPath, pid = data.split(':') ; port = int(port)
        await iAMatrixQ._register_subs(name=clientName, ip=host, port=port, writer=asyncSock, cmdLine=cmdLine, logPath=logPath, pid=pid)
        await iAMatrixQ.logger.asyncInfo("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(iAMatrixQ.Name, clientName, host, port))
        while True:
            data = await asyncSock.receive_data()
            if not data:
                break
            if data.ackw:
                response = await iAMatrixQ.get_response(msg=data)
            else:
                await iAMatrixQ.forward_message(msg=data)
                response = None
            if not response is None:
                asyncSock.send_data(response)
        asyncSock.writer.close()
        await asyncSock.writer.wait_closed()
        await iAMatrixQ._unregister_subs(name=clientName)

    async def run_TCP_server(self, host, port):
        self.async_tcp_server = await asyncioStart_server(lambda reader, writer: AMatrixQ.handle_TCP_client(reader=reader, writer=writer, iAMatrixQ=self), host=host, port=port)
        await self.logger.asyncInfo("{0} async TCP server : socket async TCP handler is open : {1}, srcport {2}".format(self.Name, host, port))
        async with self.async_tcp_server:
            await self.async_tcp_server.serve_forever()

    ####################################################################
    # external TCP SSL communication
    @staticmethod
    async def handle_TCP_SSL_client(reader, writer, eAMatrixQ):
        asyncSock = SafeAsyncSocket(reader=reader, writer=writer)
        data = await asyncSock.receive_data()
        if not data:
            asyncSock.writer.close()
            await asyncSock.writer.wait_closed()
            return
        clientName, host, port = data.split(':') ; port = int(port)
        await eAMatrixQ._register_subs(name=clientName, ip=host, port=port, writer=asyncSock)
        await eAMatrixQ.logger.asyncInfo("{0} : '{1}' has established connection with encryption '{2}' from '{3}' destport '{4}'".format(eAMatrixQ.Name, clientName, asyncSock.writer.transport.get_extra_info('ssl_object').version(), clientName, host, port))
        while True:
            data = await asyncSock.receive_data()
            if not data:
                break
            if data.ackw:
                response = await eAMatrixQ.get_response(msg=data)
            else:
                await eAMatrixQ.forward_message(msg=data)
                response = None
            if not response is None:
                asyncSock.send_data(response)
        asyncSock.writer.close()
        await asyncSock.writer.wait_closed()
        await eAMatrixQ._unregister_subs(name=clientName)

    async def run_TCP_SSL_server(self, host, port):
        from common.Helpers.network_helpers import SSL_test_context
        self.async_tcp_ssl_server = await asyncioStart_server(lambda reader, writer: AMatrixQ.handle_TCP_SSL_client(reader=reader, writer=writer, eAMatrixQ=self), host=host, port=port, ssl=SSL_test_context())
        await self.logger.asyncInfo("{0} async TCP SSL server : socket async TCP SSL handler is open : {1}, srcport {2}".format(self.Name, host, port))
        async with self.async_tcp_ssl_server:
            await self.async_tcp_ssl_server.serve_forever()

    #####################################################################
    # start watch_dog
    async def start_watch_dog(self):
        pass
        #if not is_process_running(cmdlinePatt="watch_dog"):
        #    _ = launch_watch_dog_server(conf=self.config.COMMON_FILE_PATH)
        #    await self.logger.asyncInfo("{0} : watch server is starting.. .  .".format(self.Name))
        #self.watch_dog = get_watch_dog()

    #####################################################################
    # start monitoring
    async def start_monitoring(self):
        if not is_process_running(cmdlinePatt="monitoring"):
            _ = launch_monitoring_server(conf=self.config.COMMON_FILE_PATH)
            await self.logger.asyncInfo("{0} : main monitoring server is starting.. .  .".format(self.Name))

    #####################################################################
    ## Telecommand part
    def get_asyncLock(self):
        global asyncLock
        return asyncLock
    
    def telePortMe(self):
        # do something
        pass


#================================================================
if __name__ == "__main__":
    from sys import argv

    name = AMATRIXQ_NAME
    configStr = "current"

    name = name.lower()
    config, logger = init_logger(name=name, config=configStr) 

    mainQ = AMatrixQ(config=config, logger=logger, autorun=False)
    asyncioRun(mainQ.run_forever())

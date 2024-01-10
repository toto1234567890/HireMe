#!/usr/bin/env python
# coding:utf-8


from sys import argv
from os import environ as osEnviron, getpid as osGetpid, getcwd as osGetcwd
from os.path import join as osPathJoin
from asyncio import start_server as asyncioStart_server, \
                    Lock as asyncioLock, get_event_loop as asyncioGet_event_loop, wrap_future as asyncioWrap_future
from threading import Thread
from logging.handlers import DEFAULT_TCP_LOGGING_PORT
from socketserver import ThreadingTCPServer, StreamRequestHandler

# relative import
from sys import path;path.extend("..")
from common.ThreadQs.routing_rules import LostQmsg
from common.Helpers.helpers import getUnusedPort
from common.Helpers.os_helpers import host_has_supervisor, launch_monitoring_server, start_independant_process
from common.Helpers.network_helpers import MyAsyncSocketObj, SafeAsyncSocket, SafeSocket, SSL_server_context, get_my_public_ip
from common.Helpers.retrye import asyncRetry


asyncLock = asyncioLock()

#if hasattr(self, "logger"): 
#    self.logPath = self.logger.Logger.handlers[0].baseFilename
#else: 
#    self.logPath = osPathJoin(osGetcwd(), "logs", "{0}.log".format(self.Name.lower()))


########################################################################################################################################

class WatchDog:
    monitored = {"log_server":None,  "telecommand":None, "notif_server":None, "config_server":None, "monitoring":None}

    ####################################################################
    # AMatrixQ methods
    async def aMatrixQ_watch(self):
        if host_has_supervisor():
            self.logger.asyncWarning("{0} : process won't start, 'supervisord' is already running on this machine...".format(self.Name))
        else:
            self.monitored["log_server"] = self.log_server_watch
            self.monitored["tele_remote"] = self.tele_remote_watch
            self.monitored["notif_server"] = self.notif_server_watch
            self.monitored["config_server"] = self.config_server_watch
            self.monitored["monitoring"] = self.monitoring_watch

            for name, method in self.monitored.items():
                doNotWaitThread = self.asyncLoop.run_in_executor(None, method)
                _ = asyncioWrap_future(doNotWaitThread)


    #@watchDogRetry()
    async def aMatrixQ_watch(self):
        async with MyAsyncSocketObj(name="{0}".format("watch_dog-"+self.Name)).make_connection(server="127.0.0.1", port=osEnviron.get("MA_INTPORT")) as watchDogSock:
            await watchDogSock.send_data("{0}:{1}:{2}:{3}:{4}:{5}".format(self.Name, "127.0.0.1", watchDogSock.getsockname()[1], "".join(argv), self.logPath, osGetpid()))
            while True:
                data = await watchDogSock.receive_data()
                if not data:
                    break

    #@watchDogRetry()
    async def monitoring_watch(self):
        async with MyAsyncSocketObj(name="{0}".format("watch_dog-"+self.Name)).make_connection(server="127.0.0.1", port=osEnviron.get("MT_PORT")) as watchDogSock:
            await watchDogSock.send_data("{0}:{1}:{2}:{3}:{4}:{5}".format(self.Name, "127.0.0.1", watchDogSock.getsockname()[1], "".join(argv), self.logPath, osGetpid()))
            while True:
                data = await watchDogSock.receive_data()
                if not data:
                    break

    # AMatrixQ methods
    ####################################################################




    ####################################################################
    # internal TCP communication
    @staticmethod
    async def handle_TCP_client(reader, writer, WatchDogHandler):
        asyncSock = SafeAsyncSocket(reader=reader, writer=writer)
        data = await asyncSock.receive_data()
        if not data:
            asyncSock.writer.close()
            await asyncSock.writer.wait_closed()
            return
        clientName, host, port, cmdLine, logPath, pid = data.split(':') ; port = int(port)
        await WatchDogHandler._register_subs(name=clientName, ip=host, port=port, writer=asyncSock, cmdLine=cmdLine, logPath=logPath, pid=pid)
        #await WatchDogHandler.logger.asyncInfo("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(WatchDogHandler.Name, clientName, host, port))
        while True:
            data = await asyncSock.receive_data()
            if not data:
                break
            if data.ackw:
                response = await WatchDogHandler.get_response(msg=data)
            else:
                await WatchDogHandler.forward_message(msg=data)
                response = None
            if not response is None:
                asyncSock.send_data(response)
        asyncSock.writer.close()
        await asyncSock.writer.wait_closed()
        await WatchDogHandler._unregister_subs(name=clientName)

    async def run_TCP_server(self, host, port):
        self.async_tcp_server = await asyncioStart_server(lambda reader, writer: WatchDog.handle_TCP_client(reader=reader, writer=writer, WatchDogHandler=self), host=host, port=port)
        async with self.async_tcp_server:
            await self.async_tcp_server.serve_forever()



    ####################################################################
    # WatchDog methods
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


#================================================================
if __name__ == "__main__":
    toto = WatchDog()
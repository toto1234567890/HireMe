#!/usr/bin/env python
# coding:utf-8


from os.path import dirname as osPathDirname, join as osPathJoin
from uuid import uuid4
from collections import deque
from asyncio import Lock as asyncioLock, Queue as asyncioQueue, run as asyncioRun, all_tasks as asyncioAll_tasks, sleep as asyncioSleep, \
                    start_server as asyncioStart_server, get_event_loop as asyncioGet_event_loop, wrap_future as asyncioWrap_future
from flask import Flask, request, render_template, jsonify


# relative import
from sys import path;path.extend("..")
from common.ThreadQs.routing_rules import LostQmsg
from common.TeleRemote.tele_command import ATelecommand
from common.Helpers.helpers import Singleton, init_logger, getUnusedPort
from common.Helpers.os_helpers import start_independant_process
from common.Helpers.network_helpers import SafeAsyncSocket
#from trading.trading_helpers import refresh_trading_component


DEFAULT_RETRY_PERIOD = 1

asyncLock = asyncioLock()

class Qmsg:
    def __init__(self, msg, frome, too, ackw=None, priority=False):
        self.id = uuid4()
        self.msg = msg
        self.frome = frome
        self.too = too
        self.ackw = ackw
        self.priority = priority


########################################################################################################################################

class aQSocket():
    """
    class to simulate socket for incoming message to aMatrixQ 
    or managing Subs tasks in aStarQ... 
    """
    def __init__(self, process_my_message, forward_message):
        self.aMatrixQueue = asyncioQueue()
        self.process_my_message = process_my_message
        self.forward_message = forward_message
    async def send_data(self, data):
        await self.aMatrixQueue.put(data)
    async def received_data(self):
        while True:
            data = await self.aMatrixQueue.get()
            msg = await self.process_my_message(data)
            await self.forward_message(msg)
            self.aMatrixQueue.task_done()


class AStarQ(ATelecommand, metaclass=Singleton):
    """ 
    For AStarQ.subs
    *args should contains tuples of tuples :
        (  
            ("name1", Func1_ptr | "module.func1", childProc=False), 
            ("name2", Class2_ptr | "module.class2", childProc=True)
        )
    For subs (func or class) params
    **kwargs should contains a dict of params for the task or childproc
        {   
            name1: { "name1":{"func1_named_arg":"arg1_1"} }, 
            name2: { "name2":{"class2_named_arg":"arg2_1"} }
        }
    """
    Name = "AStarQ"
    asyncLoop = None
    def __init__(self, config, logger, asyncLoop=None, name:str=None, host:str="127.0.0.1", port:int=int(getUnusedPort()), autorun=True, *args, **kwargs):
        if not name is None:
            self.Name = name
        self.config = config
        self.logger = logger
        self.host = host ; self.port = port
        self.clients = {} # traders
        self.asyncLoop = None
        teleAsyncHook = None
        self.state = "inited"   

        # async loop
        if not asyncLoop is None: self.asyncLoop = asyncLoop
        else: self.asyncLoop = asyncioGet_event_loop()

        # telecommand
        self.TeleBufQ = deque()

        #for arg in args:
        #    self.subs(arg, kwargs)
          
        if autorun:
            self.run_forever()

    def run_forever(self):
        # telecommand
        self.teleAsyncHook = self.asyncLoop.create_task(self.TeleCommand())
        # Tcp part
        self.asyncLoop.create_task(self.run_TCP_server(), name="run_TCP_server")
        # monitoring
        doNotWaitThread = self.asyncLoop.run_in_executor(None, self.start_webserver, self.Name)
        _ = asyncioWrap_future(doNotWaitThread)
        # run_forever
        self.asyncLoop.run_forever()

    ####################################################################
    # AStarQ methods
    async def _register_subs(self, name, writer):
        global asyncLock
        async with asyncLock:
            self.clients[name] = writer
            
    def _get_subs(self, TaskOrChildProc, childproc=False):
        if type(TaskOrChildProc) == "str":
            if childproc:
                return globals()["info_module"].get(TaskOrChildProc)
            else:
                return globals().get(TaskOrChildProc)
        else: 
            return TaskOrChildProc
    # @refresh_trading_component
    async def Subs(self, name, subs, childProc=False, **kwargs):
        if not childProc: 
            # local subs
            try:
                cur_kwargs = kwargs.pop(name)
            except:
                cur_kwargs = {}
            subs = self._get_subs(TaskOrChildProc=subs)
            self.asyncLoop.create_task(subs(**cur_kwargs), name=name)
            await self._register_subs(name=name, writer=subs)
        else:
            # process subs
            try:
                args = kwargs.pop(name) ; cur_kwargs = {"host":self.host, "port":self.port} | args
            except: 
                cur_kwargs = {"host":self.host, "port":self.port} 
            childProcCmd = self._get_subs(TaskOrChildProc=subs, childproc=True)
            args=()
            for arg in cur_kwargs.values(): args += (arg,) 
            start_independant_process(childProcCmd, argv=args)
        
    async def _unregister_subs(self, name):
        global asyncLock
        async with asyncLock:
            self.clients.pop(name)
    async def un_Subs(self, name):
        await self._unregister_subs(name=name)
        subsTask = None
        for task in asyncioAll_tasks():
            if task.get_name() == name:
                subsTask = task
                break
        if not subsTask is None:
            # local subs
            subsTask.cancel()
            await subsTask
        else :
            # also unregister while exiting TCP connection, in handle_TCP_client... 
            self.get_response(Qmsg(msg=False, too=name, frome=self.Name))

    ####################################################################
    # message transfert part
    async def get_response(self, msg):
        global asyncLock
        async with asyncLock:
            try:
                writer = self.clients[msg.too].writer
            except Exception as e:
                LostQmsg(msg)
                await self.logger.asyncError("{0} : error while trying to get response message : {1}".format(self.Name, e))
        return await writer.send_data(msg)
    
    async def forward_message(self, msg):
        global asyncLock
        async with asyncLock:
            try:
                writer = self.clients[msg.too].writer
            except Exception as e:
                LostQmsg(msg) 
                await self.logger.asyncError("{0} : error while trying to forward message : {1}".format(self.Name, e))     
        await writer.send_data(msg)

    ####################################################################
    # aStarQ heart
    async def handle_TCP_client(reader, writer, aStarQ):
        asyncSock = SafeAsyncSocket(reader=reader, writer=writer)
        data = await asyncSock.receive_data()
        if not data:
            asyncSock.writer.close()
            await asyncSock.writer.wait_closed()
            return
        clientName, host, port = data.split(':') ; port = int(port)
        aStarQ._register_subs(name=clientName, writer=writer)
        await aStarQ.logger.asyncInfo("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(aStarQ.Name, clientName, host, port))
        while True:
            data = await asyncSock.receive_data()
            if not data:
                break
            if data.priority:
                response = await aStarQ.get_response(msg=data)
            else:
                await aStarQ.forward_message(msg=data)
                response = None
            if not response is None:
                asyncSock.send_data(response)
                await asyncSock.writer.drain()
                await aStarQ.logger.asyncInfo("{0} async TCP : response '{1}' send to '{2}'".format(aStarQ.Name, response, clientName))
        asyncSock.writer.close()
        await asyncSock.writer.wait_closed()
        await aStarQ._unregister_subs(name=clientName)

    async def run_TCP_server(self):
        self.async_tcp_server = await asyncioStart_server(lambda r, w: self.handle_TCP_client(r, w, self), self.host, self.port)
        await self.logger.asyncInfo("{0} async TCP : socket async TCP handler is open : {1}, srcport {2}".format(self.Name, self.host, self.port))
        await self.async_tcp_server.serve_forever()

    #####################################################################
    ## Telecommand part
    def get_asyncLock(self):
        global asyncLock
        return asyncLock

    #####################################################################    
    ## webServer view
    def start_webserver(self, name, host_port=int(getUnusedPort())):
        try :
            web_template_folder = osPathJoin(osPathDirname(__file__), "templates")
            web_static_folder = osPathJoin(osPathDirname(__file__), "static")

            app = Flask(name, template_folder=web_template_folder, static_folder=web_static_folder)
            #self.webserver = host_port
            app.config['SERVER_NAME'] = "127.0.0.1:{0}".format(host_port)
            self.logger.info("{0} : flask web server is available here : http://{1}:{2}".format(self.Name, self.host, host_port))

            # main http endpoint
            @app.route('/')
            def index():
                return render_template('test.html')

            ## endpoint that send JSON data
            #@app.route('/json_data')
            #def json_data():
            #    last_data = list(data[0:25])
            #    last_data.insert(0, ("broker", "ticker", "ask", "bid", "time", "date_creat", "user"))
            #    return jsonify({'data': last_data})

            app.run()
        except Exception as e:
            self.logger.critical("{0} : error while trying to start web interface : {1}".format(name.capitalize(), e))
            enabled = False
            exit(1)



#================================================================
if __name__ == "__main__":
    configStr = "current"
    config, logger = init_logger(name=AStarQ.Name.lower(), config=configStr) 
    # for  testing purposes
    mainQ = AStarQ(config=config, logger=logger, autorun=False)
    asyncioRun(mainQ.run_forever())
    


    ## Add this to another python file for testing 
    #class TaskSubs():
    #    def __init__(self, autorun=True):
    #        AStarQ.__init__(self, autorun=autorun)
    #        self.TaskQ = asyncioQueue()
    #    async def send_data(self, data):
    #        if data.priority:
    #            return await self.process_data(data)
    #        else:
    #            self.TaskQ.put_nowait(data)
    #    async def run(self):
    #        while True:
    #            data = await self.TaskQ.get()
    #            self.process_data(data)

    # from  
    #def_kwargs={"config":config, "logger":logger}
#
    #SwissQ = SubsQ("SwissQ", tradeQueues, default_recv="SwissquoteAPI")
    #Swissquote = SubsQ("SwissquoteAPI", tradeQueues, default_recv="SwissQ")
#
    #SwissQT = SubsQ(name="SwissQT", mainQueue=tradeQueues, default_recv="SwissquoteAPIT")
    #SwissquoteT = SubsQ("SwissquoteAPIT", tradeQueues, default_recv="SwissQT")
    ## 
    ##def_kwargs = {"logger":logger, "config":config}
    #SwissQT.send_msg_in("test1", ackw=True)
    #toto = SubsQ("toto", tradeQueues, default_recv="titi", ChildProc=ProcessAdapter, kwargs=def_kwargs)
    #titi = SubsQ("titi", tradeQueues, default_recv="toto", ChildProc=ProcessAdapter, kwargs=def_kwargs)
    #Swissquote.send_msg_in("charge")
    #SwissQ.send_msg_in_now("????priority message!!!")
    #import time
    #t = time.perf_counter()
    #x = 1
    #while True:
    #    for x in range(10000):
    #        if tradeQueues.run:
    #            Swissquote.send_msg_in("charge")
    #            SwissQ.send_msg_in("????priority message!!!") 
    #            Swissquote.send_msg_in("charge") 
    #            Swissquote.send_msg_in("charge") 
    #            #titi.send_msg_in("coucou")
    #            SwissQT.send_msg_in("test1") 
    #            #toto.send_msg_in("coucou")
    #        if x == 1000:
    #            break
    #    break
#
#
    #t1 = time.perf_counter()
 #
    #print("Elapsed time: {0}".format(t1-t))
 
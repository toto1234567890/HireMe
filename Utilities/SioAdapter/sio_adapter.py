#!/usr/bin/env python
# coding:utf-8


import socketio

# relative import
from sys import path;path.extend("..")
from common.Utilities.discord import DiscordClient
from common.ThreadQs.thread_Qs import SubsQ



###########################################################################################################

class ClientRoom(socketio.ClientNamespace):
    Name="ClientNamespace"
    def __init__(self, user, config, logger, namespace, discoLogger):
        super().__init__(namespace)
        self.Room = namespace[1:]
        self.user = user
        self.config = config
        self.logger = logger
        self.Log_Chat = discoLogger
    def on_connect(self):
        self.self.Log_Chat("Hello room '{0}'!".format(self.Room))
    def on_disconnect(self):
        self.self.Log_Chat("Bye bye '{0}'!".format(self.Room))
    def connect_error(self):
        self.logger.error("{0} : discord connection to room '{1}' failed...".format(self.Name, self.Room))

###########################################################################################################

class AsyncClientRoom(socketio.AsyncClientNamespace):
    Name="AsyncClientNamespace"
    def __init__(self, user, config, logger, namespace, discoLogger):
        super().__init__(namespace)
        self.Room = namespace[1:]
        self.user = user
        self.config = config
        self.logger = logger
        self.Log_Chat = discoLogger
    async def on_connect(self):
        await self.self.Log_Chat("Hello room '{0}'!".format(self.Room))
    async def on_disconnect(self):
        await self.self.Log_Chat("Bye bye '{0}'!".format(self.Room))
    async def connect_error(self):
        await self.logger.asyncError("{0} : discord connection to room '{1}' failed...".format(self.Name, self.Room))

###########################################################################################################

class MainClientNameSpace:
    def __init__(self, user, config, logger, namespace, loop=None):
        if not loop is None:
            self.asyncLoop = loop

        else:

        super().__init__(user, config, logger, namespace)

    def on_my_event(self, data):
        self.emit('my_response', data)

###########################################################################################################

class SioClient:
    Name="SioClient" 

    def __init__(self, config, logger, name=None, RoomsAndDisc:dict=None, asnyc_mode:bool=False):
        if not name is None:
            self.Name = name

        self.config = config
        self.logger = logger
        self.RoomsAndDisc = RoomsAndDisc
        self.Log_Chat = DiscordClient(user=name, config=config, logger=logger, name=self.Name)

        if not RoomsAndDisc is None:    
            for room, item in RoomsAndDisc.items():
                if item != '': 
                    DiscoRoomAddress = item["DiscoAddress"]
                    if item["ClassNamespace"] != '' :
                        ClassNamespace = item["ClassNamespace"]
                        self.join_room(room, DiscoRoomAddress, ClassNamespace, asnyc_mode)
                    else:
                        self.join_room(room, DiscoRoomAddress, asnyc_mode)
                else:   
                    self.join_room(room, asnyc_mode)
        
        self.logger.info("{0} : has been started !".format(self.Name))


    def join_room(self, room:str, DiscoAddress:str, ClassNamespace=MainClientNameSpace, asnyc_mode:bool=False):
        try:
            if not room.startswith('/'): 
                room="/{0}".format(room)

            if asnyc_mode:  
                sio=socketio.AsyncClient(logger=True, engineio_logger=True)
            else:           
                sio=socketio.Client(logger=True, engineio_logger=True)
            sio.register_namespace(ClassNamespace(room))

            self.Log_Chat.join_room(DiscoAddress)
            self.Log_Chat.send_msg("Hello!")

            self.RoomsAndDisc[room]=sio
        except Exception as e:
            self.logger.error("{0} : error while trying to join '{1}' : {2}".format(self.Name, room, e))


    def leave_room(self, room:str):
        try:
            if not room.startswith('/'): 
                room="/{0}".format(room)

            sio = self.RoomsAndDisc[room]
            sio.disconnect(room)

            self.Log_Chat.send_msg("Bye!")
            self.Log_Chat.leave_room(room)

            self.RoomsAndDisc.pop(room, None)
        except Exception as e:
            self.logger.error("{0} : error while trying to leave '{1}' : {2}".format(self.Name, room, e))
        

    def send_msg(self, msg, room):
        sio = self.RoomsAndDisc[room]
        sio.send_msg(msg)

    async def send_async_msg(self, msg, room):
        sio = self.RoomsAndDisc[room]
        await sio.send_msg(msg)

###########################################################################################################

class SioClient:
    Name="SioClient" 

    def __init__(self, config, logger, name=None, RoomsAndDisc:dict=None, async_mode:bool=False):
        if not name is None:
            self.Name = name

        self.config = config
        self.logger = logger
        self.RoomsAndDisc = RoomsAndDisc
        self.Log_Chat = DiscordClient(user=name, config=config, logger=logger, name=self.Name)

        self.init_chat(RoomsAndDisc)
        self.logger.info("{0} : has been started !".format(self.Name))


    def init_chat(self, RoomsAndDisc, async_mode=False):
        if not RoomsAndDisc is None:    
            for room, item in RoomsAndDisc.items():
                if item != '': 
                    DiscoRoomAddress = item["DiscoAddress"]
                    if item["ClassNamespace"] != '' :
                        ClassNamespace = item["ClassNamespace"]
                        self.join_room(room, DiscoRoomAddress, ClassNamespace, async_mode)
                    else:
                        self.join_room(room, DiscoRoomAddress, async_mode)
                else:   
                    self.join_room(room, async_mode)

    def join_room(self, room:str, DiscoAddress:str, ClassNamespace=MainClientNameSpace, asnyc_mode:bool=False):
        try:
            if not room.startswith('/'): 
                room="/{0}".format(room)

            if asnyc_mode:  
                sio=socketio.AsyncClient(logger=True, engineio_logger=True)
            else:           
                sio=socketio.Client(logger=True, engineio_logger=True)
            sio.register_namespace(ClassNamespace(room))

            self.Log_Chat.join_room(DiscoAddress)
            self.Log_Chat.send_msg("Hello!")
            self.RoomsAndDisc[room]=sio
        except Exception as e:
            self.logger.error("{0} : error while trying to join '{1}' : {2}".format(self.Name, room, e))

    def leave_room(self, room:str):
        try:
            if not room.startswith('/'): 
                room="/{0}".format(room)

            sio = self.RoomsAndDisc[room]
            sio.disconnect(room)

            self.Log_Chat.send_msg("Bye!")
            self.Log_Chat.leave_room(room)

            self.RoomsAndDisc.pop(room, None)
        except Exception as e:
            self.logger.error("{0} : error while trying to leave '{1}' : {2}".format(self.Name, room, e))

#
#def my_background_task(my_argument):
#    # do some background work here!
#    pass
#
#task = sio.start_background_task(my_background_task, 123)
#
#sio.sleep(2)
#
#sio = socketio.Client(logger=True, engineio_logger=True)
#
#
#class SioAdapter(SubsQ):
#    Name="SioAdapter"
#    def __init__(self, name, ):
#        self.Name = name
#    sio = socketio.Client()
#
#    sio.connect('http://localhost:5000')
#    sio.connect('http://localhost:5000', namespaces=['/chat'])
#
#    sio.emit('my message', {'foo': 'bar'})
#    sio.emit('my message', {'foo': 'bar'}, namespace='/chat')
#
#    sio.disconnect()
#    sio.wait()
#
#    @sio.event
#    def my_event(sid, data):
#        # handle the message
#        return "OK", 123
#    
#    @sio.event
#    def connect_error(data):
#        print("The connection failed!")
#    
#    @sio.event
#    def disconnect():
#        print("I'm disconnected!")
#
#    @sio.on('my message')
#    def on_message(data):
#        print('I received a message!')
#
#    @sio.event
#    def message(data):
#        print('I received a message!')
#
#    @sio.on('*')
#    def catch_all(event, data):
#        pass





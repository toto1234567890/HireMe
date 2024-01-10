#!/usr/bin/env python
# coding:utf-8

from os.path import dirname as osPathDirname
from flask import Flask, current_app, request
from flask_socketio import SocketIO, join_room, leave_room, emit as sio_emit, send as sio_send

# relative import
from sys import path;path.extend("..")
from common.Database.database import Database
from common.FlaskNode.flask_models import Schema



class defaultRoomMethod:
    def on_connect(self, chateur):
        current_app.logger.info("{0} : '{1}' is connected !".format(self.Name, chateur))
        self.send_response("{0} : {1} please join default room : '{0}'".format(self.Name, chateur))

    def on_disconnect(self, chateur):
        current_app.logger.info("{0} : '{1}' has been disconnected !".format(self.Name, chateur))

    def on_join(self, data):
        chateur = data['username']
        room = data['room']
        join_room(room)
        current_app.logger.info("{0} : '{1}' has just joined the room !".format(self.Name, chateur))

    def on_leave(self, data):
        chateur = data['username']
        room = data['room']
        leave_room(room)
        current_app.logger.info("{0} : '{1}' has just left the room...".format(self.Name, chateur))
        self.disconnect(sid=data['sid'], namespace=self.namespace)

    def on_error(self, e:Exception):        
        current_app.logger.error("{0} : error while receiving event {1} : '{2}'".format(self.Name, request.event["args"], ))


class Room(defaultRoomMethod):
    def __init__(self, namespace, config):
        super().__init__(namespace)
        self.Name = namespace[1:]
        #self.log_chat = Notifie(apprise_config=config.parse)

    def on_my_event(self, data):
        sio_emit('my_response', data) 


def create_app(name, config, logger, prefixe=None):  
    app = Flask(name)
    if not prefixe is None:
        prefixe = prefixe.upper()
    else:
        prefixe = name.upper()

    _conf = dict(config.parser.items(name.upper()))
    app.config.update(_conf)
    app.config['SERVER_NAME'] = "{0}:{1}".format(_conf["{0}_SERVER".format(prefixe)], _conf["{0}_PORT".format(prefixe)])
    app.config['TESTING'] = True

    if not (app.config['SERVER_NAME']).startswith("127.0.0.1") and not (app.config['SERVER_NAME'].lower()).startswith("localhost"):
        try:
            app.config['SECRET_KEY'] = _conf["{0}_SECRET".format(prefixe)]
        except Exception as e:
            logger.critical("{0} : error while trying to load 'secret cookies' : {1}".format(name.capitalize(), e))
            logger.error("{0} : won't start...".format(name.capitalize()))
            exit(1)

    socketio = SocketIO(app)   

    name=name.lower()
    # linked database : 
    Flask_DB = Database(logger, config, db_dir=osPathDirname(__file__), 
            db_name="{0}.db".format(name), 
            AppBaseSchema=Schema, 
            config_prefix=prefixe if not prefixe is None else None,
            SocketReceiver=True)

    # on error check function duplicated name
    # web part...
    @app.route('/')
    def hello():
        current_app.logger.error('someone connected on web app... ')
        return 'Hello, World!'

    # socketio part...
    @socketio.on('message')
    def handle_message(data):
        current_app.logger.error('received message: ' + data)

    #socketio.on_namespace(Room('/SA_TradingRoom', config))

    #socketio.on_namespace(DataFeeder('/SA_Feeder', config))
    
    #@socketio.on("update", namespace="/backend")
    #def handle_my_custom_event(json):
    #    emit("update", json, namespace="/frontend", broadcast=True)
    
    return socketio, app, Flask_DB, None


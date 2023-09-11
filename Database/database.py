#!/usr/bin/env python
# coding:utf-8

from os import remove as osRemove, sep as osSep
from os.path import dirname as osPathDirname, join as osPathJoin
from time import sleep
from genericpath import exists
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from socketio.exceptions import ConnectionError as SocketIOConnectionError

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.MyModels.my_models import *
from common.Helpers.helpers import getUnusedPort, getOrDefault
from common.Helpers.datas_helpers import load_schema_from_file, TradeToDB


class Database:
    """
    For another DB than DB Log:
    -   Database(logger, config, user='test', uri="sqlite:///common/AppDB.db", namespace="namespaceA", db_sslcert=False, db_reset=False)
    -   Database(logger, config, user='user', uri="postgresql+psycopg2://user:password@host:port/dbname[?key=value&key=value...]...")

    Howto (copy-paste the code below): \n
    #!/usr/bin/env python \n
    #coding:utf-8 \n

    #relative import \n
    import os;from sys import path;path.extend("..") \n
    from common.Database.database import Database \n
    from common.MyLogger.my_logger import MyLogger \n

    from app_model import * #overload common \n
    #FIXME finish docstring \n
    """
    default_user = "Logger"
    default_engine = "sqlite"
    default_uri = "sqlite:///{0}{1}backend.db".format(osPathDirname(__file__), osSep)
    default_namespace = None
    default_db_dir = osPathDirname(__file__)
    default_db_name = "Dummy.db"
    def __init__(self, logger:MyLogger, config: Config, user:str="Logger",
                    uri:str="sqlite:///{0}{1}backend.db".format(osPathDirname(__file__), osSep), 
                        engine:str="sqlite", namespace:str=None, db_sslcert:bool=False, 
                            db_dir:str=osPathDirname(__file__), db_reset:bool=False, config_prefix:str=None,
                                db_name:str="Dummy.db", inMemory:bool=False, shareable:bool=True,
                                    AppBaseSchema=None, SocketReceiver=False, stream_func=None, DBStreamHandler=None):
        self.logger = logger
        self.config = config
        self.user = user
        self.db_name = db_name.lower()
        self.config_prefix = config_prefix

        try:
            if engine == "sqlite" and not inMemory:
                # standard Db log (no uri param)
                if uri == "sqlite:///{0}{1}backend.db".format(osPathDirname(__file__), osSep) and db_name == "Dummy.db" and db_dir == osPathDirname(__file__):
                    self.db_uri = uri
                    self.db_name = (self.db_uri.split(osSep))[-1]
                # complete uri path
                elif uri.startswith("sqlite:///") and uri != "sqlite:///{0}{1}backend.db".format(osPathDirname(__file__), osSep) and db_name == "Dummy.db": 
                    self.db_uri = uri
                # others cases
                else:
                    if db_dir != osPathDirname(__file__):
                        if not exists(db_dir):
                            self.logger.error("Database : directory '{0}' doesn't exist...".format(db_dir))
                            sleep(1)
                            exit(1) 
                    db_path = osPathJoin(db_dir, self.db_name)                    
                    self.db_uri = "{0}{1}".format("sqlite:///", db_path) 
                if not self.db_uri.endswith(".db"): 
                    self.db_uri = "{0}{1}".format(self.db_uri, ".db")
            elif "mode=memory" in engine and inMemory:
                if shareable:
                    self.db_uri = "sqlite:///file:{0}?mode=memory&cache=shared&uri=true".format(db_name)
                else:
                    self.db_uri = "sqlite:///file:{0}?mode=memory&uri=true".format(db_name)
            else:
                raise NotImplementedError("error SQLAlchemy only accept 'sqlite engine' or 'sqlite mode=memory' with inMemory=True")
        except Exception as e:
            self.logger.error("Database : error while trying to get URI : {0}".format(e))
            sleep(1)
            exit(1)

        engine = (self.db_uri.split(':'))[0]
        if engine == "sqlite":
            self.engine = create_engine(self.db_uri)
        
        self.database_path = self.db_uri.replace("sqlite:///", "")
        if self.db_name == "backend.db":
            self.db_port  = self.config.DB_PORT
            self.db_endpoint = self.config.DB_ENDPOINT
            self.namespace = getOrDefault(namespace, self.config.DB_NAMESPACE)
            if eval(self.config.RESET) and user == "Logger": 
                if exists(self.database_path):
                    self.drop_database() 
            if not exists(self.database_path):    
                try:
                    self._create_database()
                except Exception as e:
                    self.logger.info("Database : error while trying to create Backend database : {0}".format(e))
                    sleep(1)
                    exit(1)
        else:
            self.app_name = self.db_name.replace(".db", "")
            self.db_port = getUnusedPort() 
            self.db_endpoint = "http://db:{0}".format(self.db_port)
            self.namespace = getOrDefault(namespace, "DEFAULT")
            #if config.parser.has_section(self.app_name.upper()):
            #    section_name = "{0}".format(self.app_name.upper())
            #    section_prefix = self.config_prefix
            #else :
            #    #section_name = "DB_{0}".format(self.app_name.upper())
            #    section_name = self.app_name.upper()
            #    section_prefix = self.app_name
            section_name = "{0}".format(self.app_name.upper())
            if not self.config_prefix is None:
                section_prefix = self.config_prefix
            else:
                section_prefix = section_name
            # Section with same name => update else new section 
            config.update(
                section_name, 
                self.config.COMMON_FILE_PATH,
                params=(({"{0}_DB_URI".format(section_prefix) : self.db_uri, 
                        "{0}_DB_PORT".format(section_prefix) : self.db_port,
                        "{0}_DB_ENDPOINT".format(section_prefix) : self.db_endpoint,
                        "{0}_DB_NAMESPACE".format(section_prefix) : self.namespace,
                        "{0}_DB_SSLCERT".format(section_prefix) : db_sslcert, 
                        "{0}_DB_RESET".format(section_prefix) : db_reset} 
                        if not inMemory else 
                        {"{0}_DB_MEM_URI".format(section_prefix) : self.db_uri, 
                        "{0}_DB_MEM_PORT".format(section_prefix) : self.db_port,
                        "{0}_DB_MEM_ENDPOINT".format(section_prefix) : self.db_endpoint,
                        "{0}_DB_MEM_NAMESPACE".format(section_prefix) : self.namespace,
                        "{0}_DB_MEM_SSLCERT".format(section_prefix) : db_sslcert, 
                        "{0}_DB_MEM_RESET".format(section_prefix) : db_reset}))
                )
            if db_reset: 
                if exists(self.database_path):
                    self.drop_database()
            if not exists(self.database_path):
                try:
                    self.create_app_database(AppBaseSchema)
                    self.logger.info("Database : {0} database created{1}!".format(self.db_name, (' ' if not inMemory else " in memory ")))
                except Exception as e:
                    self.logger.error("Database : error while trying to create '{0}' application database : {1}".format(self.db_name, e))
                    sleep(1) 
                    exit(1)            

        self.SessionMaker = sessionmaker(bind=self.engine)

    # external socket connection...  
        if SocketReceiver:
            # Database TCP socket receiver...
            # Provide DB_FeedFunc or DatabaseStreamHandler or even both...
            # by default the default DatabaseStreamHandler is loaded and only DB_FeedFunc is needed
            # For complex connection use DatabaseStreamHandler and DB_FeedFunc (can use multiple DBSocketReceiver)
            from threading import Thread
            from common.Database.db_socket_receiver import DBSocketReceiver
            try:
                if not DBStreamHandler is None and not stream_func is None:
                    tcpserver = DBSocketReceiver(name=self.app_name, logger=logger, config=config, prefixe=config_prefix, inMemory=inMemory, stream_func=stream_func, DBStreamHandler=DBStreamHandler)
                elif not DBStreamHandler is None:
                    tcpserver = DBSocketReceiver(name=self.app_name, logger=logger, config=config, prefixe=config_prefix, inMemory=inMemory, DBStreamHandler=DBStreamHandler)
                elif not stream_func is None:
                    tcpserver = DBSocketReceiver(name=self.app_name, logger=logger, config=config, prefixe=config_prefix, inMemory=inMemory, stream_func=stream_func)
                else:
                    tcpserver = DBSocketReceiver(name=self.app_name, logger=logger, config=config, prefixe=config_prefix, inMemory=inMemory)
                Thread(target=self.launch_interface, args=(tcpserver,)).start()
            except Exception as e:
                self.logger.error("Database : error while trying to start TCP socket receiver : {0}".format(e))
    
    def launch_interface(self, tcpserver):
        tcpserver.serve_until_stopped()
    
    def drop_database(self):
        try:
            osRemove(self.database_path)
            self.logger.info("Database : {0} database removed !".format(self.db_name))
        except Exception as e:
            self.logger.error("Database : error while trying to remove '{0}' database : {1}".format(self.db_name, e))
            sleep(1)
            exit(1)

    def _create_database(self):
        # create backend.db
        Base.metadata.create_all(self.engine)
        self.logger.info("Database : {0} database created !".format(self.db_name))

    def create_app_database(self, AppBaseSchema):
        # overload specific method in child overload...
        AppBaseSchema.metadata.create_all(self.engine)

    @TradeToDB
    def db_order(self, ticker: String, asset_type: String, order_type: String, buy_or_sell: String, state: String, price: float, quantity: float, amount: float, order_date: DateTime):
        session: Session
        with self.db_session() as session:
            session.add(Order(ticker, asset_type, order_type, buy_or_sell, state, price, float(quantity), float(amount), order_date, self.user))
    
    def db_error(self, log_date: String, log_type: String, script_name: String, func_name: String, line: Integer, log_message: String):
        session: Session
        with self.db_session() as session:
            session.add(ErrorLog(log_date, log_type, script_name, func_name, line, log_message, self.user))

    @contextmanager
    def db_session(self):
        """Creates a context with an open SQLAlchemy session."""
        session: Session = scoped_session(self.SessionMaker)
        yield session
        session.commit()
        session.close() 

    # external sio connection...
    def socketio_connect(self):
        if self.socketio_client.connected and self.socketio_client.namespaces:
            return True
        try:
            if not self.socketio_client.connected:
                self.socketio_client.connect(self.db_endpoint, namespaces=["/{0}}".format(self.namespace)])
                self.logger.info("Database : socketio client connected on database '{1}'".format(self.db_name))
            while not self.socketio_client.connected or not self.socketio_client.namespaces:
                sleep(self.config.main)
            return True
        except SocketIOConnectionError as e:
            self.logger.error("Database : socketio error while trying to receive data on '{0}' database : {1}".format(self.db_name, e))
            return False


#================================================================
if __name__ == "__main__":
    from sys import argv
    from common.Helpers.helpers import init_logger
    name = "Database"
    configStr = "common"
    if len(argv) > 1:        
        try:
            if len(argv) == 4:
                from json import loads as jsonLoads
                name = (argv[1]).capitalize()
                configStr = argv[2]
                kwargs = jsonLoads(argv[3])

                config, logger = init_logger(name=name, config=configStr)
                model = load_schema_from_file(kwargs["AppBaseSchemaPath"])
                _ = Database(logger=logger, config=config, user=getOrDefault(kwargs, "TCP Database", key="user"),
                                uri=getOrDefault(kwargs, Database.default_uri, key="uri"), 
                                    engine=getOrDefault(kwargs, "sqlite", key="engine"), namespace=getOrDefault(kwargs, None, key="namespace"), db_sslcert=getOrDefault(kwargs, False, key="db_sslcert"),
                                        db_dir=getOrDefault(kwargs, Database.default_db_dir, key="db_dir"), db_reset=getOrDefault(kwargs, False, key="db_reset"), config_prefix=getOrDefault(kwargs, None, key="config_prefix"),
                                            db_name=getOrDefault(kwargs, "Dummy.db", key="db_name"), inMemory=getOrDefault(kwargs, False, key="inMemory"), shareable=getOrDefault(kwargs, False, key="inMemory"),
                                                AppBaseSchema=model.Schema, SocketReceiver=getOrDefault(kwargs, True, key="SocketReceiver"), stream_func=getOrDefault(model.DbInterface.stream_func, None))
            else:
                _, logger = init_logger(name=name, config=configStr)
                logger.error("Database : error while trying to launch the service, {0} parameter(s) provided : {1}, expected : 3 'name config_file_path **kwargs' {2}".format("too much" if len(argv) > 4 else "not enough", len(argv)-1, str(argv)))
        except Exception as e:
            _, logger = init_logger(name=name, config=configStr)
            logger.error("Database : error while trying to launch the service, wrong or missing parameter(s) : {0} => {1}".format(str(argv), e))
    else: 
        config, logger = init_logger(name=name, config=configStr)

        logger.error("test message to log error")

        # from new app :
        #from common.MyModels.app_models import *
        #AppDB = Database(logger, config, user='test', 
        #        db_name="fn_app.db", 
        #        AppBaseSchema=AppSchema, 
        #        config_prefix="FN", 
        #        SocketReceiver=True)

        sleep(1)



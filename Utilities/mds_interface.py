#!/usr/bin/env python
# coding:utf-8

import enum, datetime
from typing import Dict
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, \
    Float, ForeignKey, Integer, String, func, or_, select
from sqlalchemy.orm import column_property, relationship
from sqlalchemy.ext.declarative import declared_attr, declarative_base

###########################################################################################################

class Base(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_creat = Column(DateTime, default=datetime.datetime.utcnow)
    user = Column(String)

Schema = declarative_base(cls=Base)

class BuyOrSell(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
class TradeState(enum.Enum):
    STARTING = "STARTING"
    ORDERED = "ORDERED"
    CLOSED = "CLOSED"

class InterfaceModel(Schema):  # pylint: disable=too-few-public-methods
    __tablename__ = "InterfaceModel"
    ticker = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)
    order_type = Column(String)
    buy_or_sell = Column(Enum(BuyOrSell))
    state = Column(Enum(TradeState))
    price = Column(Float)
    order_date = Column(DateTime)
    def __init__(self, ticker: String=None, asset_type: String=None, order_type: String=None, buy_or_sell: String=None, state: String=None, price: float=None, order_date: datetime=None, user:String=None):
        self.ticker = ticker
        self.asset_type = asset_type
        self.order_type = order_type
        self.buy_or_sell = buy_or_sell
        self.state = state
        self.price = price
        self.order_date = order_date
        self.user = user
    def info(self):
        return {
            "id": self.id,
            "log_date": self.log_date,
            "log_type": self.log_type.info(),
            "log_message": self.log_message.info(),
            "datetime": self.date_time.isoformat(),
        }

schema_models = {'InterfaceModel', InterfaceModel}

###########################################################################################################

from os import sep as osSep
from os.path import dirname as osPathDirname

# relative import
from sys import path;path.extend("..")
from common.Database.database import Database

class DbInterface(Database):
    default_user = "mds_interface"
    default_engine = "sqlite"
    default_db_name = "mds_interface.db"
    default_uri = "sqlite:///{0}{1}{2}".format(osPathDirname(__file__), osSep, "mds_interface.db")
    default_namespace = None
    default_db_dir = osPathDirname(__file__)

    def db_InterfaceModel(self, ticker: String=None, asset_type: String=None, order_type: String=None, buy_or_sell: String=None, state: String=None, price: float=None, order_date: DateTime=None, **kwargs):
        session: Session
        with self.db_session() as session:
            if len(kwargs) > 0:
                session.add(InterfaceModel(MyKwargs=kwargs))
            else:
                session.add(InterfaceModel(ticker=ticker, asset_type=asset_type,  order_type=order_type, buy_or_sell=buy_or_sell, state=state, price=price, order_date=order_date, user=self.user))

###########################################################################################################

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

@contextmanager
def db_session(self):
    """Creates a context with an open SQLAlchemy session."""
    session: Session = scoped_session(self.SessionMaker)
    yield session
    session.commit()
    session.close() 

def stream_func(self, handlerName, clientName, data):
    if self.SessionMaker is None:
        engine = create_engine(DbInterface.default_uri)
        self.SessionMaker = sessionmaker(bind=engine)
        db_session(self)
    session: Session      
    with db_session(self) as session:
        for key, val in data.items():
            try:
                if key == "InterfaceModel":
                    session.add(InterfaceModel(ticker=val["ticker"], asset_type=val["asset_type"],  order_type=val["order_type"], buy_or_sell=val["buy_or_sell"], state=val["state"], price=val["price"], order_date=val["order_date"], user="toto"))
            except Exception as e:
                self.current_logger.error("{0} : error while trying to insert tcp records in database : {1}  -> sender '{2}', data -> {3}".format(handlerName, e, clientName, str(data)))
                continue

###########################################################################################################

from socketserver import StreamRequestHandler
from common.Helpers.network_helpers import SafeSocket
class DBStreamHandler(StreamRequestHandler):
    """ 
    overide the 'def stream_func(self, data):' or pass it to the SocketReceiverMixin __init__()
    """
    Name="DBStreamHandler"
    current_logger = None
    stream_func = None
    SessionMaker = None
    def handle(self):
        MySocket = SafeSocket(self.connection)
        msg = MySocket.receive_data()
        if not msg:
            return

        self.clientName, self.clientHost, port = msg.split(':') ; self.clientPort = int(port)
        self.current_logger.info("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(self.Name, self.clientName, self.clientHost, self.clientPort))#srcport '{3}'
        
        while True:
            data = MySocket.receive_data()
            if not data:
                break
            try:
                self.current_logger.debug("{0} : data received from '{1}' : {2}".format(self.Name, self.clientName, data))
                self.stream_func(handlerName=self.Name, clientName=self.clientName, data=data)
            except Exception as e:
                self.current_logger.error("{0} : error while trying to receive data from '{1}' : {2}".format(self.Name, self.clientName, e))

    def stream_func(self, handlerName, clientName, data):
        self.current_logger.info("{0} : stream_func data received from {1} : {2}".format(handlerName, clientName, str(data)))



#================================================================
if __name__ == "__main__":
    from sys import argv
    from common.Helpers.helpers import init_logger, getOrDefault
    from common.Helpers.os_helpers import get_real_path
    from common.Helpers.datas_helpers import load_schema_from_file
    name = "mds_interface"
    configStr = "common"
    if len(argv) > 1:        
        try:
            if len(argv) == 4:
                from json import loads as jsonLoads
                name = (argv[1]).capitalize()
                configStr = argv[2]
                kwargs = jsonLoads(argv[3])

                config, logger = init_logger(name=name, config=configStr)
                model = load_schema_from_file(getOrDefault(kwargs, get_real_path(__file__), key="AppBaseSchemaPath"))
                _ = model.DbInterface(logger=logger, config=config, user=getOrDefault(kwargs, "TCP Database", key="user"),
                                    uri=getOrDefault(kwargs, model.DbInterface.default_uri, key="uri"), 
                                        engine=getOrDefault(kwargs, "sqlite", key="engine"), namespace=getOrDefault(kwargs, None, key="namespace"), db_sslcert=getOrDefault(kwargs, False, key="db_sslcert"),
                                            db_dir=getOrDefault(kwargs, model.DbInterface.default_db_dir, key="db_dir"), db_reset=getOrDefault(kwargs, False, key="db_reset"), config_prefix=getOrDefault(kwargs, None, key="config_prefix"),
                                                db_name=getOrDefault(kwargs, "Dummy.db", key="db_name"), inMemory=getOrDefault(kwargs, False, key="inMemory"), shareable=getOrDefault(kwargs, False, key="shareable"),
                                                    AppBaseSchema=model.Schema, SocketReceiver=getOrDefault(kwargs, True, key="SocketReceiver"), stream_func=getOrDefault(model.stream_func, None), DBStreamHandler=getOrDefault(model.DBStreamHandler, None))
            else:
                _, logger = init_logger(name=name, config=configStr)
                logger.error("Database : error while trying to launch the service, {0} parameter(s) provided : {1}, expected : 3 'name config_file_path **kwargs' {2}".format("too much" if len(argv) > 4 else "not enough", len(argv)-1, str(argv)))
        except Exception as e:
            _, logger = init_logger(name=name, config=configStr)
            logger.error("Database : error while trying to launch the service, wrong or missing parameter(s) : {0} => {1}".format(str(argv), e))
    else: 

        config, logger = init_logger(name=name, config=configStr)
        msdInterface = DbInterface(logger=logger, config=config, user="mds_interface",
                            uri=DbInterface.default_uri, 
                                engine="sqlite", namespace=None, db_sslcert=False,
                                    db_dir=DbInterface.default_db_dir, db_reset=False, config_prefix=None,
                                        db_name=DbInterface.default_db_name, inMemory=False, shareable=False,
                                            AppBaseSchema=Schema, SocketReceiver= True, stream_func=stream_func, DBStreamHandler=DBStreamHandler)

        msdInterface.db_InterfaceModel(ticker="EUR/CHF", asset_type="Currency", order_type="TEST", buy_or_sell="BUY", state="CLOSED", price=3.14, order_date=datetime.datetime.now())
        logger.info("Test mdsInterface, please check 'mds_record' created with direct DbInterface method and '{0}' user !".format(DbInterface.default_user))

        from common.Helpers.network_helpers import MySocket
        with MySocket(name="mdsInterface", port=config.parser[name.upper()]["MDS_INTERFACE_DB_PORT"]) as sockTest:
            cpt = 0
            sockTest.send_data(data="TcpSenderTest:127.0.0.1:{0}".format(sockTest.conn.getsockname()[1]))
            while cpt < 100:        
                data = {"InterfaceModel" : {"ticker":"EUR/CHF", "asset_type":"Currency", "order_type":"essai de puis VsCode", "buy_or_sell":"SELL", "state":"OPEN", "price":1.414, "order_date":datetime.datetime.now(), "user":"TcpSender"}}
                sockTest.send_data(data=data)
                cpt+=1
        logger.warning("Test mdsInterface, please check 'mds_tcp_record' created with TCP Client and 'TcpSender' user !")

# independant server mode
# ##add in another *.py file to test
###from common.Helpers.os_helpers import launch_TCP_database
###from common.Helpers.helpers import getOrDefault
###from json import dumps as jsonDumps
###Name = "mds_interface"
###AppBaseSchemaPath = "/Users/imac/Desktop/venv/common/Utilities/mds_interface.py"
###db_name="{0}.db".format(Name.lower())
###JsonDump = {'user':"TCP MDS", 'engine':"sqlite", 'db_name':"mds_interface.db", 'SocketReceiver':True}
###kwargs = jsonDumps(JsonDump)
###
###toto = launch_TCP_database(name=Name, conf="common", JsonDump=kwargs, DBScriptPath=AppBaseSchemaPath)

# client Tests
##add in another *.py file to test
#from common.Helpers.helpers import init_logger
#from datetime import datetime
#name = "mds_interface"
#configStr = "common"
#config, logger = init_logger(name=name, config=configStr)
#
#
#from common.Helpers.network_helpers import MySocket
#with MySocket(name="mdsTcpInterface", port=config.parser[name.upper()]["MDS_INTERFACE_DB_PORT"]) as sockTest:
#    cpt = 0
#    sockTest.send_data(data="TcpSenderTest:127.0.0.1:{0}".format(sockTest.conn.getsockname()[1]))
#    while cpt < 100:        
#        data = {"InterfaceModel" : {"ticker":"EUR/CHF", "asset_type":"crotte", "order_type":"ESSAITCP", "buy_or_sell":"SELL", "state":"OPEN", "price":1.414, "order_date":datetime.now(), "user":"TCP sender"}}
#        sockTest.send_data(data=data)
#        cpt+=1
#logger.info("test mdsInterface, please check 'mds_record' created with direct TCP push !")
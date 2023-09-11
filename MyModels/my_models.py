#!/usr/bin/env python
# coding:utf-8

#FIXME check SQLAlchemy ORM raw SQL method to add in model base (selct, update, insert, delete) or create it

# TODO : 
# https://stackoverflow.com/questions/46913253/python-logging-how-to-save-class-attributes-values-in-the-log-file
#       ####  Model  ####    
#       class LastMsgSeqNum(Base):
#           __tablename__ = "last_msg_seq_num"
#           id = Column(Integer, primary_key=True)
#           LastMsgSeqNum = Column(BigInteger)
#           date_creat = Column(DateTime)
#           def __repr__(self):
#               return f"LastMsgSeqNum(MsgSeqNum={self.LastMsgSeqNum!r}, date={self.date_creat!r})"
#       ####  Logger  ####
#       logging.getLogger().warn('Carbs overload: one %s too much', donut)
#       ####  Log output  ####  
#       2017-10-25 10:59:05,302 9265 WARNING Carbs overload: one Donut(filling='jelly', icing='glaze') too much

import enum, datetime
from typing import Dict
from requests import session
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, \
    Float, ForeignKey, Integer, String, func, or_, select
from sqlalchemy.orm import column_property, relationship
from sqlalchemy.ext.declarative import declared_attr, declarative_base


class MyBase(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    id =  Column(Integer, primary_key=True, autoincrement=True)
    date_creat = Column(DateTime, default=datetime.datetime.utcnow)
    user = Column(String)

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base(cls=MyBase)


class BuyOrSell(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
class TradeState(enum.Enum):
    OPEN = "OPEN"
    ORDERED = "ORDERED"
    COMPLETE = "COMPLETE"
class AssetType(enum.Enum):
    CURRENCY = "CURRENCY"
    CRYPTO = "CRYPTO"
    EQUITY = "EQUITY"
    BUNDS = "BUNDS"
class OrderType(enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    OPTION = "OPTION"
    
class Order(Base):  # pylint: disable=too-few-public-methods
    __tablename__ = "orders"
    ticker = Column(String, nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    order_type = Column(String)
    buy_or_sell = Column(Enum(BuyOrSell))
    state = Column(Enum(TradeState))
    price = Column(Float)
    quantity = Column(Float)
    amount = Column(Float)
    order_date = Column(DateTime)
    def __init__(self, ticker: String, asset_type: String, order_type: String, buy_or_sell: String, state: String, price: float, quantity: float, amount: float, order_date: datetime, user:String):
        self.ticker = ticker
        self.asset_type = asset_type
        self.order_type = order_type
        self.buy_or_sell = buy_or_sell
        self.state = state
        self.price = price
        self.quantity = quantity
        self.amount = amount
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

class ErrorLog(Base):  # pylint: disable=too-few-public-methods
    __tablename__ = "error_log"
    log_date = Column(String)
    log_type = Column(String)
    script_name = Column(String)
    func_name = Column(String)
    line = Column(Integer)
    log_message = Column(String)
    def __init__(self, log_date: String, log_type: String, script_name: String, func_name: String, line: Integer, log_message: String, user:String):
        self.log_date = log_date
        self.log_type = log_type
        self.script_name = script_name
        self.func_name = func_name
        self.line = line
        self.log_message = log_message
        self.user = user
    def info(self):
        return {
            "id": self.id,
            "log_date": self.log_date,
            "log_type": self.log_type.info(),
            "log_message": self.log_message.info(),
            "datetime": self.date_time.isoformat(),
        }
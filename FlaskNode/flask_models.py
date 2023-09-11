#!/usr/bin/env python
# coding:utf-8

import enum, datetime
from typing import Dict
from requests import session
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, \
    Float, ForeignKey, Integer, String, func, or_, select
from sqlalchemy.orm import column_property, relationship
from sqlalchemy.ext.declarative import declared_attr, declarative_base


class Base(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_creat = Column(DateTime, default=datetime.datetime.utcnow)
    user = Column(String)

from sqlalchemy.ext.declarative import declarative_base
Schema = declarative_base(cls=Base)


class BuyOrSell(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
class TradeState(enum.Enum):
    STARTING = "STARTING"
    ORDERED = "ORDERED"
    COMPLETE = "COMPLETE"

class Base(Schema):  # pylint: disable=too-few-public-methods
    __tablename__ = "flask_demo"
    ticker = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)
    order_type = Column(String)
    buy_or_sell = Column(Enum(BuyOrSell))
    state = Column(Enum(TradeState))
    price = Column(Float)
    order_date = Column(DateTime)
    def __init__(self, ticker: String, asset_type: String, order_type: String, buy_or_sell: String, state: String, price: float, order_date: datetime, user:String):
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

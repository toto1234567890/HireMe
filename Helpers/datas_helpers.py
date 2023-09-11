#!/usr/bin/env python
# coding:utf-8


####################################################################
################# Save Trade messages in database ##################
# -- Decorator for Database object --
from datetime import datetime
default_order = {"ticker":"default", "asset_type":"crypto", "order_type":"long", "buy_or_sell":"buy", "state":"buy", "price":3.14, "quantity":-1, "amount":-1, "order_date":datetime.utcnow()}
def TradeToDB(f, *args, **kwargs):
    def wrap(self, **msg):
        try:
            final_msg = {**default_order, **msg}
            return f(self, **final_msg)
        except Exception as e:
            self.logger.warning("Database : '{0}' error while trying to save Trade record '{1}' in database  : {2}".format(self.user, str(msg), e))
    return wrap
################# Save Trade messages in database ##################
####################################################################
################# Save FIX messages in database ####################
# -- Decorator for Database object --
#@FixMsgToDB
#def db_fix_message(self, MsgSeqNum: BigInteger, BeginString: String,  BodyLength: Integer, MsgType: String, MsgDate: DateTime, SentOrReceived: String, FixMessageStr: String):
#    session: Session
#    with self.db_session() as session:
#        session.add(FixMessagee(self.db_endpoint, MsgSeqNum, BeginString, BodyLength, MsgType, MsgDate, SentOrReceived, FixMessageStr, self.user))
def FixToDB(f, *args, **kwargs):
    def wrap(self, **msg):
        try:
            if msg.startswith("FIX message"):
                fix = msg.split(":", 1)[1]  ;  db_rec = dict(x.split("=") for x in fix.split("|"))  ;  MSgSens = msg.split(":")[0]
                return f(self, 
                    BeginString = db_rec.get(' 8', ""),
                    BodyLength = int(db_rec.get('9', -1)),
                    MsgType = db_rec.get('35', ""),
                    MsgSeqNum = int(db_rec.get('34', -1)),
                    MsgDate = datetime.strptime(db_rec.get('52', "19000101-00:00:00.000"), "%Y%m%d-%H:%M:%S.%f"),
                    SentOrReceived = ("Sent" if "sent" in MSgSens.lower() else "Received"),
                    FixMessageStr = fix
                    )
        except Exception as e:
            self.logger.warning("Database : '{0}' error while trying to save Trade record '{1}' in database  : {2}".format(self.user, str(msg), e))
            pass
    return wrap
################# Save FIX messages in database ####################
####################################################################
#################### PreLoad of dataframe ##########################
from collections import OrderedDict
class PreDataFrame:
    """
    init with columns : \n
    x = PreDataFrame("ticker", "exchange")\n
    dataF = pd.DataFrame(x.__dict__)\n
    add function if necessary (every function name should start with "func*") : \n
    x = PreDataFrame("ticker", "exchange", "func0"=toto, "func1"=tata...) \n
    e.g: \n
    data3={'data3':{'h3': [11,212,3124,31234], 'o3': [11,212,3124,31234], 'l3': [11,212,3124,31234], 'c3': [11,212,3124,31234], 'v3': [11,212,3124,31234]}}
    y = PreDataFrame('o','h','l','c','v', format=format)
    y.format(y, data3)
    x = pd.DataFrame(y())
    """
    res=OrderedDict()
    def __init__(self, *args, **kwargs):  
        for x in args:
            self.__dict__.update({x:[]})
        self.__dict__.update(kwargs)
    def tuple_of_tuple_first_entry_columns_name(self, datas:tuple):
        for x in datas:
            self.res[x[0]] = x[1:]
    def tuple_of_dict_key_level1_columns_name(self, datas:tuple):
        for tuplee in datas:
            for key, val in tuplee.items():
                self.res[key] = val
    def dict_of_tuple_of_dict_key_level2_columns_name(self, datas:dict):
        for dataset in datas.values():
            for tuplee in dataset:
                for key, val in tuplee.items():
                    self.res[key] = val
    def display(self):
        for key, val in self.__dict__.items():
            if not key.startswith("func") and key!= "Datas":
                self.res[key]=val
    def result(self): 
        for key, val in self.__dict__.items():
            if not key.startswith("func"):
                self.res[key]=val
        return self.res
    def format(self, *args, **kwargs):
        raise NotImplemented
    def __call__(self, *args, **kwds):
        return self.res
#################### PreLoad of dataframe ##########################
####################################################################
############ For file in folder load dataframe... ##################
from common.Helpers.helpers import load_pickle_from_file
from os import curdir, walk as osWalk
from os.path import join as osPathJoin
def load_pickle_from_dir(root:str, PreDataExtractFunc, recurs:bool=False, notInDirFilter:list=None, InDirFilter:list=None, notInFileFilter:list=None, InFileFilter:list=None):
    for root, dirs, files in osWalk(root, topdown=recurs):
        # directories
        if not notInDirFilter is None:
            dirs[:] = [d for d in dirs if d not in notInDirFilter]
        if not InDirFilter is None:
            dirs[:] = [d for d in dirs if d in InDirFilter]
        # files
        if not notInFileFilter is None:
            files[:] = [f for f in files if f not in notInFileFilter]
        if not InFileFilter is None:
            files[:] = [f for f in files if f in InFileFilter]
        
        for filename in files:
            filePath = osPathJoin(root, filename)
            if filePath.endswith(".pkl"): 
                don = load_pickle_from_file(filePath)
                PreDataExtractFunc(x=don)
    return PreDataExtractFunc
############ For file in folder load dataframe... ##################
####################################################################
#################### Load Schema from file #########################
from os import sep as osSep
from sys import modules
from importlib.util import spec_from_file_location, module_from_spec
def load_schema_from_file(file_path):
    model = (file_path.split(osSep)[-1:])[0].replace(".py", '')
    spec = spec_from_file_location(model, file_path)
    module = module_from_spec(spec)
    modules[model] = module
    spec.loader.exec_module(module)
    return module
#################### Load Schema from file #########################
####################################################################


#!/usr/bin/env python
#coding:utf-8

from os import sep as osSep
from datetime import datetime
from retry import retry
from asyncio import run as asyncioRun, Lock as asyncioLock, sleep as asyncioSleep, \
                    get_running_loop as asyncioGet_running_loop, Event as asyncioEvent


# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import init_logger, getSplitedParam
from common.Helpers.network_helpers import MyAsyncSocketObj
from trading.trading_helpers import get_async_exchanges_by_name



import websocket, re, os, threading, time, rel, string, secrets
from datetime import datetime
from collections import deque
from os.path import join as osPathJoin

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.Database.database import Database
from common.ThreadQs.thread_Qs import StarQs, SubsQ
from common.Helpers.proxy import getWSSProxy


WSS_PROXY_ITER=getWSSProxy()

# Shared variable and lock
name = None
enabled = False
config = None
logger = None
# Lock globals
asyncStop = asyncioEvent()
asyncLock = asyncioLock()
asyncLoop = None
asyncSleep = None
# List to store data
brokerList = None
tickerList = None
data = []



class wsAppDispatcher:
    Name = "TradingView"
    def __init__(self, logger:MyLogger, config:Config, exchange, asset):
        self.Name += " : " + exchange + "|" + asset 
        self.ticker = exchange + ":" + asset 
        self.logger = logger
        self.config = config
        self.sID = self.generate_sId()
        self.MsgSent = None

    def __call__(*args):
        temp = args[0]
        temp.wsapp = args[1]
        if len(args)==2:
            temp.on_open()
        elif len(args)==3 and type(args[2])==str:
            temp.on_message(args[2])
        elif len(args)==3 and type(args[2])!=str:
            temp.on_message(args[2])
        elif len(args)==4:
            temp.on_close(args[2], args[3])
            exit()
        else:
            temp.logger.error("{0} unexpected error received while dispatching trading view wss message...".format(temp.name))
            pass

    def generate_sId(self):
        alphabet = string.ascii_letters + string.digits
        return "qs_" + ''.join(secrets.choice(alphabet) for i in range(12))

    def on_open(ws):
        ws.logger.info("{0} webSocket connection established on : '{1}'".format(ws.Name, ws.wsapp.url))
        
    def on_message(ws, message):
        msg = ""
        if ws.MsgSent is None:
            # set_auth_token 
            ws.MsgSent = "set_auth_token"
            msg = '~m~54~m~{"m":"'+ws.MsgSent+'","p":["unauthorized_user_token"]}'
            ws.wsapp.send(msg.encode())
            ws.logger.info("{0} websocket message sent '{1}'".format(ws.Name, msg))
        elif ws.MsgSent == "set_auth_token":
            # quote_create_session 
            ws.MsgSent = "quote_create_session"
            msg = '~m~52~m~{"m":"'+ws.MsgSent+'","p":["'+ws.sID+'"]}'
            ws.wsapp.send(msg.encode())     
            ws.logger.info("{0} websocket message sent '{1}'".format(ws.Name, msg))     
        elif ws.MsgSent == "quote_create_session" :
            # quote_add_symbols 
            ws.MsgSent = "quote_add_symbols"
            msg = '~m~63~m~{"m":"'+ws.MsgSent+'","p":["'+ws.sID+'","'+ws.ticker+'"]}'
            ws.wsapp.send(msg.encode()) 
            ws.logger.info("{0} websocket message sent '{1}'".format(ws.Name, msg))
        elif ws.MsgSent == "quote_add_symbols" and re.match(r'.+\{"m":"quote_completed","p":\["%s","%s"\]\}$'%(ws.sID, ws.ticker), message):
            # write_to_file(message, ws) send datas.....
            ws.logger.info("{0} '{1}' ticker datas received !".format(ws.Name, ws.ticker))
            ws.wsapp.close()
            ws.wsapp.keep_running = False
        else:
            ws.logger.info("{0} not expected websocket message received '{1}'".format(ws.Name, message))
            ws.wsapp.close()
            ws.wsapp.keep_running = False

    def on_error(ws, error):
        ws.logger.error("{0} error message received on websocket '{1}'".format(ws.name, error))

    def on_close(ws, close_status_code, close_msg):
        ws.logger.info("{0} connection closed ! '{1}' status '{2}'".format(ws.Name, (close_msg or "empty close_msg"), close_status_code))


def trading_view_loader(name, config:Config, logger:MyLogger):
    global asyncLoop ; global asyncSleep ; global brokerList
    global config ; global logger
    global enabled
    enabled = True
    asyncLoop = asyncioGet_running_loop()
    wss_url = config.get_mem_config(section_key_list={name:["WSS_BASE_URL"]})
    #def __init__(self, logger, config, exchange, asset):
    AppDispatcher = wsAppDispatcher(logger, config, exchange, asset)
    ws = websocket.WebSocketApp("{0}/websocket?from=symbols%2F{2}-{3}%2Ffinancials-income-statement%2F&date={1}". \
                                    format(wss_url, datetime.utcnow().strftime("%Y_%m_%d-%H_%M"), exchange, asset),
                                    on_open=AppDispatcher,
                                    on_message=AppDispatcher,
                                    on_error=AppDispatcher,
                                    on_close=AppDispatcher)
    #proxy = next(WSS_PROXY_ITER)                        
    ws.run_forever(dispatcher=rel)#, http_proxy_host=proxy[0], http_proxy_port=proxy[1])
    rel.dispatch() 
    ws.keep_running

#================================================================
if __name__ == "__main__":
    from sys import argv
    from os import sep as osSep

    name = __file__.split(osSep)[-1:][0][:-3]
    configStr = "analyst"

    if len(argv) == 2: name = argv[1]
    name = name.lower()

    config, logger = init_logger(name=name, config="analyst")

    config.update_mem_config(section_key_val_dict={name:{"CONFIG_REFRESH":"3"}})
    config.update_mem_config(section_key_val_dict={name:{"WSS_BASE_URL":"wss://data.tradingview.com/socket.io"}})
    config.update_mem_config(section_key_val_dict={name:{"WATCH_LIST_TABLE":"3"}})
    config.update_mem_config(section_key_val_dict={name:{"WATCH_LIST_ENABLED":"3"}})
    #asyncSleep = float((config.get_mem_config(section_key_list={name:["CONFIG_REFRESH"]})).get(name).get("CONFIG_REFRESH"))

    asyncioRun(trading_view_loader(name=name))

######################################################################
if __name__=="__main__":


    StarQ = StarQs(logger, config)

    Tv_Handlers = TradingViewScrapper(StarQ, logger, config)
    
    Tototrader = SubsQ("Essai", StarQ, "TradingViewScrapper")
    #Tototrader.send_msg_in(["NYSE","INFY"])
    #Tototrader.send_msg_in(["BSE","ADANIPORTS"])
    #Tototrader.send_msg_in(["NASDAQ","TSLA"])
    #Tototrader.send_msg_in(["NSE","INFY"])
    Tototrader.send_msg_in(["NASDAQ","HRTX"])
    time.sleep(1)
    Tototrader.send_msg_in(["NASDAQ","USEA"])
    time.sleep(1)
    Tototrader.send_msg_in(["NASDAQ","TSLA"])
    time.sleep(1)
    Tototrader.send_msg_in(["NASDAQ","GOOG"])
    time.sleep(1)
    Tototrader.send_msg_in(["NASDAQ","NFLX"])
    #time.sleep(1)
    #Tototrader.send_msg_in(["NASDAQ","AMD"])
    time.sleep(1)
    Tototrader.send_msg_in(["NASDAQ","NVDA"])
    #Tototrader.unSubs()



    #liste=[["NASDAQ","TSLA"], ["NASDAQ","NDQA"], ["NASDAQ","AMZN"], ["NASDAQ","GOOG"], ["NASDAQ","NFLX"], ["NASDAQ","AMD"], ["NASDAQ","NVDA"]]




    #loop = asyncio.get_event_loop()
    #try:
    #    loop.run_until_complete(start_extract(liste))
    #except Exception as e:  
    #    logger.error("{0} : error message received on main async loop  : '{1}'".format(name, e))    
    #finally:
    #    loop.close()
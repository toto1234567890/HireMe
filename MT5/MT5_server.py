#!/usr/bin/env python
# coding:utf-8

#FIXME add caffeine for windows (caffeine MT5? or windows ?)
#caffeinMe(pid=osGetpid())

from time import sleep
from datetime import datetime
from os import getcwd as osGetcwd
from os.path import join as osPathJoin, dirname as osPathDirname
from platform import system as platformSystem
from uuid import uuid4
from multiprocessing import Process as mltProcess
from asyncio import get_running_loop as asyncioGet_running_loop, sleep as asyncioSleep, open_connection as asyncioOpen_connection, \
                    start_server as asyncioStart_server, run as asyncioRun, Lock as asyncioLock
import MetaTrader5 as mt5


# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.Database.database import Database
from common.ThreadQs.routing_rules import LostQmsg
from common.Helpers.helpers import init_logger, caffeinMe
from common.Helpers.os_helpers import is_process_running, start_independant_process, host_has_proxy
from common.Helpers.network_helpers import SafeAsyncSocket, SSL_server_context


##############################################################################################################################################################################################
# MT5 windows function : https://www.mql5.com/en/docs/python_metatrader5

# initialize : Establish a connection with the MetaTrader 5 terminal
# login : Connect to a trading account using specified parameters
# shutdown : Close the previously established connection to the MetaTrader 5 terminal
# version : Return the MetaTrader 5 terminal version
# last_error : Return data on the last error

# account_info : Get info on the current trading account
# terminal_Info : Get status and parameters of the connected MetaTrader 5 terminal

# symbols_total : Get the number of all financial instruments in the MetaTrader 5 terminal
# symbols_get : Get all financial instruments from the MetaTrader 5 terminal
# symbol_info : Get data on the specified financial instrument
# symbol_info_tick : Get the last tick for the specified financial instrument
# symbol_select : Select a symbol in the MarketWatch window or remove a symbol from the window

# market_book_add : Subscribes the MetaTrader 5 terminal to the Market Depth change events for a specified symbol
# market_book_get : Returns a tuple from BookInfo featuring Market Depth entries for the specified symbol
# market_book_release : Cancels subscription of the MetaTrader 5 terminal to the Market Depth change events for a specified symbol

# copy_rates_from : Get bars from the MetaTrader 5 terminal starting from the specified date
# copy_rates_from_pos : Get bars from the MetaTrader 5 terminal starting from the specified index
# copy_rates_range : Get bars in the specified date range from the MetaTrader 5 terminal
# copy_ticks_from : Get ticks from the MetaTrader 5 terminal starting from the specified date
# copy_ticks_range : Get ticks for the specified date range from the MetaTrader 5 terminal

# orders_total : Get the number of active orders.
# orders_get : Get active orders with the ability to filter by symbol or ticket
# order_calc_margin : Return margin in the account currency to perform a specified trading operation
# order_calc_profit : Return profit in the account currency for a specified trading operation
# order_check : Check funds sufficiency for performing a required trading operation
# order_send : Send a request to perform a trading operation.

# positions_total : Get the number of open positions
# positions_get : Get open positions with the ability to filter by symbol or ticket
# history_orders_total : Get the number of orders in trading history within the specified interval
# history_orders_get : Get orders from trading history with the ability to filter by ticket or position
# history_deals_total : Get the number of deals in trading history within the specified interval
# history_deals_get : Get deals from trading history with the ability to filter by ticket or position


# MT5 only works with windows
MT5_SERVER_NAME = "MT5_server"
MT5_PROCESS_NAME = "terminal64.exe"
if platformSystem() == "Linux":
    MT5_PROCESS_EXE = osPathJoin(osPathDirname(osPathDirname(osGetcwd())),".wine","dosdevices","c:", "Program Files", "MetaTrader 5" , MT5_PROCESS_NAME)
else:
    MT5_PROCESS_EXE = osPathJoin("C:\\", "Program Files", "MetaTrader 5" , MT5_PROCESS_NAME)

asyncLoop = None ; asyncSleep = 0.1

lockTaskList = asyncioLock() ; taskList = {}
lockQuoteCache = asyncioLock() ; quoteCache = {}

accounts_infos = {}
async_tcp_server = None


class Qmsg:
    def __init__(self, msg, frome, too, ackw=None, priority=False):
        self.id = uuid4()
        self.msg = msg
        self.frome = frome
        self.too = too
        self.ackw = ackw
        self.priority = priority

##############################################################################################################################################################################################
# MT5 commands
async def stream_cache(symbol, quote):
    global lockQuoteCache ; global quoteCache
    async with lockQuoteCache:
        quoteCache[symbol] = quote

async def stream_task(task_name, task=None, stop:bool=False):
    global lockTaskList ; global taskList ; global logger
    # save == delete have to be different
    async with lockTaskList:
        if stop:
            try:
                task = taskList.pop(task_name)
                task.cancel()
                await task
            except Exception as e:
                await logger.asyncError("{0} : stream_task error while trying to cancel task '{1}' : {2}".format(MT5_SERVER_NAME, task_name, e))
        else:
            try:
                taskList[task_name] = task
            except Exception as e:
                task.cancel()
                await task
                await logger.asyncError("{0} : stream_task error while trying to register task '{1}' : {2}".format(MT5_SERVER_NAME, task_name, e))

async def async_stream(asyncSock, symbol):
    cptErr = 0
    last = {'time': 0, 'bid': 0, 'ask': 0, 'last': 0, 'volume': 0, 'time_msc': 0, 'flags': 0, 'volume_real': 0}
    while True:
        try:
            tick_data = mt5.symbol_info_tick(symbol)._asdict()
            if tick_data['bid'] != last['bid'] or tick_data['ask'] != last['ask']:
                tick_data["symbol"] = symbol
                await asyncSock.send_data(tick_data)
                await stream_cache(symbol=symbol, quote=tick_data)
                last = tick_data
            #await logger.asyncInfo("{0} : async_stream received data for '{1}' : {2}".format(MT5_SERVER_NAME, symbol, tick_data))
            cptErr = 0
        except Exception as e:
            if mt5.symbol_info_tick(symbol) == None:
                msg = "{0} : unknown symbol '{1}', please check...".format(MT5_SERVER_NAME, symbol, e)
                await asyncSock.send_data(msg)
                await logger.asyncError(msg)
                break
            else:
                await logger.asyncError("{0} : async_stream error while trying to get or send quote '{1}' : {2}".format(MT5_SERVER_NAME, symbol, e))
                cptErr+=1 
                if cptErr > 15: break # more than 5 minutes
                continue
        await asyncioSleep(asyncSleep)

def get_info(symbol):
    pass

async def buy(orderID, symbol, volume, price=None, sl=None, tp=None, deviation=None):
    global logger
    ret = mt5.order_send(
        { 
            "action": mt5.TRADE_ACTION_DEAL,                                            # immediat buy
            "symbol": symbol, 
            "volume": float(volume),                                                    # lot size currency 100 000 so 1 000 = 0.01
            "type": mt5.ORDER_TYPE_BUY, 
            "price": float(0) if price is None else float(price),                       # buy price, if not provided 0 => market order
            "sl": float(0) if sl == None else float(sl),                                # stop loss    doc example => price + 100 * pip,
            "tp": float(0) if tp == None else float(tp),                                # take profit   doc example => price + 100 * pip,
            "deviation": int(0) if deviation == None else int(deviation),               # Fill order if price has changed between deviation..               
            "magic": 122,                                                               # UUID in QMsg 
            "comment": "python script sell",             
            "type_time": mt5.ORDER_TIME_GTC,                                            # MT5 time
            "type_filling": mt5.ORDER_FILLING_IOC                                       # Fill or Kill
        }
    ) 
    if ret == None:
        last_error = mt5.last_error()
        await logger.asyncError("{0} : error while trying to place buy order '{1}' : {2}".format(MT5_SERVER_NAME, orderID, last_error))
        return last_error._asdict()
    ret = ret._asdict()
    details = ret.pop('request')
    return {**ret, **(details._asdict())}

async def sell(orderID, symbol, volume, price=None, sl=None, tp=None, deviation=None):
    global logger
    ret = mt5.order_send(
        { 
            "action": mt5.TRADE_ACTION_DEAL,                                            # immediat sell
            "symbol": symbol, 
            "volume": float(volume),                                                           # lot size currency 100 000 so 1 000 = 0.01
            "type": mt5.ORDER_TYPE_SELL, 
            "price": float(0) if price == None else float(price),                       # sell price, if not provided 0 => market order
            "sl": float(0) if sl == None else float(sl),                                # stop loss    doc example => price + 100 * pip,
            "tp": float(0) if tp == None else float(tp),                                # take profit   doc example => price + 100 * pip,
            "deviation": int(0) if deviation == None else int(deviation),               # Fill order if price has changed between deviation..               
            "magic": 125,                                                               # UUID in QMsg 
            "comment": "python script sell",            
            "type_time": mt5.ORDER_TIME_GTC,                                            # MT5 time
            "type_filling": mt5.ORDER_FILLING_IOC                                       # Fill or Kill
        }
    ) 
    if ret == None:
        last_error = mt5.last_error()
        await logger.asyncError("{0} : error while trying to place sell order '{1}' : {2}".format(MT5_SERVER_NAME, orderID, last_error))
        return last_error._asdict()
    ret = ret._asdict()
    details = ret.pop('request')
    return {**ret, **(details._asdict())}

async def close_position(BrokerOrderID, orderType, symbol, volume, price=None, deviation=None):
    global logger
    ret = mt5.order_send(
        {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "position": int(BrokerOrderID),
            "volume": float(volume),
            "type": mt5.ORDER_TYPE_SELL if orderType == "SELL" else mt5.ORDER_TYPE_BUY,
            "price": float(0 ) if price == None else float(price),
            "deviation": int(deviation),
            "type_filling": mt5.ORDER_FILLING_IOC ,
            "type_time": mt5.ORDER_TIME_GTC
        }
    ) 
    if ret == None:
        last_error = mt5.last_error()
        await logger.asyncError("{0} : error while trying to place sell order '{1}' : {2}".format(MT5_SERVER_NAME, BrokerOrderID, last_error))
        return last_error._asdict()
    ret = ret._asdict()
    details = ret.pop('request')
    return {**ret, **(details._asdict())}

async def aMT5_funcs(asyncSock, deserialized_data:Qmsg, clientName="MT5 receiver"):
    global asyncLoop ; global MT5_SERVER_NAME ; global taskList ; global config ; global logger
    try:    
        MT5_command = deserialized_data.msg.split('|')
        if MT5_command[0] == "QUOTE":
            await stream_task(task=asyncLoop.create_task(async_stream(asyncSock=asyncSock, symbol=MT5_command[1])), task_name="{0}-{1}".format(MT5_command[0], MT5_command[1]))
            return None
        if MT5_command[0] == "UNQUOTE":
            await stream_task(task_name="QUOTE-{0}".format(MT5_command[1]), stop=True)
            return None
        if MT5_command[0] == "BUY":
            response = await buy(deserialized_data.id, MT5_command[1], MT5_command[2])
            deserialized_data.msg = "{0}|{1}".format(deserialized_data.msg, response)
            return deserialized_data
        if MT5_command[0] == "SELL":
            response = await sell(deserialized_data.id, MT5_command[1], MT5_command[2])
            deserialized_data.msg = "{0}|{1}".format(deserialized_data.msg, response)
            return deserialized_data
        if MT5_command[0] == "CLOSE":
            response = await sell(deserialized_data.id, MT5_command[1], MT5_command[2])
            deserialized_data.msg = "{0}|{1}".format(deserialized_data.msg, response)
            return deserialized_data
        else:
            LostQmsg(deserialized_data)
            await logger.asyncError("{0} : error unknown message received : '{1}'".format(clientName, MT5_command))
    except Exception as e:
        await logger.asyncCritical("{0} : aMT5_funcs error while trying to route Qmsg '{1}' : {2}".format(clientName, deserialized_data, e))
        return None

##############################################################################################################################################################################################
# Async TCP gateway
async def handle_TCP_client(reader, writer):
    global MT5_SERVER_NAME ; global config ; global logger
    asyncSock = SafeAsyncSocket(reader=reader, writer=writer)
    data = await asyncSock.receive_data()
    if not data:
        asyncSock.writer.close()
        await asyncSock.writer.wait_closed()
        return
    clientName, host, port = data.split(':') ; port = int(port)
    await logger.asyncInfo("{0} : '{1}' has established connection without encryption from '{2}' destport '{3}'".format(MT5_SERVER_NAME, clientName, host, port))
    while True:
        data = await asyncSock.receive_data()
        if not data:
            break
        response = await aMT5_funcs(asyncSock=asyncSock, deserialized_data=data)
        if not response is None:
            await asyncSock.send_data(response)
            await logger.asyncInfo("{0} : response '{1}' send to '{2}'".format(MT5_SERVER_NAME, response, clientName))
    asyncSock.writer.close()
    await asyncSock.writer.wait_closed()

async def handle_TCP_ssl_client(reader, writer):
    global MT5_SERVER_NAME ; global config ; global logger
    asyncSock = SafeAsyncSocket(reader=reader, writer=writer)
    data = await asyncSock.receive_data()
    if not data:
        asyncSock.writer.close()
        await asyncSock.writer.wait_closed()
        return
    clientName, host, port = data.split(':') ; port = int(port)
    await logger.asyncInfo("{0} : '{1}' has established connection with encryption '{2}' from '{3}' destport '{4}'".format(MT5_SERVER_NAME, clientName, asyncSock.writer.transport.get_extra_info('ssl_object').version(), clientName, host, port))
    while True:
        data = await asyncSock.receive_data()
        if not data:
            break
        response = await aMT5_funcs(asyncSock=asyncSock, deserialized_data=data)
        if not response is None:
            await asyncSock.send_data(response)
            await logger.asyncInfo("{0} : response '{1}' send to '{2}'".format(MT5_SERVER_NAME, response, clientName))
    asyncSock.writer.close()
    await asyncSock.writer.wait_closed()

########################################################################################################################################
# init MT5 app module
# log accounts
def auto_login():
    global MT5_SERVER_NAME ; global config ; global logger
    for broker, conf in config.parser.items():
        if broker not in ("COMMON", "MT5", "DEFAULT"):
            account=False; pwd=None
            for name_sec, conf_sec in conf.items(): 
                if name_sec == "ACCOUNT": account = conf_sec
                if name_sec == "PASSWORD": pwd = conf_sec
            try:
                login(account=account, pwd=pwd)
            except Exception as e:
                logger.error("{0} : error while trying to log account : '{1}-{2}' : {3}".format(MT5_SERVER_NAME, broker, account, e))
                continue

def login(account, pwd=None):
    global MT5_SERVER_NAME ; global config ; global logger
    try:
        if pwd == None:
            if mt5.login(account):
                logger.info("{0} : account '{1}' connected ! account information => {2}".format(MT5_SERVER_NAME, mt5.account_info()))
        else:
            if mt5.login(account, password=pwd):
                logger.info("{0} : account '{1}' connected ! account information => {2}".format(MT5_SERVER_NAME, mt5.account_info()))
        accounts_infos[account] = mt5.account_info()._asdict()
    except:
        logger.error("{0} : response '{1}' send to '{2}'".format(MT5_SERVER_NAME, mt5.last_error()))

def init_MT5():
    global async_tcp_server ; global config ; global logger
    # launch MT5 app, if not already running
    if not is_process_running(cmdlinePatt=MT5_PROCESS_EXE, processName=MT5_PROCESS_NAME):
        logger.info("{0} : MetaTrader5 app is starting.. .  .".format(MT5_SERVER_NAME, datetime.utcnow()))
        start_independant_process(MT5_PROCESS_EXE)
        logger.info("{0} : MetaTrader5 app has been started at '{1}'".format(MT5_SERVER_NAME, datetime.utcnow()))
    else:         
        logger.info("{0} : MetaTrader5 app is already runnnig...".format(MT5_SERVER_NAME, datetime.utcnow()))
    # initialize MT5 module    
    nbTry = 0
    while True:
        sleep(1)
        try:
            mt5.initialize()
            #mt5.initialize(MT5_PROCESS_EXE,
            #               login=login,
            #               password=password,
            #               server=server,
            #               timeout=timeout,
            #               portable=False)
            break
        except Exception as e:
            nbTry+=1
            if nbTry < 10: 
                continue
            else:
                logger.error("{0} : failed to initialize MT5 connection ({1} times) : {2}".format(MT5_SERVER_NAME, nbTry, e))
                exit(1)
    # connect accounts    
    try:
        auto_login()
    except Exception as e:
        logger.error("{0} : error while trying to initialize MT5 connection : {1}".format(MT5_SERVER_NAME, e))
        #logger.error("{0} : last_error : '{1}'".format(MT5_SERVER_NAME, mt5.last_error()))
        try: mt5.shutdown()
        except: pass
        exit(1)
    else:
        logger.info("{0} : connected to MT5 application version '{1}'".format(MT5_SERVER_NAME, mt5.version()))
        #logger.info("{0} : MT5 terminal infos : {1}".format(MT5_SERVER_NAME, mt5.terminal_info()))

########################################################################################################################################
# main async server
async def run_async_tcp_server(ssl=True):

    init_MT5()

    global async_tcp_server ; global asyncLoop ; global config ; global logger
    asyncLoop = asyncioGet_running_loop()

    try:
        if ssl:
            async_TCP_IP_ssl = '0.0.0.0' ; async_TCP_port_ssl = int(config.parser["MT5"]["MT5_TCP_SSL_PORT"])
            async_tcp_server_ssl = await asyncioStart_server(handle_TCP_ssl_client, async_TCP_IP_ssl, async_TCP_port_ssl, ssl=SSL_server_context())
            await logger.asyncInfo("{0} : socket async SSL TCP handler is open : {1}, srcport {2}".format(MT5_SERVER_NAME, async_TCP_IP_ssl, async_TCP_port_ssl))
            async with async_tcp_server_ssl:
                await async_tcp_server_ssl.serve_forever()
        else:
            async_TCP_IP = '127.0.0.1' ; async_TCP_port = int(config.parser["MT5"]["MT5_TCP_PORT"])
            async_tcp_server = await asyncioStart_server(handle_TCP_client, async_TCP_IP, async_TCP_port)
            await logger.asyncInfo("{0} : socket async TCP handler is open : {1}, srcport {2}".format(MT5_SERVER_NAME, async_TCP_IP, async_TCP_port))
            async with async_tcp_server:
                await async_tcp_server.serve_forever()

    except KeyboardInterrupt:
        await logger.asyncInfo("{0} : has been stopped manually at '{1}'".format(MT5_SERVER_NAME, datetime.utcnow()))
        try: mt5.shutdown()
        except: pass
    except Exception as e:
        await logger.asyncError("{0} : error while trying to start TCP server : '{1}'".format(MT5_SERVER_NAME, e))
        try: mt5.shutdown()
        except: pass
        exit(1)

def start_MT5_server(name=None, ssl=False):
    if not name is None:
        global MT5_SERVER_NAME
        MT5_SERVER_NAME = name
    if ssl:
        proxy, proxyList = host_has_proxy()
        if proxy:
            logger.warning("{0} : you are to starting MT5 server, with ssl but there is proxy on the machine, please configure proxy also : {1}".format(MT5_SERVER_NAME, proxyList))
    asyncioRun(run_async_tcp_server(ssl=ssl))


#================================================================
if __name__ == "__main__":
    from sys import argv
    from os import getpid as osGetpid

    configStr = "current"
    #caffeinMe(pid=osGetpid())

    if len(argv) >= 2:
        MT5_SERVER_NAME = argv[1]
    if len(argv) >= 3:
        configStr = argv[2] 
    if len(argv) >= 4:
        ssl = eval((argv[3]).capitalize()) 
    if len(argv) > 4:
        config, logger = init_logger(name=MT5_SERVER_NAME)
        logger.error("{0} : error while trying to start TCP server, too much parameters provided '{1}' expected max expected 2 : {2}".format(MT5_SERVER_NAME, len(argv), argv))
        exit(1)
        
    config, logger = init_logger(name=MT5_SERVER_NAME, config=configStr)
    start_MT5_server(ssl=ssl)




#!/usr/bin/env python
# coding:utf-8

from datetime import datetime
from os.path import dirname as osPathDirname, join as osPathJoin
from logging import getLogger
from asyncio import run as asyncioRun, Lock as asyncioLock, sleep as asyncioSleep, \
                    get_running_loop as asyncioGet_running_loop
from sqlite3 import connect as sqlite3Connect


# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.Helpers.helpers import init_logger, getSplitedParam, getUnusedPort, standardStr
from common.Helpers.network_helpers import MyAsyncSocketObj
from common.Helpers.retrye import asyncRetry
from trading.trading_helpers import get_async_exchanges_by_name


# Constante alike ...
CONFIG_SECTION = "DATA_LOADER_CRYPTO"

# Shared variable and lock
enable = False ; name = None ; db_file = None ; config = None ; logger = None
# Lock globals
asyncLock = asyncioLock() ; asyncLoop = None ; asyncSleep = None
## Global realTime TA_Ananlyst
RealTimeTA_Socket = None
#TaSocket = SafeAsyncSocket()
# List to store data
brokerList = None ; tickerList = None
dataList = {}


########################################################################
# config update modify carefully !!!
async def update_config(config_updated):
    if type(config_updated) == Config: 
        pass
    else:
        config.mem_config = config_updated
async def from_sync_to_async(config_updated):
    await update_config(config_updated)
def async_config_update(config_updated):
    global asyncLoop
    _ = asyncLoop.create_task(from_sync_to_async(config_updated=config_updated))
# config update modify it carefully !!!
########################################################################
# data update
async def async_post(ticker, record, maxe=12, save_from=6):
    global dataList ; global asyncLock
    global name ; global logger 

    table_name = "{0}_{1}".format(ticker.upper(), record[0].upper())
    sql_statement = "INSERT INTO {0} (broker, ticker, ask, bid, volume, change, date, date_creat, user) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)".format(table_name)

    async with asyncLock:
        try:
            data = dataList[table_name] 
        except:
            data = []
            
        # [key,price,open,high,low,close,volume]
        await send_data_to_TaAnalyst([record[0]+"-"+record[1], record[2], record[2], record[2], record[3], record[3], record[4]])

        data.insert(0, record)
        # (broker, ticker, ask, bid, volume, change, date, date_creat, user)
        #await save_data((data, maxe, save_from, sql_statement, table_name))
        dataList[table_name] = data

# received stream datas from exchanges
async def async_stream(exchange, name, section, brokerName):
    global asyncLoop ; global brokerList
    global config ; global logger
    global enabled 
    while True:
        if not enabled:
            break
        current_brokers = getSplitedParam(config.mem_config[name]["{0}_BROKER_LIST".format(section)])
        if not brokerName in current_brokers:
            brokerList.pop(brokerList.index(brokerName))
            if not exchange is None:
                await exchange.close()
            return
        tickerList = getSplitedParam(config.mem_config[name]["{0}_WATCH_LIST".format(section)])
        for ticker in tickerList:
            if not exchange is None:
                result = await exchange.fetch_ticker(symbol=ticker)
                await async_post(ticker=standardStr(result["symbol"]),record=(standardStr(exchange.name), result["symbol"], result["ask"], result["bid"], result["baseVolume"] or -1, result["percentage"] or -101, datetime.utcnow(), datetime.utcnow(), "ccxt_data_loader"))
        await asyncioSleep(float(config.mem_config[name]["{0}_TIME_INTERVAL".format(section)])) 

@asyncRetry(delay=5, tries=-1)
async def watch_broker(name, section, brokerName, logger):
    global asyncLoop ; global brokerList
    global config 
    global enabled 

    exchange = (get_async_exchanges_by_name[brokerName])()
    async with exchange:
        exchange.userAgent = "MyAgent 3.14"
        # no big logs...
        (getLogger('ccxt')).setLevel(10)
        async_stream_task = asyncLoop.create_task(async_stream(exchange=exchange, name=name, section=section, brokerName=brokerName))
        await async_stream_task

# autoreload of config to check for new params
async def load_params(name, section):
    global asyncLoop ; global asyncSleep ; global brokerList
    global config ; global logger
    global enabled 
    try:
        while True:
            if not enabled:
                break
            try:
                new_brokerList = getSplitedParam(config.mem_config[name]["{0}_BROKER_LIST".format(section)])
            except Exception as e:
                await logger.asyncCritical("{0} : error while trying to load params getSplitedParams : {1}".format(name.capitalize(), e))
            for brokerName in new_brokerList:
                if not brokerName in brokerList:
                    brokerList.append(brokerName)
                    _ = asyncLoop.create_task(watch_broker(name=name, section=section, brokerName=brokerName, logger=logger))
            await asyncioSleep(asyncSleep)
    except Exception as e:
        await logger.asyncCritical("{0} : error while trying to load params : {1}".format(name.capitalize(), e))
        pass

async def prepare_socket(name):
    global RealTimeTA_Socket ; global config
    await logger.asyncInfo("{0} : init connection with real time TA Analyst.. .  . ".format(name))
    RealTimeTA_Socket = await MyAsyncSocketObj(name=name).make_connection(server=config.parser["REALTIMETA"]["RT_TA_SERVER"], port=int(config.parser["REALTIMETA"]["RT_TA_PORT"]))
    senderServer = RealTimeTA_Socket.sock_info[0]
    senderPort = int(RealTimeTA_Socket.sock_info[1])
    await RealTimeTA_Socket.send_data("{0}:{1}:{2}".format(name, senderServer, senderPort))

##########################################################################
# Main function to start the asyncio asyncLoop
async def cctx_data_loader(name, section):
    global asyncLock
    global asyncLoop ; global asyncSleep ; global brokerList
    global config ; global logger
    global enabled ; enabled = True 

    asyncSleep = float(config.MAIN_QUEUE_BEAT)
    asyncLoop = asyncioGet_running_loop()

    config.set_updateFunc(async_config_update)

    await prepare_socket(name)

    try :
        # main ccxt
        initial_brokers = getSplitedParam(config.mem_config[name]["{0}_BROKER_LIST".format(section)])
        brokerList = initial_brokers
        for brokerName in initial_brokers:
            _ = asyncLoop.create_task(watch_broker(name=name, section=section, brokerName=brokerName, logger=logger))

        # config refresh
        _ = asyncLoop.create_task(load_params(name=name, section=section))
    except Exception as e:
        await logger.asyncCritical("{0} : error while trying to init streams : {1}".format(name.capitalize(), e))
        enabled = False
        exit(1)

    try:
        while True:
            if not enabled:
                asyncLoop.stop()
                await logger.asyncInfo("{0} : asyncio loop have been stopped at {1} !".format(name.capitalize(), datetime.utcnow()))
                break
            await asyncioSleep(5)
    except Exception as e:
        await logger.asyncCritical("{0} : error while trying to stop asyncio loop...".format(name.capitalize(), datetime.utcnow()))

########################################################################
# process datas...
@asyncRetry(delay=5, tries=-1)        
async def send_data_to_TaAnalyst(data):
    global RealTimeTA_Socket
    try:
        await RealTimeTA_Socket.send_data(data)
    except:
        RealTimeTA_Socket.writer.close()
        await RealTimeTA_Socket.writer.wait_closed()
        await asyncSleep(1)
        await prepare_socket(name)
        await RealTimeTA_Socket.send_data(data)

async def save_data(*args):
    global logger ; global db_file 
    global CONFIGFILE ; global name 
    data, maxe, save_from, sql_statement, table_name = args

    if len(data) > maxe:
        data2save = data[save_from:]
        data = data[:save_from]
        data2save = data2save[::-1]
        try:
            with sqlite3Connect(db_file) as db:
                cursor = db.cursor()
                cursor.executemany(sql_statement, data2save)
                cursor.execute("COMMIT")
        except Exception as e:
            try:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS {0} (
                	id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broker TEXT NOT NULL,
                   	ticker TEXT NOT NULL,
                    ask REAL NOT NULL,
                    bid REAL NOT NULL,
                    volume REAL NOT NULL,
                    change REAL,
                    date DATETIME,
                    date_creat DATETIME NOT NULL,
                    user DATETIME NOT NULL)
                """.format(table_name))
                cursor.executemany(sql_statement, data2save)
                cursor.execute("COMMIT")
            except Exception as e:
                logger.critical("{0} : error while trying to save records in table {1} in '{2}.db' : {2}".format(name.capitalize(), table_name, CONFIGFILE.lower(), e))
                exit(1)

#================================================================
if __name__ == "__main__":
    from sys import argv
    CONFIGFILE = "analyst"

    from os.path import basename as osPathBasename
    name = (osPathBasename(__file__)).split('.')[0]

    if len(argv) == 2: 
        name = argv[1]
    name = name.lower()

    # loading config and logger
    config, logger = init_logger(name=name, config=CONFIGFILE)
    mem_section = name.upper()

    if config.mem_config == None or not name in config.mem_config:
        config.update_mem_config(section_key_val_dict={name:{"{0}_BROKER_LIST".format(mem_section):'binance,bybit,bitget,coinbasepro,okx,kucoin,phemex', 
                                                             "{0}_TIME_INTERVAL".format(mem_section):5,
                                                             "{0}_WATCH_LIST".format(mem_section):'BTC/USDT;ETH/USDT;ETH/BTC'}})

    db_file = osPathJoin(osPathDirname(osPathDirname(__file__)), "{0}.db".format(CONFIGFILE.lower()))    

    current_port = getUnusedPort()
    config.update(section=CONFIG_SECTION, configPath=config.COMMON_FILE_PATH, params={"{0}_DBFILE".format(CONFIG_SECTION):db_file, "{0}_PORT".format(CONFIG_SECTION):current_port})

    asyncioRun(cctx_data_loader(name=name, section=mem_section))







    
 
#!/usr/bin/env python
# coding:utf-8

from time import sleep
from datetime import datetime
from os import getcwd as osGetcwd
from os.path import dirname as osPathDirname, join as osPathJoin
from logging import getLogger
from asyncio import run as asyncioRun, Lock as asyncioLock, sleep as asyncioSleep, \
                    get_running_loop as asyncioGet_running_loop
from sqlite3 import connect as sqlite3Connect
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS


# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.Helpers.helpers import init_logger, getSplitedParam, threadIt, getUnusedPort, getAlgo, module_from_file, standardStr
from common.Helpers.os_helpers import get_executed_script_dir
from common.Helpers.ipt_helpers import host_has_ipt
from common.Helpers.retrye import asyncRetry
from common.Utilities.discord import DiscoLogger
from trading.trading_helpers import get_async_exchanges_by_name
from trading.Arbitre.template import write_template
from trading.TeleRemote.tele_trading import stop_arbitre, start_arbitre

from trading.Arbitre.strategies import *

# Constante alike ...
MAIN_TEMPLATE = "main.html"
CONFIG_SECTION = "ARBITRE"
strategy = "default only up"

# Discord
Disco_log = None

# Shared variable and lock
enable = False ; name = None ; db_file = None ; config = None ; logger = None
# Lock globals
asyncLock = asyncioLock() ; asyncLoop = None ; asyncSleep = None
# List to store data
brokerList = None ; tickerList = None
data = []
# retry on error
check_ipt = True

last_asks = {} ; last_bids = {} 
ask_dir = {} ; bid_dir = {}
min_ask = [] ; max_ask = []
min_bid = [] ; max_bid = []


# override by trading.Arbitre.strategies.*
def tradeOrNot(record, strategy, last_asks, last_bids, ask_dir, bid_dir,
                min_ask, max_ask, min_bid, max_bid):
    pass


########################################################################
# config update modify carefully !!!
async def update_config(config_updated):
    if type(config_updated) == Config: 
        pass
    else:
        global data ; global config ; global asyncLock
        global last_asks ; global last_bids 
        global ask_dir ; global bid_dir
        global min_ask ; global max_ask 
        global min_bid ; global max_bid
        data = []
        last_asks = {} ; last_bids = {} 
        ask_dir = {} ; bid_dir = {}
        min_ask = [] ; max_ask = []
        min_bid = [] ; max_bid = []
        config.mem_config = config_updated
        stratModule.ab_config_refresh(**sharedVar)
async def from_sync_to_async(config_updated):
    await update_config(config_updated)
def async_config_update(config_updated):
    global asyncLoop
    _ = asyncLoop.create_task(from_sync_to_async(config_updated=config_updated))
# config update modify it carefully !!!
########################################################################
# data update
async def async_post(record):
    global data ; global strategy

    global name
    global logger ; global Disco_log
    global last_asks ; global last_bids 
    global ask_dir ; global bid_dir
    global min_ask ; global max_ask 
    global min_bid ; global max_bid

    async with asyncLock:
        tradeOrNot(record=record, strategy=strategy, last_asks=last_asks, last_bids=last_bids, ask_dir=ask_dir, bid_dir=bid_dir, 
                   min_ask=min_ask, max_ask=max_ask, min_bid=min_bid, max_bid=max_bid)
        data.insert(0, record)

# received stream datas from exchanges
async def async_stream(exchange, name, section, brokerName):
    global asyncLoop ; global asyncSleep ; global brokerList
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
                await async_post((standardStr(exchange.name), result["symbol"], result["ask"], result["bid"], datetime.utcnow(), datetime.utcnow(), "arbitre"))
        await asyncioSleep(float(config.mem_config[name]["{0}_TIME_INTERVAL".format(section)])) 

@asyncRetry(delay=5, tries=-1)
async def watch_broker(name, section, brokerName, logger, check_ipt):
    global asyncLoop ; global asyncSleep ; global brokerList
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
    global check_ipt
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
                    _ = asyncLoop.create_task(watch_broker(name=name, section=section, brokerName=brokerName, logger=logger, check_ipt=check_ipt))
            await asyncioSleep(asyncSleep)
    except Exception as e:
        await logger.asyncCritical("{0} : error while trying to load params : {1}".format(name.capitalize(), e))
        pass

##########################################################################
# Main function to start the asyncio asyncLoop
async def arbitre(name, section):
    global asyncLock
    global asyncLoop ; global asyncSleep ; global brokerList
    global config ; global logger
    global check_ipt
    global enabled ; enabled = True 

    asyncSleep = float(config.MAIN_QUEUE_BEAT)
    asyncLoop = asyncioGet_running_loop()

    config.set_updateFunc(async_config_update)

    try :
        # main ccxt
        initial_brokers = getSplitedParam(config.mem_config[name]["{0}_BROKER_LIST".format(section)])
        brokerList = initial_brokers
        for brokerName in initial_brokers:
            _ = asyncLoop.create_task(watch_broker(name=name, section=section, brokerName=brokerName, logger=logger, check_ipt=check_ipt))

        # config refresh
        _ = asyncLoop.create_task(load_params(name=name, section=section))
    except Exception as e:
        await logger.asyncCritical("{0} : error while trying to init streams : {1}".format(name.capitalize(), e))
        enabled = False
        exit(1)

    try:
        while True:
            if not enabled:
                func = request.environ.get('werkzeug.server.shutdown')
                func() ; asyncLoop.stop()
                await logger.asyncInfo("{0} : webserver and asyncio loop have been stopped at {1} !".format(name.capitalize(), datetime.utcnow()))
                break
            await asyncioSleep(asyncSleep)
    except Exception as e:
        await logger.asyncCritical("{0} : error while trying to stop webserver and asyncio...".format(name.capitalize(), datetime.utcnow()))

##########################################################################
# database updater
@threadIt
def start_db_updater(maxe=200, save_from=100):
    global CONFIG_SECTION
    global name ; global db_file
    global logger ; global config
    global data ; data2save = None

    sql_statement = "INSERT INTO {0} (broker, ticker, ask, bid, date, date_creat, user) VALUES (?, ?, ?, ?, ?, ?, ?)".format(name)

    while True:
        sleep(float(config.parser[CONFIG_SECTION]["{0}_DBREFRESH".format(CONFIG_SECTION)]))
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
                        date DATETIME,
                        date_creat DATETIME NOT NULL,
                        user DATETIME NOT NULL)
                    """.format(name))
                    cursor.executemany(sql_statement, data2save)
                    cursor.execute("COMMIT")
                except Exception as e:
                    logger.critical("{0} : error while trying to save records table in '{1}.db' : {2}".format(name.capitalize(), CONFIG_SECTION.lower(), e))
                    exit(1)

##########################################################################
# webServer view
@threadIt
def start_webserver(name, section):
    global CONFIG_SECTION
    global asyncLoop ; global asyncSleep ; global brokerList ; global data
    global config ; global logger
    global enabled 
    
    try :
        web_template_folder = osPathJoin(osPathDirname(__file__), "templates")
        web_static_folder = osPathJoin(osPathDirname(__file__), "static")

        app = Flask(name, template_folder=web_template_folder, static_folder=web_static_folder)
        app.config['SERVER_NAME'] = "{0}:{1}".format(config.parser[CONFIG_SECTION]["{0}_SERVER".format(CONFIG_SECTION)], config.parser[CONFIG_SECTION]["{0}_PORT".format(CONFIG_SECTION)])
        CORS(app, origins="http://127.0.0.1:5000", methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Access-Control-Allow-Origin'])
  
        # main http endpoint
        @app.route('/')
        def index():
            return render_template(MAIN_TEMPLATE)

        # return template to monitoring app
        @app.route('/get-template', methods=['GET', 'POST'])
        def get_template():
            return render_template(MAIN_TEMPLATE)
        
        # endpoint that send JSON data
        @app.route('/json_data', methods=['GET', 'POST'])
        def json_data():
            last_data = list(data[0:25])
            last_data.insert(0, ("broker", "ticker", "ask", "bid", "time", "date_creat", "user"))
            return jsonify({'data': last_data})

        @app.route('/json_brokers', methods=['GET', 'POST'])
        def json_brokers():
            if request.method == "GET":
                brokers = getSplitedParam(config.mem_config[name]["{0}_BROKER_LIST".format(section)])
                return jsonify({"brokers":brokers})
            elif request.method == 'POST':
                data = request.json
                #async_config_update()
                return jsonify("done") 
            
        @app.route('/json_tickers', methods=['GET', 'POST'])
        def json_tickers():
            tickers = getSplitedParam(config.mem_config[name]["{0}_WATCH_LIST".format(section)])
            return jsonify({"tickers":tickers})

        @app.route('/json_algo', methods=['GET', 'POST'])
        def json_algo():
            algo = getAlgo(tradeOrNot)
            return algo
        
        @app.route('/json_stop_arbitre', methods=['GET', 'POST'])
        def json_stop_arbitre():
            return stop_arbitre()
        
        
        @app.route('/json_start_arbitre', methods=['GET', 'POST'])
        def json_start_arbitre():
            return start_arbitre()

        app.run()
    except Exception as e:
        logger.critical("{0} : error while trying to start web interface : {1}".format(name.capitalize(), e))
        enabled = False
        exit(1)


#================================================================
if __name__ == "__main__":
    from sys import argv
    CONFIGFILE = "trading"

    name = "Arbitre"
    if len(argv) == 2: 
        name = argv[1]
    if len(argv) == 3: 
        name = argv[1]
        strategy = argv[2].split('.')[0].lower()

    name = name.lower()

    # check if iptables reconfig is needed
    check_ipt = host_has_ipt()

    # load strategy module for arbitre...
    strategy_file = "{0}.py".format(strategy)
    stratModule = module_from_file(strategy_file, osPathJoin(osGetcwd(), "trading", "Arbitre", "strategies", strategy_file))
    tradeOrNot = stratModule.ab_strategy

    # loading config and logger
    config, logger = init_logger(name=name, config=CONFIGFILE)

    mem_section = name.upper()
    if config.mem_config == None or not name in config.mem_config:
        config.update_mem_config(section_key_val_dict={name:{"{0}_BROKER_LIST".format(mem_section):'', 
                                                             "{0}_WATCH_LIST".format(mem_section):'',
                                                             "{0}_TIME_INTERVAL".format(mem_section):30}})

    db_file = osPathJoin(osPathDirname(__file__), "{0}.db".format(CONFIG_SECTION.lower()))    

    current_port = getUnusedPort()
    config.update(section=CONFIG_SECTION, configPath=config.COMMON_FILE_PATH, params={"{0}_DBFILE".format(CONFIG_SECTION):db_file, "{0}_PORT".format(CONFIG_SECTION):current_port})
    write_template(port=current_port, file_dest=osPathJoin(get_executed_script_dir(__file__), "templates", MAIN_TEMPLATE))

    # to see order placed 
    discLogger = DiscoLogger(user=name, room=CONFIG_SECTION, url=config.parser[CONFIG_SECTION]["{0}_LOG_CHAT".format(CONFIG_SECTION)], logger=logger)

    # init global variable shared with strategy
    sharedVar = {'config':config, 'logger':logger, 'discLogger':discLogger, 'name':name, 'config_section':CONFIG_SECTION, 'strategy':strategy}
    stratModule.ab_init(**sharedVar)

    start_webserver(name=name, section=mem_section)
    start_db_updater()
    asyncioRun(arbitre(name=name, section=mem_section))







    
 
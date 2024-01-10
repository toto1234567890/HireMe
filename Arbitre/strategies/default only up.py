#!/usr/bin/env python
# coding:utf-8

#************************************************************************************#
#                 Todo list for arbitre strategy creation                            #
#                                                                                    #
#    One strategy by files, main function always called 'ab_strategy'.               #
#    File name is the strategy name.                                                 #
#    ab_init function has to be implemented also even if it does nothing...          #
#    ab_config_refresh function has to be implemented in case of config change...    #
#************************************************************************************#

from datetime import datetime

# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import getSplitedParam, getOrDefault
from trading.trading_helpers import get_ccxt_exchanges_by_name

TESTNET = True


name = None ; config = None ; logger = None ; discLogger = None ; config_section = None
strategie = ''
open_positions = {}

def ab_add_broker(config, strategie, logger):
    global open_positions
    # broker trade list
    trade_broker_list = getSplitedParam(config.mem_config[name]["{0}_BROKER_TRADE".format(config_section)])
    for broker in trade_broker_list:
        if broker in open_positions:
            pass # broker already in enabled
        elif broker.upper() in config.parser.sections():
            try:
                exchange = (get_ccxt_exchanges_by_name[broker])({
                                                                    'apiKey': config.parser[broker.upper()]['API_KEY'], 
                                                                    'secret': config.parser[broker.upper()]['API_SECRET'], 
                                                                    'password': getOrDefault(config.parser[broker.upper()], None, key='PASSWORD'),
                                                                })
                exchange.userAgent = "MyAgent 1.414"
                open_positions[broker] = [False, exchange]
                # testnet
                if getOrDefault(config.parser[broker.upper()]['TESTNET'], True): 
                    exchange.set_sandbox_mode(True)  

            except Exception as e:
                logger.warning("{0} : {1}, strategy '{2}', error while trying to initialize broker '{3}' for trading : {4}, this broker will be ignored...".format(config_section, name, strategie, broker, e))
                continue 
        else:
            logger.warning("{0} : {1}, strategy '{2}', no credentials found for this broker : '{3}' this broker will be ignored for trading...".format(config_section, name, strategie, broker))
    return trade_broker_list
    

def ab_init(**kwargs):
    global name ; global config ; global logger ; global discLogger ; global config_section
    name = kwargs['name'] ; config = kwargs['config'] ; logger = kwargs['logger'] ; discLogger = kwargs['discLogger'] ; config_section = kwargs['config_section'] 
    strategie = kwargs['strategy']

    # add Tradable brokers if not already exist
    _ = ab_add_broker(config=config, strategie=strategie, logger=logger)


def ab_config_refresh(**kwargs):
    global name ; global config ; global logger ; global discLogger ; global config_section
    name = kwargs['name'] ; config = kwargs['config'] ; logger = kwargs['logger'] ; discLogger = kwargs['discLogger'] ; config_section = kwargs['config_section'] 
    strategie = kwargs['strategy']

    # add Tradable brokers if not already exist
    trade_broker_list = ab_add_broker(config=config, strategie=strategie, logger=logger)

    global open_positions ; broker_to_remove = []
    # remove broker if not open position
    for broker in open_positions:
        if not broker in trade_broker_list:
            if open_positions[broker][0]: 
                logger.warning("{0} : {1}, strategy '{2}' cannot remove broker '{3}' for now, one position is still open...".format(config_section, name, strategie, broker))
            else: 
                broker_to_remove.append(broker)
    open_positions = {key: value for key, value in open_positions.items() if not key in broker_to_remove}




def ab_strategy(record, strategy, last_asks, last_bids, ask_dir, bid_dir,
                min_ask, max_ask, min_bid, max_bid):
    global name ; global config ; global logger ; global discLogger ; global config_section
    global open_positions

    """ 
**********************************************************************************************
        Strategy name :             Default Only Up
        Simple 'default' strategy find the delayed cotation from one exchange 
        regarding the others, assumption : 
            if 1/3 of ask prices exchange moves the 2/3 remaining will move...
            ask order is placed with the better price
            one order by broker that can be placed simultenaously.
**********************************************************************************************
    """ 
    ret = ''
    amount = 0.01

    try:

        # unpack record
        exchange, symbol, ask, bid, quote_date, recv_date, user = record

        # check if position has to be closed or can be closed
        if exchange in open_positions and open_positions[exchange][0]:

            if (bid / open_positions[exchange][0]) >= 1.02:
                try:
                    ret = (open_positions[exchange][1]).create_market_sell_order(symbol, amount)
                    open_positions[exchange][0] = False
                    log_msg = "{0} : {1}, strategie '{2}' has placed 'SELL' order at '{3}' at '{4}' for '{5}-{6}' at '{7}' !".format(config_section.lower(), name, strategy, bid, datetime.utcnow(), amount, symbol, bid)
                    tradeMsg = {"log_msg": log_msg, 
                            "broker":min_broker_ask, "ticker":symbol, "order_type":'long',  "buy_or_sell":'sell', "state":'open', "price":ret['info']['fills'][0]['price'], "amount":amount, "order_date":datetime.utcnow(), "user":"{0}-{1}".format(user, strategy)}
                    logger.trade(tradeMsg)
                    discLogger.send_msg(log_msg)
                except Exception as e:
                    logger.error("{0} : {1}, strategy '{2}' error while trying to close position to broker {3} : {4}".format(config_section.lower(), name, strategy, exchange, ret))

            if (open_positions[exchange][0] / bid) <= 0.99:
                try:
                    ret = (open_positions[exchange][1]).create_market_sell_order(symbol, amount)
                    open_positions[exchange][0] = False
                    log_msg = "{0} : {1}, strategie '{2}' has placed 'SELL' order at '{3}' at '{4}' for '{5}-{6}' at '{7}' !".format(config_section.lower(), name, strategy, bid, datetime.utcnow(), amount, symbol, bid)
                    tradeMsg = {"log_msg": log_msg, 
                            "broker":min_broker_ask, "ticker":symbol, "order_type":'long',  "buy_or_sell":'sell', "state":'open', "price":ret['info']['fills'][0]['price'], "amount":amount, "order_date":datetime.utcnow(), "user":"{0}-{1}".format(user, strategy)}
                    logger.trade(tradeMsg)
                    discLogger.send_msg(log_msg)
                except Exception as e:
                    logger.error("{0} : {1}, strategy '{2}' error while trying to close position to broker {3} : {4}".format(config_section.lower(), name, strategy, exchange, ret))


        else:
            # starting by buy... 
            previous_ask = last_asks[exchange]
            # sens 1=up, -1 down
            sens_ask = 1 if ask > previous_ask else -1 if previous_ask == ask else 0
            ask_dir[exchange] = sens_ask
            last_asks[exchange] = ask
            # min_max -> ask
            sum_ask = sum(last_asks.values())
            average_ask = sum_ask/len(last_asks)
            min_broker_ask, min_ask_price = min(last_asks.items(), key=lambda item: item[1])

            # global market dir
            assumption = sum(item for item in ask_dir.values())/len(ask_dir)

            # if tradable cotation comes from one 'Tradable broker'
            if min_broker_ask in open_positions:
                if assumption >= 0.3 and average_ask-min_ask_price > 1:
                    # BUY MARKET order...
                    if not open_positions[min_broker_ask][0]:
                        try:
                            ret = (open_positions[min_broker_ask][1]).create_market_buy_order(symbol, amount)
                            open_positions[min_broker_ask][0] = min_ask_price
                            log_msg = "{0} : {1}, strategie '{2}' has placed 'BUY' order at '{3}' at '{4}' for '{5}-{6}' at '{7}' !".format(config_section.lower(), name, strategy, min_broker_ask, datetime.utcnow(), amount, symbol, min_ask_price)
                            tradeMsg = {"log_msg": log_msg, 
                                    "broker":min_broker_ask, "ticker":symbol, "order_type":'long',  "buy_or_sell":'buy', "state":'open', "price":min_ask_price, "amount":amount, "order_date":datetime.utcnow(), "user":"{0}-{1}".format(user, strategy)}
                            logger.trade(tradeMsg)
                            discLogger.send_msg(log_msg)
                        except Exception as e:
                            logger.error("{0} : {1}, strategy '{2}' error while trying to place order to broker {3} : {4}".format(config_section.lower(), name, strategy, min_broker_ask, ret))

    except Exception as e:

        try:
            if not exchange in last_asks:
                last_asks[exchange] = ask
                ask_dir[exchange] = 0
            else:
                logger.error("{0} : {1}, strategy '{2}' error while running main strategy : {3}".format(config_section.lower(), name, strategy, e))  
        except Exception as e:
            logger.error("{0} : {1}, strategy '{2}' unexpected error occurs while trying to recover ask datas : {3}".format(config_section.lower(), name, strategy, e))

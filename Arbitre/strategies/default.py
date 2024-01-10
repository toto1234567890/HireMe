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
from common.Helpers.helpers import getSplitedParam
from trading.trading_helpers import get_ccxt_exchanges_by_name



name = None ; config = None ; logger = None ; discLogger = None ; config_section = None
strategie = ''
open_positions = {}


def ab_init(**kwargs):
    global name ; global config ; global logger ; global discLogger ; global config_section
    name = kwargs['name'] ; config = kwargs['config'] ; logger = kwargs['logger'] ; discLogger = kwargs['discLogger'] ; config_section = kwargs['config_section'] 
    strategie = kwargs['strategy']
    global open_positions
    # add Tradable brokers
    trade_broker_list = getSplitedParam(config.mem_config[name]["{0}_BROKER_TRADE".format(config_section)])
    for broker in trade_broker_list:
        exchange = (get_ccxt_exchanges_by_name[broker])()
        exchange.userAgent = "MyAgent 1.414"
        open_positions[broker] = [False, exchange]

def ab_config_refresh(**kwargs):
    global name ; global config ; global logger ; global discLogger ; global config_section
    name = kwargs['name'] ; config = kwargs['config'] ; logger = kwargs['logger'] ; discLogger = kwargs['discLogger'] ; config_section = kwargs['config_section'] 
    strategie = kwargs['strategy']
    global open_positions
    # add Tradable brokers if not already exist
    trade_broker_list = getSplitedParam(config.mem_config[name]["{0}_BROKER_TRADE".format(config_section)])
    for broker in trade_broker_list:
        if not broker in open_positions:
            exchange = (get_ccxt_exchanges_by_name[broker])()
            exchange.userAgent = "MyAgent 1.414"
            open_positions[broker] = [False, exchange]
    # remove broker if not open position
    for broker in open_positions:
        if not broker in trade_broker_list:
            if broker[0]: 
                logger.warning("{0} : {1}, strategy '{2}' error while trying to recover ask datas : {3}".format(name, strategie))
            else: 
                open_positions.pop(broker)




def ab_strategy(record, strategy, last_asks, last_bids, ask_dir, bid_dir,
                min_ask, max_ask, min_bid, max_bid):
    global name ; global config ; global logger ; global discLogger ; global config_section
    global open_positions

    """ 
**********************************************************************************************
        Strategy name :             Default
        Simple 'default' strategy find the delayed cotation from one exchange 
        regarding the others, assumption : 
            if 1/3 of exchange prices moves the 2/3 remaining will move...
            order is placed regarding direction with the better price
**********************************************************************************************
    """ 
  
    try:

        # unpack record
        exchange, symbol, ask, bid, quote_date, recv_date, user = record

        # check if position has to be closed or can be closed
        if open_positions[exchange][0]:
            pass


        # starting by buy... 
        previous_ask = last_asks[exchange]
        # sens 1=up, -1 down
        sens_ask = 1 if ask > previous_ask else -1 if previous_ask == ask else 0
        ask_dir[exchange] = sens_ask ; last_asks[exchange] = ask
        # min_max -> ask
        sum_ask = sum(last_asks.values())
        broker_ask, min_ask_price = min(last_asks.items(), key=lambda item: item[1])

        nb = sum(item for item in ask_dir.values())
        average_ask = sum_ask/len(last_asks)
        # if tradable cotation comes from one 'Tradable broker'
        if broker_ask in open_positions:
            if nb/len(ask_dir) >= 0.3 and average_ask-min_ask_price > 5:
                # BUY MARKET order...
                if not open_positions[broker_ask][0]:
                    amount = 1
                    #ret = min_ask_exchange.create_market_ask_order(symbol, amount)
                    open_positions[broker_ask][0] = min_ask_price
                    tradeMsg = {"log_msg":"{0} : strategie '{1}' has placed 'BUY' order at '{2}' at '{3}' for '{4}-{5}' !".format(name, strategy, broker_ask, datetime.utcnow(), amount, symbol), 
                                "broker":broker_ask, "ticker":symbol, "order_type":'long',  "buy_or_sell":'buy', "state":'open', "price":min_ask_price, "amount":amount, "order_date":datetime.utcnow(), "user":"{0}-{1}".format(user, strategy)}
                    logger.trade(tradeMsg)
                    discLogger.send_msg(tradeMsg['log_msg'])


        # trying sell  
        previous_bid = last_bids[exchange]
        # sens 1=up, -1 down
        sens_bid = 1 if bid > previous_bid else -1 if previous_bid == bid else 0
        bid_dir[exchange] = sens_bid ; last_bids[exchange] = bid
        # max_bid -> bid
        sum_bid = sum(last_bids.values())
        broker_bid, max_bid_price = max(last_bids.items(), key=lambda item: item[1])

        nb = sum(item for item in bid_dir.values())
        average_bid = sum_bid/len(last_bids)
        # if tradable cotation comes from one 'Tradable broker'
        if broker_bid in open_positions:
            if nb/len(bid_dir) <= -0.3 and max_bid_price-average_bid > 5:
                # SELL MARKET order...
                amount = 1
                #ret = max_bid_exchange.create_market_sell_order(symbol, amount)
                open_positions[broker_bid][0] = max_bid_price # ret_price
                tradeMsg = {"log_msg":"{0} : strategie '{1}' has placed 'SELL' order at '{2}' at '{3}' for '{4}-{5}' !".format(name, strategy, broker_bid, datetime.utcnow(), amount, symbol), 
                            "broker":broker_bid, "ticker":symbol, "order_type":'long',  "buy_or_sell":'sell', "state":'open', "price":max_bid_price, "amount":amount, "order_date":datetime.utcnow(), "user":"{0}-{1}".format(user, strategy)}
                logger.trade(tradeMsg)
                discLogger.send_msg(tradeMsg['log_msg'])

    except:

        try:
            last_asks[exchange] = ask
            if len(last_asks) == 1:
                min_ask = [ask, exchange]
                ask_dir[exchange] = 0
            else:
                previous_ask = last_asks[exchange]
                # sens
                sens_ask = 1 if ask > previous_ask else -1 if previous_ask == ask else 0
                ask_dir[exchange] = sens_ask ; last_asks[exchange] = ask
                # min_max -> ask
                min_ask = min(last_asks.items(), key=lambda item: item[1])
        except Exception as e:
            logger.error("{0} : {1}, strategy '{2}' error while trying to recover ask datas : {3}".format(config_section, name, strategy, e))

        try:
            last_bids[exchange] = bid
            if len(last_bids) == 1:
                max_bid = [bid, exchange]
                bid_dir[exchange] = 0
            else:
                previous_bid = last_bids[exchange]
                # sens
                sens_bid = 1 if previous_bid < bid else -1 if previous_bid == bid else 0
                bid_dir[exchange] = sens_bid ; last_bids[exchange] = bid
                # min_max -> ask
                max_bid = max(last_bids.items(), key=lambda item: item[1])
        except Exception as e:
            logger.error("{0} : {1}, strategy '{2}' error while trying to recover bid datas : {3}".format(config_section, name, strategy, e))
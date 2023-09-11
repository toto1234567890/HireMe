#!/usr/bin/env python
# coding:utf-8
#FIXME add url for password ??

from os.path import join as osPathJoin
from uuid import uuid4
from telebot import types

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.Helpers.helpers import TreeNode
from common.Helpers.os_helpers import get_executed_script_dir
from common.TeleRemote.tele_funcs import BaseMixin

# *️⃣🍾🎖🚀📲🕹⌚️⏰⚙️🔫💣🚬⚰️🔭🔬🗝📩📨📪📫📬📭📈📊📉🗄🗂🔐⛔️🌐✅🔀🔝®️🔚🔙💲💱📶🎲🌹🎯↪️ ⛔️ 📛 ⏏️ 🔀 ℹ️ #️⃣ *️⃣
# 🏎🎢🏦🏛⛪️🎇🛤🛰🚔🚨🏍🛴🦯🎮🚴🪃⚽️🍼❄️🐿🐢🦊💼🧳☂️🍀🏡🕌💾🎥📹🔦💶💴💵💷💰⏳🔋💉🧬🦠📰❌✅
# 🕹☎️🔮🧻📦⁉️♻️🔱⚙️🚦🪙🚧📱📨⚖️✏️

class Qmsg:
    def __init__(self, msg, frome, too, ackw=None, priority=False):
        self.id = uuid4()
        self.msg = msg
        self.frome = frome
        self.too = too
        self.ackw = ackw
        self.priority = priority


class BACK_CONFIG:
    name = 'config menu'
    caption = '🔙 config'
    bot_confirmation = '🔙'
    back_parent_menu = None
    def __init__(self):
        pass
    def __call__(self, telecommande, bot):
        if not self.back_parent_menu is None:
            self.back_parent_menu(telecommande, bot)
        else:
            from common.TeleRemote.tele_funcs import BACK, MAIN_MENU
            bot.send_message(telecommande.config.TB_CHATID, BACK.caption, MAIN_MENU(telecommande, bot, FirstCall=False))
_BACK_CONFIG = BACK_CONFIG()

##############################################################################################################################################################################################
# button

class config_button(BaseMixin):
    name = None
    caption = None
    tele_message = None
    bot_confirmation = '🧮'
    starQs_message = None
    saved = '✅'
    config = None
    def __init__(self, section=None, key_val=None, config=None):
        TreeNode.__init__(self, node_name=section)
        self.config = config
        self.caption = section
        if not key_val is None:
            self.markup = types.ReplyKeyboardMarkup()
            back = types.InlineKeyboardButton(_BACK_CONFIG.caption)
            self.markup.row(back)
            for val in key_val:
                self.add_sub_menu(obj=config_button(section="{0}\n{1} : {2}".format(self.caption, val["key"], val["value"]), config=config))
        else:
            # refresh config
            self.markup = types.ReplyKeyboardMarkup()
            back = types.InlineKeyboardButton(_BACK_CONFIG.caption)
            self.markup.row(back)
    def __call__(self, telecommande, bot):
        _BACK_CONFIG.back_parent_menu = self.parent
        bot.send_message(telecommande.config.TB_CHATID, self.bot_confirmation, reply_markup=self.markup)
    def edit(self, telecommande, bot, replyMessage):
        newVal_oldCaption = replyMessage.split("√2")[0].strip()
        section = newVal_oldCaption.split('\n')[0].replace(self.bot_confirmation, '').strip()
        key = newVal_oldCaption.split('\n')[1].split(':')[0].strip()
        newVal = replyMessage.split("√2")[1].strip()
        self.config.update_mem_config(section_key_val_dict={section:{key:newVal}})
        bot.send_message(telecommande.config.TB_CHATID, "{0} {1}\n{2}:{3}  {4}".format(self.bot_confirmation, section, key, newVal, self.saved), reply_markup=self.markup)

##############################################################################################################################################################################################
# button

class CURRENTCONFIG(BaseMixin):
    name = 'currentconfig'
    caption = '🧮 currentconfig'
    tele_message = 'currentconfig'
    bot_confirmation = '🧮'
    starQs_message = 'currentconfig'
    markup = types.ReplyKeyboardMarkup()
    config = None
    def __init__(self, all_message_handlers):
        TreeNode.__init__(self, node_name=self.caption)
        all_message_handlers[_BACK_CONFIG.caption]=_BACK_CONFIG
    def __call__(self, telecommande, bot):
        _BACK_CONFIG.back_parent_menu = None
        return self.get_config_buttons()
    def get_config_buttons(self):
        try:
            config_key_val = self.config.get_mem_config()
        except:
            self.config = Config(name="ConfigButton")
            config_key_val = self.config.get_mem_config()
        return [config_button(section="{0} {1}".format(self.bot_confirmation, section), key_val=key_val, config=self.config) for section, key_val in config_key_val.items() if key_val and len(key_val)>0]


#class CRYPTO_ARBITRE:
#    name = 'crypto arbitre'
#    caption = '⚖️ crypto arbitre'
#    tele_message = None
#    bot_confirmation = '⚖️'
#    starQs_message = None
#    markup = None
#    def __init__(self):
#        pass
#    def __call__(self, telecommande, bot):
#        telecommande.send_msg_in(self.starQs_message)
#        bot.send_message(telecommande.config.TB_CHATID, self.bot_confirmation)
#    def starQs_response(name):
#        return "⚖️ {0} is listening to the market !".format(name)

##############################################################################################################################################################################################
# Sub Menu

#class AVAILABLE_BROKERS:
#    name = 'available brokers'
#    caption = '🏛 available brokers'
#    tele_message = None
#    bot_confirmation = '🏛'
#    starQs_message = None
#    markup = types.ReplyKeyboardMarkup()
#    def __init__(self, brokersList):
#        back = types.InlineKeyboardButton('📊 menu...')
#        self.markup.row(back)
#        self.brokers_info = brokersList
#        for broker in brokersList.BrokerList:
#            broker_button = types.InlineKeyboardButton('{0} start ?'.format(broker))
#            self.markup.row(broker_button)
#    def __call__(self, telecommande, bot):
#        bot.send_message(telecommande.config.TB_CHATID, self.bot_confirmation, reply_markup=self.markup)
#    def starQs_response(name):
#        return ("🏛 {0} has been started !".format(name)).encode()

#class WATCH_LIST:
#    name = 'watch list'
#    caption = '💶 💴 💵 💷 watch list'
#    tele_message = None
#    bot_confirmation = '💶 💴 💵 💷'
#    starQs_message = None
#    markup = types.ReplyKeyboardMarkup()
#    def __init__(self):
#        back = types.InlineKeyboardButton('📊 menu...')
#        self.markup.row(back)
#        Nonee = types.InlineKeyboardButton(UNDER_CONSTRUCTION.caption)
#        self.markup.row(Nonee)
#    def __call__(self, telecommande, bot):
#        bot.send_message(telecommande.config.TB_CHATID, self.bot_confirmation, reply_markup=self.markup)


#class ARBITRE:
#    name = 'available brokers'
#    caption = '🏛 available brokers'
#    tele_message = None
#    bot_confirmation = '🏛'
#    starQs_message = None
#    markup = types.ReplyKeyboardMarkup()
#    def __init__(self, brokersList):
#        back = types.InlineKeyboardButton('📊 menu...')
#        self.markup.row(back)
#        self.brokers_info = brokersList
#        for broker in brokersList.BrokerList:
#            broker_button = types.InlineKeyboardButton('{0} start ?'.format(broker))
#            self.markup.row(broker_button)
#    def __call__(self, telecommande, bot):
#        bot.send_message(telecommande.config.TB_CHATID, self.bot_confirmation, reply_markup=self.markup)
#    def starQs_response(name):
#        return ("🏛 {0} has been started !".format(name)).encode()

##############################################################################################################################################################################################
# Menu




#class MENU:
#    name = 'menu'
#    caption = '📊 menu...'
#    tele_message = None
#    bot_confirmation = '📊'
#    starQs_message = None
#    markup = types.ReplyKeyboardMarkup()
#    def __init__(self):    
#        back = types.InlineKeyboardButton(BACK.caption) 
#        self.markup.row(back)
#        menu_available_broker = types.InlineKeyboardButton(AVAILABLE_BROKERS.caption)
#        menu_watch_list = types.InlineKeyboardButton(WATCH_LIST.caption)
#        menu_startegy_list = types.InlineKeyboardButton(RUNNABLE_STARTEGIES.caption)
#        self.markup.row(menu_available_broker)
#        self.markup.row(menu_watch_list)
#        self.markup.row(menu_startegy_list)
#    def __call__(self, telecommande, bot):
#        bot.send_message(telecommande.config.TB_CHATID, self.bot_confirmation, reply_markup=self.markup)


#class ARBITRAGE:
#    name = 'arbitrage'
#    caption = '📈📉 arbitrage'
#    tele_message = 'arbitrage'
#    bot_confirmation = '📈📉'
#    starQs_message = 'arbitrage'
#    markup = types.ReplyKeyboardMarkup()
#    def __init__(self, arbitreList):
#        back = types.InlineKeyboardButton(BACK.caption)
#        self.markup.row(back)
#        self.arbitre_info = arbitreList
#        for arbitre in arbitreList.ArbitreList:
#            arbitre_button = types.InlineKeyboardButton('{0} start ?'.format(arbitre))
#            self.markup.row(arbitre_button)
#    def __call__(self, telecommande, bot):
#        bot.send_message(telecommande.config.TB_CHATID, self.bot_confirmation, reply_markup=self.markup)







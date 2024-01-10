#!/usr/bin/env python
# coding:utf-8
# FIXME start in process mode

from socket import gethostname
WHOIAMI = "+++++++++++++ " + str(gethostname()) + " +++++++++++++\n"

import apprise
from time import sleep
from collections import deque
from os.path import join as osPathJoin, dirname as osPathDirname, exists as osPathExists
from threading import Thread
from queue import Queue as ProcessQ
from multiprocessing import Process
from requests import post as requestesPost

# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import getOrDefault, threadIt


class DEFAULT_BEAT:
    MAIN_QUEUE_BEAT = 0.1

        
class Notifie:#(Process):

    APPRISE_CONFIG_PATH = osPathJoin(osPathDirname(__file__), "notifie.yml")

    # 2 constructors not possible in python.... (same for process or for threads)
    def __init__(self, enabled=True, apprise_config:str=None, main_config=None, child=None, *args, **kwargs):          
        if enabled and osPathExists(self.APPRISE_CONFIG_PATH):
            self.config = getOrDefault(main_config, DEFAULT_BEAT)
            self.MAIN_QUEUE_BEAT = self.config.MAIN_QUEUE_BEAT

            self.apobj = apprise.Apprise()
            config = apprise.AppriseConfig()
            apprise_config = getOrDefault(apprise_config, self.APPRISE_CONFIG_PATH)
            config.add(apprise_config)
            self.apobj.add(config)

            # Queue.queue mode 
            #self.queue = ProcessQ()

            # deque mode 
            self.queue = deque()
            self.enabled = True
            self.start_worker()
        else:
            self.enabled = False

    #    # Process Mode
    #    if not child is None:
    #        self.child = child
    #        super(Process, self).__init__(*args, **kwargs)
    #        self.start()
    #
    #def run(self):
    #    if self.enabled:
    #        while True:
    #            message = (self.child.recv()).decode()
    #            attachments = message.attachments ; tag = message.tag ; message = message.msg
    #            self.queue.put((message, attachments, tag))

    # Thread Mode
    def start_worker(self):
        Thread(target=self.process_queue, daemon=True).start()

    def process_queue(self):
        while True:
            # Queue.queue mode 
            #message, attachments, tag = self.queue.get()

            # deque mode
            if len(self.queue) > 0:
                # deque mode
                message, attachments, tag = self.queue.popleft()

                if attachments:
                    execution = self.apobj.notify(body=message, attach=attachments, tag=tag)
                else:
                    execution = self.apobj.notify(body=message, tag=tag)
            sleep(self.MAIN_QUEUE_BEAT)
            #while not execution:
                #sleep(self.MAIN_QUEUE_BEAT)
            #print(execution)
            
            # Queue.queue mode 
            #self.queue.task_done()

    def send_notification(self, message, attachments=None, tag="all"):
        if self.enabled:
            # deque mode
            message = WHOIAMI + message
            self.queue.append((message, attachments, tag))

            # Queue.queue mode 
            #self.queue.put((message, attachments, tag))
 

class LightNotifie:
    DEFAULT_YAML_PATH = Notifie.APPRISE_CONFIG_PATH
    def __init__(self, config=None):
        """
            While passing config or any other parameters, the message will be forwarded too the matching tele_remote, 
            else message as usual to the WatchDog bot...
        """
        if config == None:
            self.bot_token, self.tb_chat_id = LightNotifie.load_yaml_conf()
        else:
            self.tb_chat_id = config.TB_CHATID
            self.bot_token = config.TB_TOKEN
        self.url = "https://api.telegram.org/bot{0}/sendMessage".format(self.bot_token)

    @threadIt
    def send_message(self, message):
        message = WHOIAMI + message 
        requestesPost(self.url, params={'chat_id': self.tb_chat_id, 'text': message})

    @staticmethod
    def load_yaml_conf():
        from yaml import safe_load
        with open(LightNotifie.DEFAULT_YAML_PATH, 'r') as file:
            yml_config = safe_load(file)
        tgram_conf = [key.replace("tgram://", '').split('/') for config in yml_config["urls"] for key in config if key.startswith("tgram://")][0]
        return tgram_conf[0], tgram_conf[1]

    @staticmethod
    @threadIt
    def notifie(message, bot_token=None, chat_id=None):
        message = WHOIAMI + message
        default_bot_token, default_chat_id = LightNotifie.load_yaml_conf()
        url = "https://api.telegram.org/bot{0}/sendMessage".format(bot_token or default_bot_token)
        requestesPost(url, params={'chat_id': chat_id or default_chat_id, 'text': message})


#================================================================
if __name__ == "__main__":
    notif = Notifie()
    notif.send_notification("Telebot and Desktop without Notif server", tag=["telebot", "desktop"])
    notif.send_notification("Telebt and Desktp without Notif server", tag=["telebot", "desktop"])
    notif.send_notification("Telebot and Dsktop without Ntif server", tag=["telebot", "desktop"])
    notif.send_notification("Telebot an Destop without Notif server", tag=["telebot", "desktop"])
    notif.send_notification("Telebo and Desktop without Notif server", tag=["telebot", "desktop"])
    sleep(10)
    
    from common.config import Config
    config = Config(name="LightNotifie", ignore_config_server=True)
    with_config = LightNotifie(config=config) ; with_config.send_message("test -> LightNotifie.send_message (with_config)")
    without_config = LightNotifie() ; without_config.send_message("test -> LightNotifie.send_message (without_config)")
    LightNotifie.notifie(bot_token='6533432523:AAGxkahs4SViTww53Ihln523-ObaD_MuFdI', chat_id='1995178465', message="test -> LightNotifie.notifie")
    LightNotifie.notifie(message="test -> LightNotifie.notifie without params")
    
    # import time
    # sleep(30)
    # notif.send_notification("Desktop only", tag="desktop")
    # sleep(1)
    # notif.send_notification("Telebot only", tag="telebot")
    # sleep(1)
    # notif.send_notification("Notification sent to phone, SMS...", tag="sms")
    # sleep(1)

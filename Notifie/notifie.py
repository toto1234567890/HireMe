#!/usr/bin/env python
# coding:utf-8
# FIXME start in process mode

import apprise
from time import sleep
from collections import deque
from os import path as ospath
from threading import Thread
from queue import Queue as ProcessQ
from multiprocessing import Process

# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import getOrDefault


class DEFAULT_BEAT:
    MAIN_QUEUE_BEAT = 0.1

        
class Notifie:#(Process):

    APPRISE_CONFIG_PATH = ospath.join(ospath.dirname(__file__), "notifie.yml")

    # 2 constructors not possible in python.... (same for process or for threads)
    def __init__(self, enabled=True, apprise_config:str=None, main_config=None, child=None, *args, **kwargs):          
        if enabled and ospath.exists(self.APPRISE_CONFIG_PATH):
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
            self.queue.append((message, attachments, tag))

            # Queue.queue mode 
            #self.queue.put((message, attachments, tag))    

#================================================================
if __name__ == "__main__":
    notif = Notifie()
    notif.send_notification("Telebot and Desktop without Notif server", tag=["telebot", "desktop"])
    notif.send_notification("Telebt and Desktp without Notif server", tag=["telebot", "desktop"])
    notif.send_notification("Telebot and Dsktop without Ntif server", tag=["telebot", "desktop"])
    notif.send_notification("Telebot an Destop without Notif server", tag=["telebot", "desktop"])
    notif.send_notification("Telebo and Desktop without Notif server", tag=["telebot", "desktop"])
    sleep(10)
    
    # import time
    # sleep(30)
    # notif.send_notification("Desktop only", tag="desktop")
    # sleep(1)
    # notif.send_notification("Telebot only", tag="telebot")
    # sleep(1)
    # notif.send_notification("Notification sent to phone, SMS...", tag="sms")
    # sleep(1)

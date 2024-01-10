#!/usr/bin/env python
# coding:utf-8


from discord_webhook import DiscordWebhook, AsyncDiscordWebhook


class DiscoLogger:
    Name="DiscoLogger" 
    def __init__(self, user, room, url, logger):
        self.user = user
        self.room = room
        self.url = url
        self.logger = logger
    def send_msg(self, msg):
        try:
            webhook = DiscordWebhook(url=self.url, content=msg)
            webhook.execute()
        except Exception as e:
            self.logger.error("{0} : user '{1}', room '{2}', error while trying to send message '{3}' : {4}".format(self.Name, self.user, self.room, msg, e))
    async def async_send_msg(self, msg):
        try:
            webhook = AsyncDiscordWebhook(url=self.url, content=msg) 
            await webhook.execute()
        except Exception as e:
            self.logger.error("{0} : user '{1}', room '{2}', error while trying to send async message '{3}' : {4}".format(self.Name, self.user, self.room, msg, e))




class DiscordClient:
    Name="DiscordClient"
    def __init__(self, user, config, logger, name=None, rooms:dict=None):
        if not name is None:
            self.Name = name
        self.user = user
        self.config = config
        self.logger = logger
        self.NameSpace = {}
        if not rooms is None:    
            for room, url in rooms.items():
                self.join_room(room=room, url=url)

    def join_room(self, room:str, url:str):
        discord = DiscoLogger(user=self.Name, room=room, url=url, logger=self.logger)
        self.NameSpace[room] = discord

    def leave_room(self, room:str):
        self.NameSpace.pop(room, None)

    def send_msg(self, msg, room):
        msg = "#:-{0}-:#->   {1}".format(self.user, msg)
        discord = self.NameSpace[room]
        discord.send_msg(msg)

    def async_send_msg(self, msg, room):
        msg = "#:-{0}-:#->   {1}".format(self.user, msg)
        discord = self.NameSpace[room]
        discord.async_send_msg(msg)




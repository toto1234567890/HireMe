#!/usr/bin/env python
# coding:utf-8

from os import getcwd as osGetcwd, mkdir as osMkdir
from os.path import join as ospathJoin
from genericpath import exists

# relative import
from sys import path;path.extend("..")
from common.Helpers.helpers import getOrDefault, threadIt

LOST_QMSG_DIR = ospathJoin(osGetcwd(), "logs", "lost")

@threadIt
def LostQmsg(Qmsg):
    global LOST_QMSG_DIR
    if not exists(LOST_QMSG_DIR):
        osMkdir(LOST_QMSG_DIR)
    with open(ospathJoin(LOST_QMSG_DIR, "{0}.Qmsg".format(Qmsg.id)), 'w') as file:
        file.write(str(Qmsg.__dict__))


def starQ_route_msg(self, cur_msg, QueuesOut):#, logger:MyLogger):
    try :
        QueuesOut[cur_msg.too].append(cur_msg)
        self.logger.debug("{0} : routing_rules, sent message id '{1}' from '{2}' to '{3}'".format(self.Name, cur_msg.id, cur_msg.frome, cur_msg.too))
    except Exception as e:
        self.logger.critical("{0} : routing_rules, error while trying to route message id '{0}' in Threads Queues '{1}' : {2}".format(self.Name, getOrDefault(cur_msg.id, "#None"), cur_msg.too, e))
        if not (cur_msg.too in QueuesOut):
            self.logger.critical("{0} : routing_rules, threads Queue '{1}' doesn't exist in subscribers StarQs...".format(self.Name, cur_msg.too))

        self.logger.critical("{0} : routing_rules, message id '{0}' has been lost !!!".format(self.Name, getOrDefault(cur_msg.id, "#None")))
        LostQmsg(cur_msg)




#================================================================
if __name__ == "__main__":
    pass
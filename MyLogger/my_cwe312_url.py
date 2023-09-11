#!/usr/bin/env python
# coding:utf-8

from apprise.utils import cwe312_url

def load_sensitive_data(config):
    conf_data = []
    for key, val in config.__dict__.items():
        if "PASSWORD" in key or "USERNAME" in key or "KEY" in key or "SENDERCOMPID" in key:
            conf_data.append(val)
    return conf_data

def my_cwe312_url(msg, sensitive_data):
    msg = cwe312_url(msg)
    # FIX message
    for x in sensitive_data:
        msg = msg.replace(x, '*'*len(x))
    return msg
#!/usr/bin/env python
# coding:utf-8


###################################################################
######################## wake on lan local  #######################
from re import compile as reCompile, IGNORECASE as reIGNORECASE
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST
NON_HEX_CHARS = reCompile(r"[^a-f0-9]", reIGNORECASE)
MAC_PATTERN = reCompile(r"^[a-f0-9]{12}$", reIGNORECASE)
def wake_on_lan(mac_address, IP=None, logger=None):
    """ https://code.activestate.com/recipes/358449-wake-on-lan/
    Switches on remote computers using WOL. """
    
    def _clean_mac_address(mac_address):
        """Removes all non-hexadecimal characters from `mac_address_supplied`"""
        mac_address_cleaned = NON_HEX_CHARS.sub("", mac_address)
        if MAC_PATTERN.fullmatch(mac_address_cleaned):
            return mac_address_cleaned
        else:
            if not logger is None:
                logger.error("Wake on Lan : error while trying to format mac address, 'Incorrect MAC address format'")
                return
            else:
                raise ValueError('Incorrect MAC address format')
    
    mac_address = _clean_mac_address(mac_address)

    # Pad the synchronization stream.
    data = bytes.fromhex("FF" * 6 + mac_address * 16)

    if not IP is None:
        try:
            # send only to IP
            # return
            pass
        except:
            # do braodcast...
            pass  
    # Broadcast it to the LAN.
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    sock.sendto(data, ('<broadcast>', 9))
    return True
######################## wake on lan local  ####################### 
################################################################### 


#================================================================
if __name__ == "__main__":
    # Use mac_addresses with any seperators.
    wake_on_lan('0F:0F:DF:0F:BF:EF')
    wake_on_lan('0F-0F-DF-0F-BF-EF')
    # or without any seperators.
    wake_on_lan('0F0FDF0FBFEF')
import socket
import time
from zeroconf import ServiceBrowser, Zeroconf
import settings
import logging

class MyListener:

    infos = []

    def remove_service(self, zeroconf, type, name):
        pass

    def add_service(self, zeroconf, type, name):
        self.infos.append(zeroconf.get_service_info(type, name))


def hue_ip():

    # use the settings first

    settings_json = settings.get_settings()
    address = settings_json["hue_ip"]

    if address:
        print("found address in settings: %s" % address)
        if address == "disabled":
            return None

        return address

    # then try zeroconf

    bridge_id = settings_json.get("hue_bridge_id")

    print("settings bridge id", bridge_id)

    try:
        zeroconf = Zeroconf()
        listener = MyListener()
        ServiceBrowser(zeroconf, "_hue._tcp.local.", listener)
        time.sleep(1.0)
        zeroconf.close()

        for info in listener.infos:
            address = socket.inet_ntoa(info.address)
            # if there is no bridge id given it will return the first one found
            if bridge_id is None:
                print("found address with zeroconf: %s" % address)
                return address
            # otherwise it will return only the matching one
            else:
                discovered_bridgeid = info.properties[b'bridgeid'].decode("utf-8")
                print("discovered_bridge id", discovered_bridgeid)
                if discovered_bridgeid.endswith(bridge_id.lower()):
                    print("found address with zeroconf: %s" % address)
                    return address

        # otherwise return an empty string as this is the previous default behaviour
        return ""

    except Exception as e:
        logging.error("Zeroconf has failed!")
        logging.error(e)
        return ""







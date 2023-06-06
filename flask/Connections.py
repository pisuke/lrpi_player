from apscheduler.schedulers.background import BackgroundScheduler
from tinkerforge.ip_connection import IPConnection  # pylint: disable=import-error
from time import sleep
import os
import logging
logging.basicConfig(level=logging.INFO)

# brickd
HOST = os.environ.get("BRICKD_HOST", "127.0.0.1")
PORT = 4223


class Connections():
    """
        {apscheduler BackgroundScheduler} and {Tinkerforge IPConnection} 
        instances.

        We were seeing very troubling behaviour concerning
        multiple BackgroundScheduler instances and many, MANY
        tinkerforge.ip_connection(s). In the latter case, this 
        would eventually end in too many connections and therefore
        Linux file handles - this crashed the entire system

        This wrapper class, instantiated just once on Server.py boot,
        helps to keep things tidy, fine and dandy
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler({
            'apscheduler.executors.processpool': {
                'type': 'processpool',
                'max_workers': '1'
            }}, timezone="Europe/London")

        try:
            self.tfIpCon = IPConnection()
            self.tfIpCon.connect(HOST, PORT)
            self.tfIDs = []
            self.tfIpCon.register_callback(
                IPConnection.CALLBACK_ENUMERATE, self.cb_enumerate)

            # Trigger Enumerate
            self.tfIpCon.enumerate()

            # Likely wait for the tinkerforge brickd to finish doing its thing
            sleep(0.7)
        except Exception as e:
            logging.warning(
                "Could not create IPConnection to Tinkerforge, assigning stub to self.tfIpCon")
            self.tfIpCon = None
            self.tfIDs = []

        print("tfIds before main loop: ", self.tfIDs)
        print("Starting scheduler...")
        self.scheduler.start(paused=False)

    def cb_enumerate(self, uid, connected_uid, position, hardware_version, firmware_version,
                     device_identifier, enumeration_type):
        self.tfIDs.append([uid, device_identifier])

    def reset_scheduler(self):
        logging.info("************** RESETTING SCHEDULER **************")
        for job in self.scheduler.get_jobs():
            print("Removing job: ", job)
            job.remove()
        self.scheduler.resume()

    def __del__(self):
        try:
            logging.info(
                "************** SHUTTING DOWN CONNECTIONS **************")
            logging.info("Shutting down scheduler...")
            self.scheduler.shutdown()
            logging.info("Disconnecting from Tinkerforge master brick...")
            self.tfIpCon.disconnect()
            sleep(1)
        except Exception as e:
            print("COULD NOT KILL CONNECTIONS PROPERLY")
            print("Why: ", e)

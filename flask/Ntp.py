import time
import os

NTP_SERVER = 'pool.ntp.org'


def set_os_time_with_ntp():
    try:
        import ntplib
        client = ntplib.NTPClient()
        response = client.request(NTP_SERVER)
        print("Attempting to set os time with ntp server : " + NTP_SERVER)
        tx_time = time.strftime('%m%d%H%M%Y.%S',
                                time.localtime(response.tx_time))
        print("Setting to : ", tx_time)
        os.system('date ' + tx_time)
    except Exception as e:
        print('Could not sync with time server, why: ')
        print(e)

    print('Done.')

from os import system, uname


def findArm():
    return uname().machine == 'armv7l'


def killOmx():
    # This will only work on Unix-like (just Linux?) systems...
    try:
        system("killall omxplayer.bin")
        print('omxplayer processes killed!')
    except:
        print('How are you NOT running omxplayer on Linux?')
        exit(0)

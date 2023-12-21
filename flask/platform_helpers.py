from os import system, uname


# def findArm():
#     return uname().machine == 'armv7l'

def findArm():
    is_arm = uname().machine == 'armv7l' or uname().machine == 'aarch64'
    print("is arm = ",is_arm)
    return is_arm

def killOmx():
    # This will only work on Unix-like (just Linux?) systems...
    try:
        system("killall omxplayer.bin")
        print('omxplayer processes killed!')
    except:
        print('How are you NOT running omxplayer on Linux?')
        exit(0)

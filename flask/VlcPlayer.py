from os import uname, system
from time import sleep
import vlc

class VlcPlayer():
    def __init__(self):
        self.ready = False
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()

    def start(self, pathToTrack):
        self.media = self.vlc_instance.media_new('file://' + pathToTrack)
        self.player.set_media(self.media)
        self.player.play()
        self.player.pause()
        sleep(1.5)
        self.player.audio_set_volume(50)
        self.player.play()
        print("Playing on vlc...", self.player.get_length() / 1000)
        return self.player.get_length() / 1000     

    def playPause(self):
        print("Playpausing...", self.player.get_length() / 1000)
        self.player.pause()
        return self.player.get_length() / 1000

    def getPosition(self):
        print("0:00")

    def pause(self):
        self.player.pause()

    def stop(self):
        print("Stopping...")

    def crossfade(self, nextTrack):
        print("Crossfading...") 

    def next(self):
        print("Skipping forward...")

    def previous(self):
        print("Skipping back...")

    def mute(self):
        print(self.player.audio_get_volume())
        self.player.audio_set_volume(0)

    def volumeUp(self):
        self.player.audio_set_volume(self.player.audio_get_volume() + 10)

    def volumeDown(self, interval):
        print("vlc downer: ", self.player.audio_get_volume())
        if (self.player.audio_get_volume() <= 10 or interval == 0):
            return False
        else:
            self.player.audio_set_volume(self.player.audio_get_volume() - 100/interval)
            return True  

    def exit(self):
        if self.player:
            self.player.stop()
        else:
            return 1

    def __del__(self):
        print("VLC died")
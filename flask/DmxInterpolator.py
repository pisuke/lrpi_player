from pysrt import SubRipFile, SubRipItem, SubRipTime # pylint: disable=import-error
from numpy import array, ones, zeros # pylint: disable=import-error

class DmxInterpolator():
    def __init__(self):
        self.start_frame = None
        self.target_frame = None
        self.start_time = None
        self.target_time = None
        self.duration = None
        self.running = False
        self.twiddle = 0.5

    def srt_to_seconds(self, t):
        block, milliseconds = str(t).split(",")
        hours, minutes, seconds = block.split(":")
        u_ts = (int(seconds) + int(minutes)*60 + int(hours)*60*60 + int(milliseconds)/1000.0)
        # print("converted to seconds: ", u_ts)
        return u_ts

    def srt_to_array(self, f):
        # print("converting frame: ", f)
        scope,items = f[0:len(f)-1].split("(")
        return array(items.split(",")).astype(int)   

    def start(
        self,
        start_frame,
        start_time,
        target_frame,
        target_time
    ):

        self.start_frame = self.srt_to_array(start_frame)
        self.target_frame = self.srt_to_array(target_frame)
        self.start_time = self.srt_to_seconds(start_time)
        self.target_time = self.srt_to_seconds(target_time)
        self.duration = target_time - start_time
        self.running = True
        print("Interpolator starting with duration: ", self.duration)
        print("Starts at: ", self.start_time)
        print("Ends at: ", self.target_time)
        print("Running ", self.running)

    def isRunning(self):
        return self.running

    def clear(self):
        self.__init__()

    def findNextEvent(
        self,
        thisI,
        subtitle
    ):
        # Look for the next DMX event
        # If there isn't one, don't start the interpolator

        nextI = thisI + 1
        lenSubs = len(subtitle)

        while nextI < lenSubs and not self.running:
            if subtitle[nextI].text.find("DMX", 0, 5) > -1:
                print("Interpolation event found!")
                print('From frame: ', subtitle[thisI].text)
                print('at time: ', subtitle[thisI].start)
                print('TO frame: ', subtitle[nextI].text)
                print('until time: ', subtitle[nextI].start)
                
                self.start(
                    subtitle[thisI].text,
                    subtitle[thisI].start,
                    subtitle[nextI].text,
                    subtitle[nextI].start
                )
            nextI += 1

    # NB: this is linear interpolation only!       

    def getInterpolatedFrame(self, current_time):
        # Calculate the interpolated DMX frame
        # print("Getting int frame at ", current_time)
        ct = self.srt_to_seconds(current_time)
        # print("Current int frame time after conversion ", ct, " target_time: ", self.target_time)
        # print("Target time minus current time: ", self.target_time - ct)
        
        frame_diff = self.target_frame[0] - self.start_frame[0]
        period = self.target_time - self.start_time
        # print("Frame diff: ", frame_diff)
        # print("interpolation period: ", period)

        # print("ct/tt * frame diff + start: ", ((ct/self.target_time)*frame_diff) + self.start_frame[0])
        normalized_ct = ct - self.start_time

        val = int(((normalized_ct/period)*frame_diff) + self.start_frame[0])

        print("return (1) interpolated value! :: ", val, " sf: ", self.start_frame[0], " ef: ", self.target_frame[0])

        if (ct >= self.target_time - self.twiddle) or (val == self.target_frame[0]):
            self.running = False
            self.clear()
            print("Target reached!")
            return self.target_frame      
        else:
            return [val, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        
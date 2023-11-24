import os
from os.path import splitext
from content_reader import content_in_dir
import logging
logging.basicConfig(level=logging.INFO)


class BasePathInvalid(Exception):
    pass


class FileNotFound(Exception):
    pass


JSON_LIST_FILE = "content.json"


class FileExplorer():
    # note - tree traversal here could be memo'd
    # with a dict
    def __init__(self, media_base_path) -> None:
        self.media_base_path = media_base_path
        self.mpegOnly = True
        self.mlpOnly = False
        self.allFormats = False
        self.BUILT_PATH = None

    def track_by_track_id(self, track_id: str):

        logging.info("Getting track id: " + track_id)

        track = {"Path": "/not/valid.mp4"}
        path_to_track = "/not/valid.mp4"
        path_to_srt = "/not/valid.srt"

        for root, _, _ in os.walk(self.media_base_path, topdown=True):
            this_root_dir = content_in_dir(root)

            logging.debug("____content in this dir " + str(this_root_dir))

            for file in this_root_dir:
                if file['ID'] == track_id:
                    track = file
                    path_to_track = os.path.join(root, file['Path'])
                    expected_srt_filename = splitext(file['Path'])[0] + ".srt"
                    path_to_srt = os.path.join(
                        root, expected_srt_filename)
                    if not os.path.exists(path_to_srt):
                        logging.warning("SRT file: " + path_to_srt + " does not exist in the file system for track: " + path_to_track)
                        
                    break

        return (track, path_to_track, path_to_srt)

    def contents_by_directory_id(self, directory_id: str):

        NEW_TRACK_ARRAY = None
        NEW_SRT_ARRAY = None
        TRACK_ARRAY_UNFILTERED = None

        # return a graceful error if the usb stick isn't mounted
        # or if the base path is corrutpted somehow
        if os.path.isdir(self.media_base_path) == False:
            raise BasePathInvalid

        # from here, we know that we're starting in a good place
        # we have an id (there may be hash collisions if the filenames are the same) - we're here to fix this!
        # with this id, walk the directories until we have a match
        # it might return at least one folder, in which case we display the filenames
        # it might return an array of audio files (size 1 or more), in which case we display the player screen
        #
        # note - the frontend probably handles the above, this just needs to return arrays

        for root, _, _ in os.walk(self.media_base_path, topdown=True):
            this_root_dir = content_in_dir(root)
            for file in this_root_dir:
                if file['ID'] == directory_id:
                    self.BUILT_PATH = os.path.join(root, file['Path'])
                    break

        print('BUILT_PATH after OS WALK: ' + str(self.BUILT_PATH))

        if self.BUILT_PATH is None:
            self.BUILT_PATH = self.media_base_path

        TRACK_ARRAY_UNFILTERED = content_in_dir(self.BUILT_PATH)
        NEW_SRT_ARRAY = TRACK_ARRAY_UNFILTERED

        if self.mpegOnly:
            NEW_TRACK_ARRAY = [x for x in TRACK_ARRAY_UNFILTERED if ((x['Name'] != JSON_LIST_FILE) and (
                splitext(x['Name'])[1].lower() != ".srt") and (splitext(x['Name'])[1].lower() != ".mlp"))]
        elif self.mlpOnly:
            NEW_TRACK_ARRAY = [x for x in TRACK_ARRAY_UNFILTERED if ((x['Name'] != JSON_LIST_FILE) and (
                splitext(x['Name'])[1].lower() != ".srt") and (splitext(x['Name'])[1].lower() != ".mp4"))]
        elif self.allFormats:
            NEW_TRACK_ARRAY = [x for x in TRACK_ARRAY_UNFILTERED if (
                (x['Name'] != JSON_LIST_FILE) and (splitext(x['Name'])[1].lower() != ".srt"))]

        NEW_SRT_ARRAY = [x for x in TRACK_ARRAY_UNFILTERED if splitext(x['Name'])[
            1].lower() == ".srt"]

        return (NEW_TRACK_ARRAY, NEW_SRT_ARRAY)

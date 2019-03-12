import os
import unittest
import shutil
import json
import sys

TMP_DIR = os.path.join(os.path.dirname(__file__), "tmp")
TRACKS_DIR = "/Volumes/GoogleDrive/Team Drives/LushRooms/Tracks"

from content_reader import content_in_dir

class TestContentJson(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TMP_DIR):
            shutil.rmtree(TMP_DIR)

        os.makedirs(TMP_DIR)

        print(TMP_DIR)


    def test_create_json(self):

        ref_json_file = os.path.join(TRACKS_DIR, "content.json")
        output_file = os.path.join(TMP_DIR, "content.json")
        output = {}

        with open(ref_json_file, "r") as f:
            ref = json.loads(f.read())


        output = content_in_dir(TRACKS_DIR)
        self.maxDiff = None

        print(json.dumps(output, indent=4, sort_keys=True))
        # self.assertEqual(ref, output)


    def test_create_json_2(self):

        dir = os.path.join(TRACKS_DIR, "01_Comforter")

        ref_json_file = os.path.join(dir, "content.json")
        # output_file = os.path.join(TMP_DIR, "01_Conforter", "content.json")
        output = {}

        with open(ref_json_file, "r") as f:

            ref = json.loads(f.read())

            print(json.dumps(ref, indent=4, sort_keys=True))

        output = content_in_dir(dir)
        self.maxDiff = None

        print(json.dumps(output, indent=4, sort_keys=True))
import datetime
import os
import random

ALPHA_NUMERIC = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

MIME_TYPES = {
    "json": "application/json",
    "mp4": "video/mp4",
}

def generateNewRandomAlphaNumeric(length):
    random.seed()
    values = []
    for i in range(length):
        values.append(random.choice(ALPHA_NUMERIC))
    return "".join(values)


def get_mime_type(filename):
    ext = os.path.splitext(filename)[1][1:]
    return MIME_TYPES.get(ext, "application/octet-stream")


def content_in_dir(dir):

    content = []

    filenames = os.listdir(dir)
    sorted_filenames = sorted(filenames)

    for filename in sorted_filenames:
        filepath = os.path.join(dir, filename)
        is_dir = os.path.isdir(filepath)
        if is_dir:
            mime_type = "inode/directory"
            size = -1
        else:
            mime_type = get_mime_type(filename)
            size = os.path.getsize(filepath)

        mod_time_ts = os.path.getmtime(filepath)
        dt = datetime.datetime.fromtimestamp(mod_time_ts)

        content.append(
            {
                "ID": generateNewRandomAlphaNumeric(33),
                "IsDir": is_dir,
                "MimeType": mime_type,
                "ModTime": dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "Name": filename,
                "Path": filename,
                "Size": size
            }
        )

    return content
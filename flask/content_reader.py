import datetime
import os
import random
import hashlib


MIME_TYPES = {
    "json": "application/json",
    "mp4": "video/mp4",
}


def get_mime_type(filename):
    ext = os.path.splitext(filename)[1][1:]
    return MIME_TYPES.get(ext, "application/octet-stream")


def id_for_filename(filepath):
    md5 = hashlib.md5()
    to_hash = filepath.encode("utf-8")
    md5.update(to_hash)
    return md5.hexdigest()


def content_in_dir(dir: str):

    content = []

    filenames = os.listdir(dir)
    sorted_filenames = sorted(filenames)

    for filename in sorted_filenames:
        if not filename.startswith('.'):
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
            modifed_time_pretty = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            content.append(
                {
                    "ID": id_for_filename(filepath),
                    "IsDir": is_dir,
                    "MimeType": mime_type,
                    "ModTime": modifed_time_pretty,
                    "Name": filename,
                    "Path": filename,
                    "Size": size,
                    "AbsolutePath": filepath
                }
            )

    return content

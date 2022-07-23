from models import Video
from mongoengine.signals import post_save
from requests import post
from flask import request
from os import environ
from os import mkdir
from os.path import join
from os.path import basename
from os import devnull
from os import remove
from os import rename
from moviepy.editor import VideoFileClip
import os
import ffmpeg
from pathlib import Path
from shutil import rmtree
from threading import Thread


def compress_video(filename, target_size):
    min_audio_bitrate = 32000
    max_audio_bitrate = 256000

    probe = ffmpeg.probe(filename)
    # Video duration, in s.
    duration = float(probe["format"]["duration"])
    # Audio bitrate, in bps.
    audio_bitrate = float(
        next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)[
            "bit_rate"
        ]
    )
    # Target total bitrate, in bps.
    target_total_bitrate = (target_size * 1024 * 8) / (1.073741824 * duration)

    # Target audio bitrate, in bps
    if 10 * audio_bitrate > target_total_bitrate:
        audio_bitrate = target_total_bitrate / 10
        if audio_bitrate < min_audio_bitrate < target_total_bitrate:
            audio_bitrate = min_audio_bitrate
        elif audio_bitrate > max_audio_bitrate:
            audio_bitrate = max_audio_bitrate
    # Target video bitrate, in bps.
    video_bitrate = target_total_bitrate - audio_bitrate

    i = ffmpeg.input(filename)
    ffmpeg.output(
        i, devnull, **{"c:v": "libx264", "b:v": video_bitrate, "pass": 1, "f": "mp4"}
    ).overwrite_output().run()
    ffmpeg.output(
        i,
        "{}compressed_{}".format(
            filename.replace(basename(filename), ""), basename(filename)
        ),
        **{
            "c:v": "libx264",
            "b:v": video_bitrate,
            "pass": 2,
            "c:a": "aac",
            "b:a": audio_bitrate,
        }
    ).overwrite_output().run()


def resize(clip, filename):
    clip_resized = clip.resize(height=576, width=1024)
    clip_resized.write_videofile(
        "{}resize_{}".format(
            filename.replace(basename(filename), ""), basename(filename)
        ),
    )


def screenshot(clip, filename):
    clip.save_frame(
        "{}{}.png".format(
            filename.replace(basename(filename), ""), Path(filename).stem
        ),
        t=int(clip.duration / 2),
    )


def gif(clip, filename):
    clip.subclip(int(clip.duration / 2), int(clip.duration / 2) + 3).write_gif(
        "{}{}.gif".format(
            filename.replace(basename(filename), ""), Path(filename).stem
        ),
    )


def process_video(filename, document):
    # First we load the video into a moviepy object
    clip = VideoFileClip(filename)

    # Then we extract a screenshot
    screenshot(clip, filename)
    post_file(document, "{}.png".format(Path(filename).stem), "thumbnail")

    # # Then we extract a gif
    gif(clip, filename)
    post_file(document, "{}.gif".format(Path(filename).stem), "gif")

    # Then we resize the video
    resize(clip, filename)
    remove(filename)
    rename(
        "{}resize_{}".format(
            filename.replace(basename(filename), ""), basename(filename)
        ),
        filename,
    )

    # Then we compress the video
    compress_video(filename, 7000)
    remove(filename)
    rename(
        "{}compressed_{}".format(
            filename.replace(basename(filename), ""), basename(filename)
        ),
        filename,
    )
    post_file(document, basename(filename), "video")
    rmtree(str(document.id))


def post_file(document, filename, field):
    post(
        "http://127.0.0.1:5000/aws_s3/files/file/{}__{}".format(
            str(document.id), filename
        ),
        files={
            "file": (
                filename,
                open("{}/{}".format(str(document.id), filename), "rb"),
            )
        },
    )

    setattr(
        document,
        field,
        "https://{}.s3.{}.amazonaws.com/{}".format(
            environ.get("AWS_S3_DEFAULT_BUCKET"),
            "eu-west-2",
            "{}/{}".format(str(document.id), filename),
        ),
    )
    document.save()


def save_video(sender, document, created):
    if created:
        file = request.files.get("file")
        filename = join(str(document.id), file.filename)

        mkdir(str(document.id))
        with open(filename, "wb") as w:
            w.write(file.read())

        th = Thread(target=process_video, args=(filename, document))
        th.start()


post_save.connect(save_video, sender=Video)

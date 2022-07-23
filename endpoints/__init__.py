# Standard library imports
import os
from werkzeug.datastructures import FileStorage
from datetime import datetime
from requests import post
from requests import get

# Third party imports
from flask import Flask
from flask import request
from flask import g
from flask_restx import Namespace
from flask_restx import Resource as _Resource
from flask_restx.fields import DateTime
from flask_restx.fields import Float
from flask_restx.fields import Integer
from flask_restx.fields import List
from flask_restx.fields import Nested
from flask_restx.fields import String
from flask_restx.fields import Boolean
from flask_restx.fields import Raw

# Local application imports
import models


class Resource(_Resource):
    dispatch_requests = []

    def __init__(self, api=None, *args, **kwargs):
        super(Resource, self).__init__(api, args, kwargs)

    def dispatch_request(self, *args, **kwargs):

        tmp = request.args.to_dict()

        if request.method == "GET":
            request.args = tmp

            [
                tmp.update({k: v.split(",")})
                for k, v in tmp.items()
                if k.endswith("__in")
            ]

            [
                tmp.update({k: v.split(",")})
                for k, v in tmp.items()
                if k.startswith("$sort")
            ]

        if (
            request.method == "POST"
            and request.headers.get("Content-Type", "") == "application/json"
        ):
            json = request.get_json()

            for key, value in json.items():
                if isinstance(value, dict) and key in routes:
                    if "id" in value:
                        json[key] = value["id"]

                    else:
                        item = post(
                            "http://localhost:5000/api/{}".format(key), json=value
                        )
                        json[key] = item.json()["id"]

        for method in self.dispatch_requests:
            method(self, args, kwargs)

        return super(Resource, self).dispatch_request(*args, **kwargs)


api = Namespace("api", description="")
video_base = api.model("video_base", models.Video.base())
video_reference = api.model("video_reference", models.Video.reference())
video_full = api.clone("video", models.Video.model(api))


@api.route("/video")
class VideoController(Resource):
    file_upload_parser = api.parser()
    file_upload_parser.add_argument(
        "file", location="files", type=FileStorage, required=True
    )

    @api.marshal_list_with(api.models.get("video"), skip_none=True)
    def get(self):
        return models.Video.qry(request.args)

    @api.marshal_with(api.models.get("video"), skip_none=True)
    @api.expect(file_upload_parser)
    def post(self):
        file = request.files.get("file")
        return models.Video.post({"title": file.filename})

    @api.marshal_with(api.models.get("video"), skip_none=True)
    def put(self):
        return models.Video.put(request.get_json())

    @api.marshal_with(api.models.get("video"), skip_none=True)
    def patch(self):
        return models.Video.patch(request.get_json())


@api.route("/video/<video_id>")
class BaseVideoController(Resource):
    @api.marshal_with(api.models.get("video"), skip_none=True)
    def get(self, video_id):
        return models.Video.objects.get(id=video_id).to_json()

    @api.marshal_with(api.models.get("video"), skip_none=True)
    def put(self, video_id):
        return models.Video.put({"id": video_id, **request.get_json()})

    @api.marshal_with(api.models.get("video"), skip_none=True)
    def patch(self, video_id):
        return models.Video.patch({"id": video_id, **request.get_json()})

    def delete(self, video_id):
        return models.Video.get(id=video_id).delete()


routes = list(set([x.urls[0].split("/")[1] for x in api.resources]))

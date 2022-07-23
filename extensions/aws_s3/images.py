from werkzeug.datastructures import FileStorage
from datetime import datetime
from datetime import timedelta
from io import BytesIO

# Third party imports
from flask import Flask
from flask import request
from flask_restx import Namespace
from flask_restx.fields import String
from flask_restx.fields import DateTime
from flask_restx.fields import Boolean
from flask_restx.fields import Float as Number
from flask import g
from PIL import Image
from PIL import ImageOps

# Local imports
from endpoints import Resource
from extensions.aws_s3.methods import generate_presigned_urls_for_bucket
from extensions.aws_s3.methods import list_objects
from extensions.aws_s3.methods import generate_presigned_url
from extensions.aws_s3.methods import upload_file
from extensions.aws_s3.methods import delete_object


api = Namespace("aws_s3/images")


@api.route("/image/<filename>")
class File(Resource):
    image_upload_parser = api.parser()
    image_upload_parser.add_argument(
        "file", location="files", type=FileStorage, required=True
    )

    def get(self, filename):
        return generate_presigned_url(
            "{}/{}".format(filename, request.args.get("size", "original"))
        )

    @api.expect(image_upload_parser)
    def post(self, filename):
        image = Image.open(BytesIO(request.files.get("file").read()))

        in_mem_file = BytesIO()
        image.save(in_mem_file, format=image.format, filename=filename)
        in_mem_file.seek(0)
        file = in_mem_file
        file.content_type = request.files.get("file").content_type
        upload_file(file, "{}/original".format(filename))

        in_mem_file = BytesIO()
        image.thumbnail((200, 200))
        image.save(in_mem_file, format=image.format, filename=filename)
        in_mem_file.seek(0)
        file = in_mem_file
        file.content_type = request.files.get("file").content_type
        upload_file(file, "{}/thumbnail".format(filename))

    def delete(self, filename):
        return delete_object(filename)

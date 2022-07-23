from werkzeug.datastructures import FileStorage
from datetime import datetime
from datetime import timedelta

# Third party imports
from flask import Flask
from flask import request
from flask_restx import Namespace
from flask_restx.fields import String
from flask_restx.fields import DateTime
from flask_restx.fields import Boolean
from flask_restx.fields import Float as Number
from flask import g

# Local imports
from endpoints import Resource
from extensions.aws_s3.methods import generate_presigned_urls_for_bucket
from extensions.aws_s3.methods import list_objects
from extensions.aws_s3.methods import generate_presigned_url
from extensions.aws_s3.methods import upload_file
from extensions.aws_s3.methods import delete_object


api = Namespace("aws_s3/files")


@api.route("/bucket_search")
class FileSearch(Resource):
    def get(self):
        return list_objects(**request.args)


@api.route("/bucket_retrieval")
class FileRetrieval(Resource):
    def get(self):
        return generate_presigned_urls_for_bucket()


@api.route("/file/<filename>")
class File(Resource):
    file_upload_parser = api.parser()
    file_upload_parser.add_argument(
        "file", location="files", type=FileStorage, required=True
    )

    def get(self, filename):
        return generate_presigned_url(filename)

    @api.expect(file_upload_parser)
    def post(self, filename):
        file = request.files.get("file")

        if not file:
            return "File missing"

        if file.filename == "":
            return "Please select a file"

        if upload_file(file, filename):
            return generate_presigned_url(filename)

        raise BadRequest("Error uploading image")

    def delete(self, filename):
        return delete_object(filename)

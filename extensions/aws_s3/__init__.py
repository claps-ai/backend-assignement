import os
from boto3 import session
from flask import request
from endpoints import Resource

client = session.Session().client("s3")
default_bucket = os.environ.get("AWS_S3_DEFAULT_BUCKET", None)


def dispatch_request(self, *args, **kwargs):
    pass


Resource.dispatch_requests.append(dispatch_request)

from extensions.aws_s3 import client
from extensions.aws_s3 import default_bucket


def generate_presigned_urls_for_bucket(prefix="", bucket=default_bucket):
    files = list_objects(bucket, prefix)

    return [generate_presigned_url(bucket, key) for key in files]


def list_objects(prefix="", bucket=default_bucket):
    return [
        x.get("Key")
        for x in client.list_objects(Bucket=bucket, Prefix=prefix).get("Contents", [])
    ]


def generate_presigned_url(key, bucket=default_bucket):
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600,
    )


def upload_file(file, filename, bucket=default_bucket):
    filename = filename.replace("__", "/", 1)
    client.upload_fileobj(
        file,
        bucket,
        str(filename),
    )
    return filename


def delete_object(key, bucket=default_bucket):
    client.delete_object(Bucket=bucket, Key=key)

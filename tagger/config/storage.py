import os

import boto3

S3_CLIENT = boto3.resource("s3")
IMAGE_BUCKET = os.getenv("IMAGE_BUCKET", "hotosm-osm-tagger")

# MinIO
# S3_CLIENT = boto3.resource(
#   's3',
#   endpoint_url='http://127.0.0.1:9000',
#   config=boto3.session.Config(signature_version='s3v4'),
#   aws_access_key_id="<S3_ACCESS_KEY>",
#   aws_secret_access_key="<S3_SECRET_KEY>",
# )

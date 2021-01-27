import uuid
import boto3
from botocore.exceptions import ClientError

from six import raise_from

from zc_events.config import settings


class S3IOException(Exception):
    pass


def save_string_contents_to_s3(stringified_data, aws_bucket_name, content_key=None,
                               aws_access_key_id=None, aws_secret_access_key=None):
    """Save data (provided in string format) to S3 bucket and return s3 key."""

    aws_access_key_id = aws_access_key_id or settings.AWS_ACCESS_KEY_ID
    aws_secret_access_key = aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY

    try:
        if not content_key:
            content_key = str(uuid.uuid4())

        session = boto3.session.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        s3 = session.resource('s3')
        s3.Bucket(aws_bucket_name).put_object(Key=content_key, Body=stringified_data)
        return content_key
    except ClientError as error:
        msg = 'Failed to save contents to S3. aws_bucket_name: {}, content_key: {}, ' \
              'error: {}'.format(aws_bucket_name, content_key, error)
        raise_from(S3IOException(msg), error)


def save_file_contents_to_s3(filepath, aws_bucket_name, content_key=None,
                             aws_access_key_id=None, aws_secret_access_key=None):
    """Upload a local file to S3 bucket and return S3 key."""

    aws_access_key_id = aws_access_key_id or settings.AWS_ACCESS_KEY_ID
    aws_secret_access_key = aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY

    try:
        if not content_key:
            content_key = str(uuid.uuid4())

        session = boto3.session.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        s3 = session.resource('s3')
        s3.Bucket(aws_bucket_name).upload_file(filepath, content_key)
        return content_key
    except ClientError as error:
        msg = 'Failed to save contents to S3. filepath: {}, aws_bucket_name: {}, content_key: {}, ' \
              'error: {}'.format(filepath, aws_bucket_name, content_key, error)
        raise_from(S3IOException(msg), error)


def read_s3_file_as_string(aws_bucket_name, content_key, delete=False,
                           aws_access_key_id=None, aws_secret_access_key=None):
    """Get the contents of an S3 file as string and optionally delete the file from the bucket."""

    aws_access_key_id = aws_access_key_id or settings.AWS_ACCESS_KEY_ID
    aws_secret_access_key = aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY

    try:
        session = boto3.session.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        s3 = session.resource('s3')
        obj = s3.Object(aws_bucket_name, content_key).get()
        output = obj['Body'].read()

        if delete:
            obj.delete()

        return output
    except ClientError as error:
        msg = 'Failed to save contents to S3. aws_bucket_name: {}, content_key: {}, delete: {}, ' \
              'error: {}'.format(aws_bucket_name, content_key, delete, error)
        raise_from(S3IOException(msg), error)

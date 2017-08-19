import binascii
import hashlib
import os

# Max size in bytes before uploading in parts
AWS_UPLOAD_MAX_SIZE = 20 * 1024 * 1024
# Size of parts when uploading in parts
AWS_UPLOAD_PART_SIZE = 8 * 1024 * 1024


def calculate_etag(f):
    """
    Source: https://stackoverflow.com/questions/6591047/etag-definition-changed-in-amazon-s3/28877788#28877788
    Get the md5 hash of a file stored in S3.

    with open('./myfile.txt', 'rb') as f:
        etag = s3_etag(f)

    :return: md5 hash that will match the ETag in S3
    """
    f.seek(0, os.SEEK_END)
    filesize = f.tell()

    f.seek(0)
    if filesize > AWS_UPLOAD_MAX_SIZE:
        block_count = 0
        md5string = b''
        for block in iter(lambda: f.read(AWS_UPLOAD_PART_SIZE), b''):
            h = hashlib.md5()
            h.update(block)
            md5string = md5string + binascii.unhexlify(h.hexdigest())
            block_count += 1

        h = hashlib.md5()
        h.update(md5string)
        return h.hexdigest() + "-" + str(block_count)

    else:
        h = hashlib.md5()
        for block in iter(lambda: f.read(AWS_UPLOAD_PART_SIZE), b''):
            h.update(block)
        return h.hexdigest()

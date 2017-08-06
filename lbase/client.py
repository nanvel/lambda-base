import botocore.session

from .settings import AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY


session = botocore.session.get_session()
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    session.set_credentials(
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY
    )
client = session.create_client('lambda', region_name=AWS_REGION)

AWS_REGION = None
AWS_ACCESS_KEY = None
AWS_SECRET_KEY = None


try:
    from local_settings import *
except ImportError:
    pass

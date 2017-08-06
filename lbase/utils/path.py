import os.path


PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..')


def rel(*path):
    return os.path.join(PROJECT_ROOT, *path)

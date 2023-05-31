# pyright: reportUnusedImport=false
"""The hubuum.models package.

See https://stackoverflow.com/questions/6336664/split-models-py-into-several-files
Sadly the import of the user model is required.
"""
from .iam import User  # noqa

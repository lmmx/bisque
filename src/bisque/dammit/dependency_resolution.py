"""
Import a library to autodetect character encodings. We'll support
any of a number of libraries that all support the same API:

* cchardet
* chardet
* charset-normalizer
"""
from contextlib import suppress

__all__ = ["chardet_module"]

chardet_module = None
try:
    #  PyPI package: cchardet
    import cchardet as chardet_module
except ImportError:
    try:
        #  Debian package: python-chardet
        #  PyPI package: chardet
        import chardet as chardet_module
    except ImportError:
        with suppress(ImportError):
            # PyPI package: charset-normalizer
            import charset_normalizer as chardet_module

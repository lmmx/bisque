__all__ = ["_invert"]


def _invert(d):
    "Invert a dictionary."
    return {v: k for k, v in list(d.items())}

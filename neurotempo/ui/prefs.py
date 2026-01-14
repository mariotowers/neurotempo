#neurotempo/ui/prefs.py

from PySide6.QtCore import QSettings

ORG = "Neurotempo"
APP = "Neurotempo"
KEY_MUSE_DEVICE = "muse/device_id"


def _s() -> QSettings:
    return QSettings(ORG, APP)


def get_saved_device_id() -> str | None:
    v = _s().value(KEY_MUSE_DEVICE, None)
    if not v:
        return None
    return str(v)


def save_device_id(device_id: str) -> None:
    _s().setValue(KEY_MUSE_DEVICE, device_id)


def forget_device_id() -> None:
    _s().remove(KEY_MUSE_DEVICE)
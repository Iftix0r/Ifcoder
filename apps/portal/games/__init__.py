"""O'yinlar uchun umumiy narsalar. Ro'yxatning o'zi ``apps/portal/catalog.py`` da."""


class BadPayload(Exception):
    """Brauzerdan noto'g'ri tuzilgan so'rov keldi."""


def code_from(payload: dict) -> str:
    code = payload.get("code")
    if not isinstance(code, str):
        raise BadPayload
    return code

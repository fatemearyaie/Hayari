def username_identifier(username: str) -> dict:
    if not username:
        return {"email": None, "phone": None}

    username = username.strip()

    if "@" in username:
        return {"email": username.lower(),"phone": None,}

    phone = (username.replace(" ", "").replace("+", "").replace("-", ""))
    return {"email": None, "phone": phone,}

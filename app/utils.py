def trunc(text: str, n: int = 400):
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "..."

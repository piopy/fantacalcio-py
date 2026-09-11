import re, ast, unicodedata


def norm(s):
    t = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())).strip()
    if t == "ac milan":
        t = "milan"
    return t


def parse_skills(s):
    if isinstance(s, list):
        return s
    if not isinstance(s, str) or not s:
        return []
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return [x.strip(" '\"[]") for x in s.split(",") if x.strip(" '\"[]")]


def clip(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

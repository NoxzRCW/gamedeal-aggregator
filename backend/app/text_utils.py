import re

# le symbole ™/®/© casse la recherche par titre sur ITAD comme sur l'index
# Algolia d'Instant Gaming (résultats sans rapport ou 0 résultat)
_TRADEMARK_RE = re.compile(r"[™®©]")


def sanitize_title(query: str) -> str:
    return re.sub(r"\s+", " ", _TRADEMARK_RE.sub("", query)).strip()

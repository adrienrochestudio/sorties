"""Fonctions partagées : chemins, normalisation de texte, dates, lecture/écriture JSON."""
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"
CONFIG = RACINE / "config"
PARIS = ZoneInfo("Europe/Paris")


def lire(chemin, defaut=None):
    p = Path(chemin)
    if not p.exists():
        return defaut
    return json.loads(p.read_text(encoding="utf-8"))


def ecrire(chemin, donnees, indent=None):
    p = Path(chemin)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(donnees, ensure_ascii=False, indent=indent), encoding="utf-8")


def norm(texte):
    """Minuscules sans accents, espaces réduits : base de toutes les comparaisons."""
    if not texte:
        return ""
    t = unicodedata.normalize("NFKD", str(texte))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = t.replace("’", "'")
    return re.sub(r"\s+", " ", t).strip()


def sans_html(texte):
    return re.sub(r"<[^>]+>", " ", texte or "")


def aujourdhui():
    return datetime.now(PARIS).date()


def parse_dt(valeur):
    """ISO 8601 ou AAAA-MM-JJ vers datetime à l'heure de Paris. None si illisible."""
    if not valeur:
        return None
    v = str(valeur).strip()
    try:
        if len(v) == 10:
            return datetime.fromisoformat(v).replace(tzinfo=PARIS)
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=PARIS)
        return dt.astimezone(PARIS)
    except ValueError:
        return None


def arrondissement(code_postal, ville=""):
    cp = re.sub(r"\D", "", str(code_postal or ""))
    if len(cp) == 5 and cp.startswith("75"):
        n = int(cp[3:])
        if cp == "75116":
            return 16
        return n if 1 <= n <= 20 else None
    if "paris" in norm(ville):
        m = re.search(r"\b(\d{1,2})(?:e|er|eme)\b", norm(ville))
        if m:
            return int(m.group(1))
    return None


def prix_euros(texte):
    """Premier montant en euros trouvé dans un texte libre, sinon None."""
    if not texte:
        return None
    t = norm(sans_html(texte)).replace(",", ".")
    m = re.findall(r"(\d+(?:\.\d+)?)\s*(?:€|euros?|eur\b)", t)
    if m:
        return min(float(x) for x in m)
    return None


def tranche_prix(gratuit, montant):
    if gratuit:
        return "gratuit"
    if montant is None:
        return "inconnu"
    if montant <= 15:
        return "0-15"
    if montant <= 50:
        return "15-50"
    if montant <= 100:
        return "50-100"
    return "trop-cher"

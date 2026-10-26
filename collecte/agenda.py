"""Relit l'agenda Google (adresse iCal secrète, secret AGENDA_ICS) dans la GitHub Action.

- Reconstruit data/suggeres.json : les [Sortie suggérée] présentes dans l'agenda (id, date, lieu, thème).
- Apprend des suppressions : une suggestion à venir qui a disparu de l'agenda baisse le poids de son lieu et de son thème.
Sans secret ou en cas d'erreur réseau, ne touche à rien.
"""
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from commun import DATA, PARIS, aujourdhui, ecrire, lire, norm, parse_dt

MARQUE = "[Sortie suggérée]"


def vevents(texte):
    texte = re.sub(r"\r?\n[ \t]", "", texte)
    for bloc in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", texte, re.S):
        champs = {}
        for ligne in bloc.strip().splitlines():
            if ":" in ligne:
                cle, val = ligne.split(":", 1)
                champs.setdefault(cle.split(";")[0].upper(), (cle, val.strip()))
        yield champs


def texte_ics(v):
    return v.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def debut(champ):
    cle, val = champ
    try:
        if val.endswith("Z"):
            return datetime.strptime(val, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(PARIS)
        if "VALUE=DATE" in cle.upper() or len(val) == 8:
            return datetime.strptime(val[:8], "%Y%m%d").replace(tzinfo=PARIS)
        return datetime.strptime(val[:15], "%Y%m%dT%H%M%S").replace(tzinfo=PARIS)
    except ValueError:
        return None


VIDES = {"paris", "salle", "grande", "theatre", "musee", "cinema", "eglise", "rue", "avenue", "boulevard", "place", "bibliotheque",
         "mediatheque", "galerie", "centre", "maison", "institut", "espace", "studio", "club", "jazz",
         "opera", "auditorium", "hotel", "conservatoire", "musique", "cite", "fondation"}


def mots(texte):
    return {m for m in re.findall(r"[a-z0-9]{4,}", norm(texte)) if m not in VIDES}


def meme_lieu(a, b):
    return bool(mots(a) & mots(b))


def theme_de(desc):
    m = re.search(r"Th[eè]me\s*:\s*([^\n]+)", desc)
    return norm(m.group(1)).split("/")[0].strip() if m else "autre"


def main():
    url = os.environ.get("AGENDA_ICS", "").strip()
    if not url:
        print("AGENDA_ICS absent : agenda non relu")
        return
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "sorties-agenda/1.0"})
        ics = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="replace")
    except Exception as err:
        print(f"agenda illisible : {type(err).__name__}")
        return

    precedent = lire(DATA / "suggeres.json", [])
    par_id = {s["id"]: s for s in precedent if s.get("id")}
    brut = {e["id"]: e for e in lire(DATA / "brut" / "evenements.json", [])}
    par_heure = {}
    for e in brut.values():
        par_heure.setdefault((e.get("debut") or "")[:16], []).append(e)

    lieux_base = [l for f in sorted((DATA / "seed").glob("lieux_*.json")) for l in lire(f, []) if l.get("lat")]

    def coords_lieu(lieu):
        cible = mots(lieu.split(",")[0])
        meilleur = max(lieux_base, key=lambda l: len(mots(l["nom"]) & cible), default=None)
        if meilleur and len(mots(meilleur["nom"]) & cible) >= 1:
            return meilleur["lat"], meilleur["lon"]
        return None, None

    limite = aujourdhui() - timedelta(days=30)
    actuels = []
    for c in vevents(ics):
        desc = texte_ics(c.get("DESCRIPTION", ("", ""))[1])
        if MARQUE not in desc or c.get("STATUS", ("", ""))[1].upper() == "CANCELLED" or "DTSTART" not in c:
            continue
        d = debut(c["DTSTART"])
        if not d or d.date() < limite:
            continue
        titre = re.sub(r"^Avec [^-]{1,40} - ", "", texte_ics(c.get("SUMMARY", ("", ""))[1]))  # pas de prénoms en public
        lieu = texte_ics(c.get("LOCATION", ("", ""))[1])
        ref = re.search(r"R[ée]f\s*:\s*([0-9a-f]{12})", desc)
        lien = re.search(r"Lien\s*:\s*(\S+)", desc)
        source = brut.get(ref.group(1)) if ref else None
        if not source:
            for e in par_heure.get(d.isoformat()[:16], []):
                if e.get("lieu") and meme_lieu(e["lieu"], lieu):
                    source = e
                    break
        ancien = par_id.get(ref.group(1)) if ref else None
        if not ancien:
            ancien = next((p for p in precedent if p.get("d", "")[:16] == d.isoformat()[:16]
                           and meme_lieu(p.get("l", ""), lieu)), None)
        ident = (ref.group(1) if ref else None) or (ancien or {}).get("id") or (source or {}).get("id") or "cal-" + c.get("UID", ("", ""))[1][:20]
        s = {"id": ident, "t": titre, "d": d.isoformat()[:16], "l": lieu.split(",")[0],
             "lat": (source or {}).get("lat") or (ancien or {}).get("lat"),
             "lon": (source or {}).get("lon") or (ancien or {}).get("lon"),
             "p": (source or {}).get("tranche") or (ancien or {}).get("p") or "inconnu",
             "th": theme_de(desc), "u": lien.group(1) if lien else (source or {}).get("url", "")}
        if s["lat"] is None:
            s["lat"], s["lon"] = coords_lieu(lieu)
        actuels.append(s)

    if not actuels and precedent:
        print("agenda relu mais aucune suggestion trouvée : rien n'est modifié par prudence")
        return
    maintenant = datetime.now(PARIS).isoformat()[:16]
    presents = {s["id"] for s in actuels}
    supprimes = [s for s in precedent if s.get("d", "") > maintenant and s.get("id") not in presents
                 and not any(a["d"] == s.get("d", "")[:16] and meme_lieu(a["l"], s.get("l", "")) for a in actuels)]
    if supprimes:
        p = lire(DATA / "poids.json", {"lieux": {}, "themes": {}, "mots": {}})
        for s in supprimes:
            k = norm(s.get("l"))[:40]
            if k:
                p["lieux"][k] = max(-10, p["lieux"].get(k, 0) - 2)
            th = s.get("th")
            if th:
                p["themes"][th] = max(-6, p["themes"].get(th, 0) - 1)
        ecrire(DATA / "poids.json", p, indent=1)
    # Le dépôt est public : on ne garde que ce qu'il faut pour les leçons (pas de titre, lien ni coordonnées)
    minimal = [{k: s[k] for k in ("id", "d", "l", "th")} for s in actuels]
    ecrire(DATA / "suggeres.json", sorted(minimal, key=lambda s: s["d"]), indent=0)
    print(f"agenda : {len(actuels)} suggestions, {len(supprimes)} suppressions apprises",
          [s["t"][:50] for s in supprimes])


if __name__ == "__main__":
    sys.exit(main())

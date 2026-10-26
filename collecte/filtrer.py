"""Filtres durs, score, diversité : produit la shortlist que Claude lit le dimanche, et les données de la carte.

Entrées : data/brut/evenements.json, config/*.json, data/poids.json (leçons), data/suggeres.json (déjà créés).
Sorties : data/shortlist.json (versionné, compact), site/carte.json.
"""
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from commun import CONFIG, DATA, SITE, aujourdhui, ecrire, lire, norm, parse_dt
from creneaux import buckets

JOURS = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
R = lire(CONFIG / "regles.json")
G = lire(CONFIG / "gouts.json")
POIDS = lire(DATA / "poids.json", {"lieux": {}, "themes": {}, "mots": {}})
SUGGERES = lire(DATA / "suggeres.json", [])


def contient(texte, motif):
    return re.search(r"(?<![a-z])" + re.escape(motif), texte) is not None


def texte_de(e):
    return norm(" ".join([e["titre"], e["resume"], e["tags"], e["lieu"]]))


def rejete(e, t):
    for m in R["rejets"]:
        if contient(t, m):
            return m
    for motif in R.get("rejets_regex", []):
        if re.search(motif, t):
            return motif
    for m, sauf in R["rejets_sauf"].items():
        if contient(t, m) and not any(contient(t, s) for s in sauf):
            return m
    return None


def themes(t):
    trouves = [th for th, mots in G["themes"].items() if any(contient(t, m) for m in mots)]
    return trouves or ["autre"]


def score_gout(t):
    return sum(int(p) for p, mots in G["poids"].items() for m in mots if contient(t, m))


def score(e, t, ths):
    s = min(score_gout(t), 30)
    lieu = norm(e["lieu"])
    if any(f in lieu for f in R["lieux_favoris"]):
        s += 6
    elif any(f in lieu for f in R["lieux_connus"]):
        s += 3
    s += R["prix_bonus"].get(e["tranche"], 0)
    s += sum(v for k, v in POIDS.get("lieux", {}).items() if k and k in lieu)
    s += sum(POIDS.get("themes", {}).get(th, 0) for th in ths)
    s += sum(v for k, v in POIDS.get("mots", {}).items() if k and contient(t, k))
    if e["periode"]:
        s -= 3
    return s


def disponible(dt, periode):
    """Lun-jeu après 18h, ven-sam tout, dim avant 18h (le dimanche soir n'est gardé que signalé)."""
    if periode or dt.hour == 0 and dt.minute == 0:
        return True, False
    wd = dt.weekday()
    if wd <= 3 and dt.strftime("%H:%M") < R["dispo"]["lundi_jeudi_debut_min"]:
        return False, False
    if wd == 6 and dt.strftime("%H:%M") >= R["dispo"]["dimanche_fin_max"]:
        return True, True
    return True, False


def zone_ok(e):
    if e["anticiper"] and e.get("categorie") == "hors_paris":
        return "hors_paris"
    if e["arr"] in R["arrondissements"]:
        return "paris"
    if e["arr"] is None and "paris" in norm(e["ville"]) and not norm(e["ville"]).startswith(("paris-la", "paris la")):
        return "paris?"
    return None


def court(e, sc, ths, decouverte, dim_soir):
    dt = parse_dt(e["debut"])
    quand = f"{JOURS[dt.weekday()]} {dt:%d/%m}" + ("" if e["periode"] else f" {dt:%H:%M}")
    if e["periode"] and e.get("fin"):
        quand += f" > {parse_dt(e['fin']):%d/%m}"
    lieu = e["lieu"] + (f" ({e['arr']}e)" if e.get("arr") else f" ({e['ville']})" if e["ville"] else "")
    prix = "gratuit" if e["gratuit"] or e["prix"] == 0 else (f"{e['prix']:g} €" if e["prix"] is not None else "?")
    c = {"id": e["id"], "t": e["titre"][:110], "d": quand, "l": lieu[:70], "p": prix, "th": ths[:2],
         "sc": sc, "u": e["url"]}
    if e.get("resa") and e["resa"] != e["url"]:
        c["r"] = e["resa"]
    if decouverte:
        c["dec"] = 1
    if e["periode"]:
        c["pe"] = 1
    if dim_soir:
        c["dim_soir"] = 1
    if e["anticiper"]:
        c["ant"] = e.get("billetterie") or 1
        if e.get("train"):
            c["train"] = e["train"]
    return c


def main():
    demain = aujourdhui() + timedelta(days=1)
    fin_horizon = demain + timedelta(weeks=R["horizon_semaines"])
    deja = {s.get("id") for s in SUGGERES}
    lieux_recents = defaultdict(list)
    for s in SUGGERES:
        d = parse_dt(s.get("debut"))
        if d:
            lieux_recents[norm(s.get("lieu"))].append(d.date())

    stats, candidats = Counter(), []
    for e in lire(DATA / "brut" / "evenements.json", []):
        dt = parse_dt(e["debut"])
        if not dt or not (demain <= dt.date() < fin_horizon):
            stats["hors_horizon"] += 1
            continue
        if e["id"] in deja:
            stats["deja_suggere"] += 1
            continue
        if e["tranche"] == "trop-cher":
            stats["trop_cher"] += 1
            continue
        zone = zone_ok(e)
        if not zone:
            stats["hors_zone"] += 1
            continue
        t = texte_de(e)
        if rejete(e, t):
            stats["rejet"] += 1
            continue
        ok, dim_soir = disponible(dt, e["periode"])
        if not ok:
            stats["horaire"] += 1
            continue
        ths = themes(norm(e["titre"] + " " + e["tags"]))
        sc = score(e, t, ths)
        forte = e["anticiper"] or any(f in norm(e["lieu"]) for f in R["lieux_forte_demande"])
        decouverte = score_gout(t) < 4
        candidats.append((e, dt, sc, ths, decouverte, dim_soir, forte, zone))
        stats["retenu"] += 1

    candidats.sort(key=lambda c: -c[2])
    shortlist, pris_ids, carte = [], set(), []
    for b in buckets(demain, R["horizon_semaines"]):
        d0, d1 = date.fromisoformat(b["debut"]), date.fromisoformat(b["fin"])
        if b["mode"] == "proche":
            quota_confort, quota_dec = 12, 4
        elif b["mode"] == "moyen":
            quota_confort, quota_dec = 4, 1
        else:
            quota_confort, quota_dec = 4, 0
        par_theme, choisis, n_conf, n_dec, n_per = Counter(), [], 0, 0, 0
        for e, dt, sc, ths, dec, dim_soir, forte, zone in candidats:
            if e["id"] in pris_ids or not (d0 <= dt.date() <= d1):
                continue
            if b["mode"] == "anticiper" and not forte:
                continue
            if zone == "hors_paris" and b["mode"] == "proche":
                continue
            lieu = norm(e["lieu"])
            if any(abs((dt.date() - j).days) < R["meme_lieu_jours"] for j in lieux_recents.get(lieu, [])):
                continue
            if any(norm(c["l"]).startswith(lieu[:25]) for c in choisis) and lieu:
                continue
            if par_theme[ths[0]] >= R["meme_theme_par_semaine"] * (3 if b["mode"] == "proche" else 1):
                continue
            if e["periode"] and n_per >= R.get("periodes_par_bucket", 3):
                continue
            if dec and n_dec < quota_dec and sc > -2:
                n_dec += 1
            elif not dec and n_conf < quota_confort:
                n_conf += 1
            else:
                continue
            par_theme[ths[0]] += 1
            n_per += int(e["periode"])
            pris_ids.add(e["id"])
            choisis.append({**court(e, sc, ths, dec, dim_soir), "_k": dt.isoformat()})
        choisis.sort(key=lambda c: c["_k"])
        for c in choisis:
            del c["_k"]
        shortlist.append({**b, "candidats": choisis})

    for e, dt, sc, ths, dec, dim_soir, forte, zone in candidats[:600]:
        if e.get("lat") is None or e.get("lon") is None:
            continue
        carte.append({"id": e["id"], "t": e["titre"][:120], "d": e["debut"], "f": e.get("fin"),
                      "l": e["lieu"], "a": e["adresse"], "lat": round(float(e["lat"]), 5),
                      "lon": round(float(e["lon"]), 5), "p": e["tranche"], "th": ths[0], "u": e["url"],
                      "ant": int(bool(forte)), "dec": int(dec), "pe": int(e["periode"]),
                      "s": int(e["id"] in pris_ids)})
    for s in SUGGERES:
        if s.get("lat") is not None:
            carte.append({**s, "sug": 1})

    ecrire(DATA / "shortlist.json", {"genere": aujourdhui().isoformat(), "stats": stats,
                                     "buckets": shortlist}, indent=0)
    ecrire(SITE / "carte.json", {"genere": aujourdhui().isoformat(), "evenements": carte})
    print(dict(stats), "| shortlist:", sum(len(b["candidats"]) for b in shortlist), "| carte:", len(carte))


if __name__ == "__main__":
    main()

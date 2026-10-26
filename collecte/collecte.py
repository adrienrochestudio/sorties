"""Collecte sans IA : open data "Que faire à Paris", flux des lieux de la base, événements à anticiper.

Tourne dans la GitHub Action. Sortie : data/brut/evenements.json (non versionné) et data/brut/rapport.json.
Stdlib uniquement.
"""
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from commun import (DATA, PARIS, arrondissement, aujourdhui, ecrire, lire, norm, parse_dt,
                    prix_euros, sans_html, tranche_prix)

UA = "sorties-collecte/1.0 (+https://github.com/adrienrochestudio/sorties)"
QFAP = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/que-faire-a-paris-/exports/json"
QFAP_CHAMPS = ("id,url,title,lead_text,date_start,date_end,occurrences,qfap_tags,address_name,"
               "address_street,address_zipcode,address_city,lat_lon,price_type,price_detail,"
               "access_link,access_type,audience")
rapport = {"sources": {}, "erreurs": []}


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def ident(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def evt(**k):
    """Fabrique un événement normalisé ; calcule tranche de prix et identifiant."""
    e = {"id": None, "titre": "", "resume": "", "debut": None, "fin": None, "lieu": "", "adresse": "",
         "arr": None, "ville": "Paris", "lat": None, "lon": None, "gratuit": False, "prix": None,
         "url": "", "resa": "", "tags": "", "source": "", "periode": False, "anticiper": False,
         "categorie": ""}
    e.update(k)
    e["tranche"] = tranche_prix(e["gratuit"], e["prix"])
    e["id"] = e["id"] or ident(e["source"], e["titre"], e["debut"], e["lieu"])
    return e


# ---------- Que faire à Paris ----------

def occurrences(valeur):
    sorties = []
    for bloc in str(valeur or "").split(";"):
        if "_" not in bloc:
            continue
        d, f = bloc.split("_", 1)
        dd, ff = parse_dt(d), parse_dt(f)
        if dd:
            sorties.append((dd, ff))
    return sorties


def qfap(depuis):
    params = {"where": f'date_end >= "{depuis.isoformat()}"', "select": QFAP_CHAMPS}
    try:
        brut = get(QFAP + "?" + urllib.parse.urlencode(params), timeout=180)
    except urllib.error.HTTPError as err:
        rapport["erreurs"].append(f"qfap select refusé ({err.code}), export complet")
        brut = get(QFAP + "?" + urllib.parse.urlencode({"where": params["where"]}), timeout=240)
    lignes = json.loads(brut)
    if lignes:
        rapport["qfap_champs"] = sorted(lignes[0].keys())
    sortie = []
    for r in lignes:
        aud = norm(r.get("audience"))
        if "enfant" in aud and "adulte" not in aud:
            continue
        geo = r.get("lat_lon") or {}
        gratuit = "gratuit" in norm(r.get("price_type")) and "condition" not in norm(r.get("price_type"))
        base = dict(
            titre=r.get("title") or "", resume=sans_html(r.get("lead_text"))[:300],
            lieu=r.get("address_name") or "", ville=r.get("address_city") or "Paris",
            adresse=f'{r.get("address_street") or ""}, {r.get("address_zipcode") or ""} {r.get("address_city") or ""}'.strip(", "),
            arr=arrondissement(r.get("address_zipcode"), r.get("address_city")),
            lat=geo.get("lat"), lon=geo.get("lon"), gratuit=gratuit,
            prix=prix_euros(r.get("price_detail")), url=r.get("url") or "",
            resa=r.get("access_link") or "", tags=r.get("qfap_tags") or "", source="qfap")
        occ = [o for o in occurrences(r.get("occurrences")) if o[0].date() >= depuis]
        if occ and len(occ) <= 20:
            for d, f in occ:
                sortie.append(evt(id=ident("qfap", r.get("id"), d.isoformat()), debut=d.isoformat(),
                                  fin=f.isoformat() if f else None, **base))
        else:
            d, f = parse_dt(r.get("date_start")), parse_dt(r.get("date_end"))
            if d:
                sortie.append(evt(id=ident("qfap", r.get("id")), debut=max(d.date(), depuis).isoformat(),
                                  fin=f.date().isoformat() if f else None, periode=True, **base))
    rapport["sources"]["qfap"] = len(sortie)
    return sortie


# ---------- Flux des lieux ----------

def ical(texte, lieu):
    texte = re.sub(r"\r?\n[ \t]", "", texte)
    evts = []
    for bloc in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", texte, re.S):
        champs = {}
        for ligne in bloc.strip().splitlines():
            if ":" in ligne:
                cle, val = ligne.split(":", 1)
                champs.setdefault(cle.split(";")[0].upper(), (cle, val.strip()))
        if "DTSTART" not in champs:
            continue
        cle, val = champs["DTSTART"]
        try:
            if "VALUE=DATE" in cle.upper() or len(val) == 8:
                debut = datetime.strptime(val[:8], "%Y%m%d").replace(tzinfo=PARIS)
            elif val.endswith("Z"):
                debut = datetime.strptime(val, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(PARIS)
            else:
                debut = datetime.strptime(val[:15], "%Y%m%dT%H%M%S").replace(tzinfo=PARIS)
        except ValueError:
            continue
        titre = champs.get("SUMMARY", ("", ""))[1].replace("\\,", ",").replace("\\;", ";")
        desc = champs.get("DESCRIPTION", ("", ""))[1].replace("\\n", " ").replace("\\,", ",")
        evts.append(evt(titre=titre, resume=desc[:300], debut=debut.isoformat(),
                        url=champs.get("URL", ("", ""))[1] or lieu.get("url_agenda", ""),
                        **depuis_lieu(lieu, "ical")))
    return evts


def jsonld(texte, lieu):
    evts = []
    for bloc in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', texte, re.S | re.I):
        try:
            data = json.loads(bloc.strip())
        except json.JSONDecodeError:
            continue
        pile = data if isinstance(data, list) else [data]
        while pile:
            n = pile.pop()
            if isinstance(n, list):
                pile.extend(n)
                continue
            if not isinstance(n, dict):
                continue
            pile.extend(v for k, v in n.items() if k in ("@graph", "itemListElement", "item", "subEvent"))
            types = n.get("@type")
            types = types if isinstance(types, list) else [types]
            if not any(t and "Event" in str(t) for t in types):
                continue
            d = parse_dt(n.get("startDate"))
            if not d:
                continue
            offre = n.get("offers") or {}
            offre = offre[0] if isinstance(offre, list) and offre else offre
            prix = None
            if isinstance(offre, dict):
                try:
                    prix = float(str(offre.get("price") or offre.get("lowPrice")).replace(",", "."))
                except ValueError:
                    prix = None
            evts.append(evt(titre=n.get("name") or "", resume=sans_html(n.get("description"))[:300],
                            debut=d.isoformat(), fin=(parse_dt(n.get("endDate")) or d).isoformat(),
                            url=n.get("url") or lieu.get("url_agenda", ""),
                            resa=(offre.get("url") if isinstance(offre, dict) else "") or "",
                            gratuit=prix == 0, prix=prix or None, **depuis_lieu(lieu, "jsonld")))
    return evts


def depuis_lieu(lieu, source):
    return dict(lieu=lieu.get("nom", ""), adresse=lieu.get("adresse", ""), arr=lieu.get("arrondissement"),
                ville=lieu.get("ville", "Paris"), lat=lieu.get("lat"), lon=lieu.get("lon"),
                tags=",".join(lieu.get("themes", [])), source=f"{source}:{lieu.get('id')}")


def flux_lieu(lieu):
    f = lieu.get("flux") or {}
    url = f.get("url") or (lieu.get("url_agenda") if f.get("type") == "jsonld" else None)
    if f.get("type") not in ("ical", "jsonld") or not url:
        return []
    try:
        texte = get(url)
        return ical(texte, lieu) if f["type"] == "ical" else jsonld(texte, lieu)
    except Exception as err:  # un lieu en panne ne bloque jamais la collecte
        rapport["erreurs"].append(f"{lieu.get('id')}: {type(err).__name__}")
        return []


def lieux():
    tous = []
    for fichier in sorted((DATA / "seed").glob("lieux_*.json")):
        tous.extend(lire(fichier, []))
    return tous


# ---------- Événements à anticiper ----------

def anticiper():
    sortie = []
    for a in lire(DATA / "seed" / "anticiper.json", []):
        heure = a.get("heure") or "20:00"
        d = parse_dt(f'{a.get("date_debut")}T{heure}:00') if a.get("date_debut") else None
        if not d:
            continue
        sortie.append(evt(id=ident("ant", a.get("id")), titre=a.get("nom", ""), resume=a.get("note", ""),
                          debut=d.isoformat(), fin=a.get("date_fin"), lieu=a.get("lieu", ""),
                          adresse=a.get("adresse", ""), ville=a.get("ville", "Paris"),
                          arr=arrondissement(a.get("adresse")), lat=a.get("lat"), lon=a.get("lon"),
                          prix=prix_euros(f'{a.get("prix")} €'), gratuit=norm(a.get("prix")) == "gratuit",
                          url=a.get("url", ""), tags=",".join(a.get("themes", [])), source="anticiper",
                          anticiper=True, categorie=a.get("categorie", ""),
                          periode=bool(a.get("date_fin") and a.get("date_fin") != a.get("date_debut"))))
        sortie[-1]["billetterie"] = a.get("ouverture_billetterie")
        sortie[-1]["train"] = a.get("train_depuis_paris")
    rapport["sources"]["anticiper"] = len(sortie)
    return sortie


def main():
    depuis = aujourdhui() + timedelta(days=1)
    tous = []
    try:
        tous += qfap(depuis)
    except Exception as err:
        rapport["erreurs"].append(f"qfap: {type(err).__name__}: {err}")
    base = lieux()
    with ThreadPoolExecutor(max_workers=8) as pool:
        for lot in pool.map(flux_lieu, base):
            tous += lot
    rapport["sources"]["flux_lieux"] = sum(1 for e in tous if ":" in e["source"])
    tous += anticiper()
    vus, uniques = set(), []
    for e in tous:
        cle = (norm(e["titre"])[:60], (e["debut"] or "")[:16], norm(e["lieu"])[:30])
        if cle not in vus:
            vus.add(cle)
            uniques.append(e)
    rapport["total"] = len(uniques)
    rapport["date"] = datetime.now(PARIS).isoformat(timespec="minutes")
    ecrire(DATA / "brut" / "evenements.json", uniques)
    ecrire(DATA / "brut" / "rapport.json", rapport, indent=1)
    print(json.dumps(rapport, ensure_ascii=False, indent=1)[:3000])
    if not uniques:
        sys.exit("Aucun événement collecté")


if __name__ == "__main__":
    main()

"""Outils de la tâche Claude du dimanche, pour ne jamais éditer les JSON à la main.

python3 collecte/maj.py voir                      shortlist en texte compact (une ligne par candidat)
python3 collecte/maj.py suggere crees.json        ajoute les événements créés à data/suggeres.json
python3 collecte/maj.py lecon "lieu" "theme"      une suppression constatée : baisse le poids du lieu et du thème
"""
import sys
from datetime import timedelta

from commun import DATA, aujourdhui, ecrire, lire, norm, parse_dt


def voir():
    s = lire(DATA / "shortlist.json")
    print(f"shortlist du {s['genere']}")
    for b in s["buckets"]:
        print(f"\n## S{b['semaine']} {b['debut']} > {b['fin']} | cible {b['cible']} | {b['mode']}")
        for c in b["candidats"]:
            extra = " ".join(x for x in [
                "DECOUVERTE" if c.get("dec") else "", "PERIODE" if c.get("pe") else "",
                "DIM-SOIR" if c.get("dim_soir") else "",
                f"ANTICIPER(billetterie {c['ant']})" if c.get("ant") not in (None, 1) else ("ANTICIPER" if c.get("ant") else ""),
                f"train {c['train']}" if c.get("train") else ""] if x)
            print(f"- [{c['id']}] {c['d']} | {c['t']} | {c['l']} | {c['p']} | {'/'.join(c['th'])} | sc {c['sc']} {extra}".rstrip())
            print(f"  {c['u']}" + (f" | resa {c['r']}" if c.get("r") else ""))


def suggere(chemin):
    nouveaux = lire(chemin, [])
    limite = aujourdhui() - timedelta(days=30)
    garde = [s for s in lire(DATA / "suggeres.json", []) if (parse_dt(s.get("d")) or parse_dt("2100-01-01")).date() >= limite]
    ids = {s["id"] for s in garde}
    for n in nouveaux:
        if n.get("id") not in ids:
            garde.append({k: n.get(k) for k in ("id", "t", "d", "l", "lat", "lon", "p", "th", "u")})
    ecrire(DATA / "suggeres.json", garde, indent=0)
    print(f"{len(garde)} suggestions suivies")


def lecon(lieu, theme):
    p = lire(DATA / "poids.json", {"lieux": {}, "themes": {}, "mots": {}})
    if lieu:
        k = norm(lieu)[:40]
        p["lieux"][k] = max(-10, p["lieux"].get(k, 0) - 2)
    if theme:
        p["themes"][theme] = max(-6, p["themes"].get(theme, 0) - 1)
    ecrire(DATA / "poids.json", p, indent=1)
    print(p)


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["voir"]
    {"voir": voir, "suggere": suggere, "lecon": lecon}[cmd](*args)

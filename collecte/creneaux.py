"""Répartition dans le temps : dense à court terme, puis de plus en plus espacée.

0-3 semaines : 4 à 6 sorties par semaine (cible 5)
4-7 semaines : 1 par semaine
2 mois : 1 toutes les 2 semaines ; 3 mois : 1 toutes les 3 semaines ; au-delà : 1 par mois
Au-delà de 7 semaines, seulement des événements à anticiper (billetterie qui part vite ou hors Paris).
"""
from datetime import timedelta


def intervalle(semaine):
    if semaine < 3:
        return 1
    if semaine < 7:
        return 1
    return min(4, max(2, round(semaine / 4)))


def buckets(demain, horizon_semaines=26):
    sortie, w = [], 0
    while w < horizon_semaines:
        pas = intervalle(w)
        debut = demain + timedelta(days=7 * w)
        fin = demain + timedelta(days=7 * (w + pas) - 1)
        if w < 3:
            cible, mode = 5, "proche"
        elif w < 7:
            cible, mode = 1, "moyen"
        else:
            cible, mode = 1, "anticiper"
        sortie.append({"semaine": w + 1, "debut": debut.isoformat(), "fin": fin.isoformat(),
                       "cible": cible, "mode": mode})
        w += pas
    return sortie


if __name__ == "__main__":
    from commun import aujourdhui
    for b in buckets(aujourdhui() + timedelta(days=1)):
        print(b)

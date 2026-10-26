# sorties

Suggestions de sorties à Paris pour l'agenda d'Adrien, avec le moins d'IA possible.

- `data/seed/` : base de lieux et d'événements à anticiper, mise à jour une fois par mois.
- `collecte/collecte.py` : collecte sans IA (open data "Que faire à Paris", flux iCal et JSON-LD des lieux, base à anticiper).
- `collecte/creneaux.py` : répartition dans le temps, dense à 3 semaines puis espacée jusqu'à 6 mois.
- `collecte/filtrer.py` : filtres durs, score, diversité ; écrit `data/shortlist.json` et `site/carte.json`.
- `collecte/maj.py` : outils de la tâche Claude du dimanche (lecture compacte, leçons, suggestions créées).
- `config/` : règles et goûts, modifiables à la main.
- `consignes/hebdo.md` : ce que fait la tâche Claude du dimanche.
- `site/` : la carte, publiée sur GitHub Pages.

Cycle : samedi soir, l'Action collecte et publie la shortlist ; dimanche matin, Claude choisit, vérifie et crée les événements, puis pousse `data/suggeres.json` et `data/poids.json`, ce qui relance la carte.

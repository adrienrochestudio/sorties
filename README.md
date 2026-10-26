# sorties

Suggestions de sorties à Paris pour l'agenda d'Adrien, avec le moins d'IA possible.

- `data/seed/` : base de lieux et d'événements à anticiper, mise à jour une fois par mois.
- `collecte/collecte.py` : collecte sans IA (open data "Que faire à Paris", flux iCal et JSON-LD des lieux, base à anticiper).
- `collecte/creneaux.py` : répartition dans le temps, dense à 3 semaines puis espacée jusqu'à 6 mois.
- `collecte/filtrer.py` : filtres durs, score, diversité ; écrit `data/shortlist.json`.
- `collecte/maj.py` : outils de la tâche Claude du dimanche (lecture compacte, leçons, suggestions créées).
- `config/` : règles et goûts, modifiables à la main.
- `consignes/hebdo.md` : ce que fait la tâche Claude du dimanche.

Cycle : samedi soir, l'Action collecte et publie la shortlist ; dimanche matin, Claude choisit, vérifie et crée les événements ; ensuite l'Action relit l'agenda et apprend des suppressions.

## Exploitation

- Tâche planifiée "Agenda sorties Paris" (dimanche 9h56, Sonnet) : lit `consignes/hebdo.md`, crée les sorties dans l'agenda, ne modifie rien dans le dépôt.
- Action GitHub : samedi 23h17 (collecte), dimanche 10h37 et chaque matin de semaine (relecture de l'agenda, leçons).
- Secret GitHub `AGENDA_ICS` : adresse iCal secrète de l'agenda adrienrochestudio. Sans lui, pas de relecture d'agenda.
- Fichier Drive "Agenda sorties - profils" : profils d'amis pour le quota 10 à 20 %.
- Pour reprendre le projet dans une nouvelle conversation : "projet sorties, dépôt adrienrochestudio/sorties".

## Historique

- 26/10/2026 : refonte (base de données, courbe sur 6 mois, carte, relecture d'agenda). Agenda remis à zéro, `data/suggeres.json` vidé.
- 26/10/2026 : carte supprimée à la demande d'Adrien ; `data/suggeres.json` réduit à id, date, lieu, thème.

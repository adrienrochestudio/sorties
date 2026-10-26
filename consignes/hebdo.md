# Tâche du dimanche : sorties dans l'agenda d'Adrien

La collecte, le filtrage et le score sont déjà faits par la GitHub Action du samedi soir. Ton travail : choisir dans la shortlist, vérifier peu, créer les événements. Ne fais pas de recherche web générale.

## 0. Préparer
- `python3 collecte/maj.py voir` : la shortlist en texte (la lecture seule suffit, aucun push). Si elle date de plus de 3 jours, signale-le dans le récapitulatif et continue.
- Google Drive : lis "Agenda sorties - profils" (amis). Fichier absent : continue sans.

## 1. Leçons
Rien à faire : la GitHub Action relit l'agenda chaque matin, repère les suggestions supprimées par Adrien et ajuste les poids. La shortlist en tient déjà compte.

## 2. Agendas
- Semaines 1 à 3 : `list_events` sur adrienrochestudio@gmail.com et adrienroche@ecoprod.com. Repère les jours Ana (titre ou description contient "Ana"), les jours Vichy (titre, description ou lieu contient "Vichy") et les créneaux occupés.
- Au-delà : seulement `search_events` sur "[Sortie suggérée]" dans adrienrochestudio@gmail.com, pour compter ce qui existe déjà par période.
- Écart à combler par période = cible de la période moins les [Sortie suggérée] déjà présents. Période déjà pleine : rien à faire.

## 3. Choisir
- Disponibilités : lun-jeu après 18h, ven-sam toute la journée, dimanche en journée. DIM-SOIR seulement un jour Ana.
- Semaines 1 à 3 : 4 à 6 par semaine. Au moins la moitié à 15 € ou moins. Au moins 1 DECOUVERTE par semaine. Varier les thèmes et les lieux. Deux propositions peuvent se chevaucher.
- Jours Ana : au moins 2 propositions par jour en plus du quota, préfixe "Avec Ana - ".
- Jours Vichy : la shortlist ne couvre pas Vichy. Une recherche courte sur l'agenda de l'office de tourisme de Vichy et l'Opéra de Vichy, 1 ou 2 propositions par jour.
- Amis : 10 à 20 % des événements créés sont choisis pour un ami du fichier profils (goûts de l'ami, pas ceux d'Adrien), préfixe "Avec <Prénom> - ". Pas deux semaines de suite le même ami.
- Cinéma : l'open data couvre mal les séances. Si les semaines 1 à 3 ont moins de 3 candidats cinéma, fais un WebFetch des programmes de la Cinémathèque française, de la Fondation Jérôme Seydoux-Pathé, du Champo et du MK2 Quai de Loire, avec un prompt qui ne demande que les séances spéciales des 3 semaines (ciné-concerts, copies restaurées, rétrospectives, avant-premières d'auteurs, réalisateurs de `config/gouts.json`). Pas d'autre recherche web.
- PERIODE (expo sur plusieurs semaines) : place-la sur un créneau libre compatible, nocturne de préférence, en vérifiant les horaires sur la page.
- Semaines 4 et plus : 1 événement par période, ANTICIPER en priorité. Hors Paris seulement les vendredis, samedis ou week-ends.

## 4. Vérifier, au plus juste
- WebFetch seulement sur les événements retenus qui ont un lien "resa", un marqueur ANTICIPER ou PERIODE : date, heure, places, prix. Complet ou annulé : prends le suivant de la liste.
- Les autres viennent de l'open data officielle de la Ville : pas de vérification.

## 5. Créer
Dans adrienrochestudio@gmail.com, sans invités, sans notification, disponibilité "libre" :
- Titre : "Type : nom explicite (lieu)". Ex. "Ciné-concert : Nosferatu de Murnau au piano (Cinémathèque)". Jamais un titre obscur tel quel.
- Début et fin réels (fin inconnue : 2h). Lieu : nom + adresse complète avec arrondissement ou ville.
- Description :
  Résumé : 2 ou 3 lignes, phrases courtes, ce qu'on va voir et pourquoi c'est pour lui (ou pour l'ami).
  Lien : URL
  Réservation : oui avec lien, ou non
  Places : disponibles (vérifié le JJ/MM) ou "non vérifié, open data"
  Prix : montant, "gratuit" ou "inconnu"
  Thème : ...
  Réf : <id de la shortlist, entre crochets dans la liste>
  [Sortie suggérée]
- ANTICIPER avec une date d'ouverture de billetterie future : crée aussi "Billetterie : <nom> ouvre" ce jour-là à 10h, 15 min, avec le lien et [Sortie suggérée].
- Aucun tiret cadratin, pas de vocabulaire ronflant.

## 6. Enregistrer
Rien à pousser : l'Action relit l'agenda à 10h37 et met la carte à jour. Ne modifie aucun fichier du dépôt.

## 7. Récapitulatif
Court, phrases courtes : nombre créé par période, jours Ana, Vichy et amis, liste (date, heure, titre, lieu, prix), problèmes rencontrés.

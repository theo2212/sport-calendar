# 🏟️ Mes sports — calendrier auto

Un calendrier unique avec tous les matchs de mes équipes et joueurs, mis à jour **toutes les 2 h**
(horaires décalés, reports, résultats).

## S'abonner sur iPhone
Réglages → Calendrier → Comptes → Ajouter un compte → Autre → **Ajouter un calendrier avec abonnement**, puis colle :

- **Tout** : `https://raw.githubusercontent.com/theo2212/sport-calendar/main/docs/calendar.ics`
- **Ou un calendrier par sport** (une couleur par sport) : remplace `calendar.ics` par
  `sport-foot.ics`, `sport-basket.ics`, `sport-rugby.ics`, `sport-hand.ics`, `sport-flechettes.ics`,
  `sport-esport.ics`, `sport-biathlon.ics`, `sport-f1.ics`.

## Ajouter / retirer une équipe
Modifie `config.yaml` (même depuis l'app GitHub). Le calendrier se régénère tout seul dans les ~2 minutes.

## Sources
ESPN (foot, basket, rugby) · Sofascore (hand, fléchettes, esport, autres) · IBU (biathlon) · Jolpica (F1).
L'état de chaque source est visible dans `docs/status.json`.

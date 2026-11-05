# Dashboard Power BI — guide de construction

Objectif : un rapport de 3 pages qui répond à la question « les passoires thermiques se vendent-elles moins cher ? »,
avec des chiffres fiables et une page dédiée à la qualité des données.

Maquette de la page principale (construite avec les vraies données) : [`powerbi/maquette_page1.png`](../powerbi/maquette_page1.png)

## 1. Préparer

1. Installer **Power BI Desktop** (gratuit, Microsoft Store).
2. Lancer le pipeline pour produire la couche gold : `cd transform` puis `dbt build`.
   Les fichiers sont dans `data/gold/` : `fait_ventes`, `dim_dpe`, `dim_commune`, `dim_temps`, `suivi_rapprochement`.

## 2. Charger les données

Pour chacun des 5 fichiers : **Accueil → Obtenir les données → Plus… → Parquet**, puis coller le chemin complet du
fichier, par exemple `C:\Users\…\observatoire-valeur-verte\data\gold\fait_ventes.parquet`, puis **Charger**.

> Si le connecteur Parquet refuse le chemin local : **Obtenir les données → Dossier**, choisir `data\gold`,
> puis **Combiner** fichier par fichier.

## 3. Le modèle (vue Modèle)

**Relations** (toutes de type *plusieurs à un*, filtrage dans un seul sens, de la dimension vers le fait) :

| De (fait) | Vers (dimension) |
| --- | --- |
| `fait_ventes[date_vente]` | `dim_temps[date]` |
| `fait_ventes[code_commune]` | `dim_commune[code_commune]` |
| `fait_ventes[etiquette_dpe]` | `dim_dpe[etiquette_dpe]` |
| `suivi_rapprochement[code_commune]` | `dim_commune[code_commune]` |

**Réglages :**
- `dim_temps` : clic droit → **Marquer comme table de dates** (colonne `date`).
- `dim_dpe[etiquette_dpe]` : **Outils de colonne → Trier par colonne → `ordre`** (pour avoir A, B, C… et non un tri alphabétique hasardeux).
- Masquer les colonnes techniques dans la vue rapport (`numero_dpe`, `longitude`/`latitude` hors carte, etc.).
- **Affichage → Thèmes → Parcourir les thèmes** → `powerbi/theme_dpe.json` : les classes A à G prennent automatiquement les couleurs officielles du DPE.

**Colonnes calculées** (Modélisation → Nouvelle colonne) :

```dax
Groupe DPE = SWITCH(TRUE(), dim_dpe[ordre] <= 3, "A-C", dim_dpe[ordre] <= 5, "D-E", "F-G")
```
```dax
Zone = IF(dim_commune[est_lyon], "Lyon", "Reste du Rhône")
```

## 4. Les mesures DAX

Créer une table vide **Mesures** (Accueil → Entrer des données → nommer la table « Mesures »), puis ajouter :

```dax
Ventes totales = COUNTROWS(fait_ventes)

Ventes analysées = CALCULATE(COUNTROWS(fait_ventes), fait_ventes[inclus_analyse] = TRUE())

Prix m² médian = CALCULATE(MEDIAN(fait_ventes[prix_m2]), fait_ventes[inclus_analyse] = TRUE())

Prix m² médian A-C = CALCULATE([Prix m² médian], dim_dpe[etiquette_dpe] IN {"A", "B", "C"})

Prix m² médian F-G = CALCULATE([Prix m² médian], dim_dpe[est_passoire] = TRUE())

Décote F-G vs A-C = DIVIDE([Prix m² médian F-G] - [Prix m² médian A-C], [Prix m² médian A-C])

Part de passoires = DIVIDE(CALCULATE([Ventes analysées], dim_dpe[est_passoire] = TRUE()), [Ventes analysées])

Taux de rapprochement = DIVIDE(CALCULATE(COUNTROWS(fait_ventes), fait_ventes[est_rapprochee] = TRUE()), [Ventes totales])

-- Décote affichée seulement si chaque groupe compte au moins 30 ventes (sinon le chiffre n'est pas fiable)
Décote fiable =
VAR nAC = CALCULATE([Ventes analysées], dim_dpe[etiquette_dpe] IN {"A", "B", "C"})
VAR nFG = CALCULATE([Ventes analysées], dim_dpe[est_passoire] = TRUE())
RETURN IF(nAC >= 30 && nFG >= 30, [Décote F-G vs A-C])
```

> Si Power BI signale une erreur de syntaxe, c'est le séparateur régional : remplacer les `,` entre arguments
> par des `;` (ou choisir **Fichier → Options → Paramètres régionaux → séparateurs DAX recommandés**).

Formats : `Décote…`, `Part…`, `Taux…` en **pourcentage, 1 décimale** ; `Prix…` en **nombre entier** avec le suffixe « €/m² ».

## 5. Les pages

### Page 1 — Vue d'ensemble (voir la maquette)

| Zone | Visuel | Contenu |
| --- | --- | --- |
| En haut à droite | 3 segments (slicers) | `fait_ventes[type_logement]`, `dim_temps[annee]`, `dim_commune[Zone]` |
| Bandeau | 4 cartes | Ventes analysées · Prix m² médian · Décote F-G vs A-C · Part de passoires |
| Bas gauche | Histogramme groupé | Axe : `dim_dpe[etiquette_dpe]` · Valeur : Prix m² médian · étiquettes de données activées · couleur par étiquette |
| Bas droite | Graphique en courbes | Axe : `dim_temps[annee]` · Valeur : Prix m² médian · Légende : `dim_dpe[Groupe DPE]` |
| Pied de page | Zone de texte | « Écarts bruts, non corrigés de la surface ni de la localisation. » |

Couleurs des courbes : A-C `#55AB26`, D-E `#E0A800`, F-G `#E2001A`. Carte « Décote » en rouge (`#B91C1C`).

### Page 2 — Territoires

| Visuel | Contenu |
| --- | --- |
| Carte (Azure Maps ou carte classique) | Latitude / longitude de `fait_ventes`, couleur = `etiquette_dpe`, filtre visuel `inclus_analyse = Vrai` |
| Tableau | `dim_commune[libelle]`, Ventes analysées, Prix m² médian A-C, Prix m² médian F-G, Décote fiable — trié par Ventes analysées |
| Histogramme groupé | Axe : `dim_commune[Zone]` · Légende : `fait_ventes[type_logement]` · Valeur : Décote F-G vs A-C |

Message clé de la page : **la décote est plus de deux fois plus forte hors de Lyon pour les appartements** (−27,5 % contre −11,2 %).

### Page 3 — Qualité des données

| Visuel | Contenu |
| --- | --- |
| Entonnoir | Lignes DVF ingérées (354 101, texte) → Ventes totales → ventes rapprochées → Ventes analysées |
| Courbes | Axe : `suivi_rapprochement[annee_vente]` · Valeur : moyenne pondérée du taux (ou mesure Taux de rapprochement) · Légende : type de logement |
| Anneau | `fait_ventes[methode_rapprochement]` (clé BAN / adresse normalisée) |
| Zone de texte | Méthode en 3 lignes : clé d'adresse exacte, contrôles surface ±10 % et date, exclusion des cas ambigus |

Cette page montre au recruteur que les chiffres sont **mesurés et contrôlés**, pas seulement affichés.

## 6. Vérifier : les chiffres attendus

Sans filtre (Rhône, 2022-2025, tous logements) :

| Mesure | Valeur attendue |
| --- | --- |
| Ventes totales | 85 431 |
| Ventes analysées | 30 217 |
| Taux de rapprochement | 62,2 % |
| Prix m² médian | 4 000 |
| Prix m² médian A-C | 4 228 |
| Prix m² médian F-G | 3 581 |
| Décote F-G vs A-C | −15,3 % |
| Part de passoires | 7,4 % |

Avec filtres :

| Filtre | Décote F-G vs A-C |
| --- | --- |
| Appartements | −15,3 % (4 306 → 3 648) |
| Maisons | −11,7 % (3 952 → 3 489) |
| Appartements, Lyon | −11,2 % (5 032 → 4 470) |
| Appartements, reste du Rhône | −27,5 % (3 819 → 2 769) |
| Année 2022 | −14,6 % |
| Année 2025 | −17,7 % |

Si un chiffre diffère, vérifier en priorité : les relations (sens du filtrage), le filtre `inclus_analyse`, et le tri de `etiquette_dpe`.

## 7. Publier dans le portfolio

1. Enregistrer le rapport sous `powerbi/observatoire_valeur_verte.pbix`.
2. Exporter chaque page en image (**Fichier → Exporter → PDF**, puis capture) et les ajouter dans `powerbi/`.
3. Afficher la capture de la page 1 en haut du README.

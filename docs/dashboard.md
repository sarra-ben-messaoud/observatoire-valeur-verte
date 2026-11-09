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

La page 1 est dupliquée (titre, segments synchronisés, cartes), puis on remplace les deux graphiques du bas.

| Visuel | Champs | X | Largeur |
| --- | --- | --- | --- |
| Barres horizontales triées | Axe Y : `dim_commune[libelle]` · Axe X : `Décote fiable` · filtre : Décote fiable n'est pas vide · tri croissant · couleur fx dégradé rouge `E2001A` → jaune `FBBA00` | 30 | 700 |
| Tableau | Commune, Ventes, Prix A-C, Prix F-G, Décote (mêmes 20 communes), sans ligne de total | 750 | 640 |
| Barres groupées horizontales | Axe Y : `dim_commune[Zone]` · Légende : `type_logement` (bleu `3B6FB6`, gris `6B7280`) · Axe X : `Décote fiable` | 1410 | 480 |

Tous à Y = 350, hauteur 650.

**Pourquoi un classement plutôt qu'une carte :** sans fond de carte (Azure Maps exige un compte professionnel),
une carte en bulles ne permet pas de reconnaître les communes, et les 20 communes fiables se chevauchent autour de
Lyon. La question posée — « quelles communes ont la plus forte décote ? » — se lit mieux dans un classement.

**Point d'attention : l'effet de composition.** À Meyzieu, la décote est positive (+5,2 %) parce que 90 % des
passoires vendues y sont des maisons, contre 31 % des logements A-C : on compare des biens différents.
C'est la raison d'être de l'analyse « toutes choses égales par ailleurs » (étape 7).

### Page 3 — Qualité des données

Mesures supplémentaires :

```dax
Ventes rapprochées = CALCULATE(COUNTROWS(fait_ventes), fait_ventes[est_rapprochee] = TRUE())
Rapprochements fiables = CALCULATE(COUNTROWS(fait_ventes), fait_ventes[est_rapprochement_fiable] = TRUE())
Part analysée = DIVIDE([Ventes analysées], [Ventes totales])
Part clé exacte = DIVIDE(CALCULATE([Ventes rapprochées], fait_ventes[methode_rapprochement] = "cle_ban"), [Ventes rapprochées])
Ventes par étape = SWITCH(SELECTEDVALUE('Étapes'[Ordre]), 1, [Ventes totales], 2, [Ventes rapprochées], 3, [Rapprochements fiables], 4, [Ventes analysées])
```

Table des étapes de l'entonnoir (Modélisation → Nouvelle table), triée par `Ordre` :

```dax
Étapes = DATATABLE("Étape", STRING, "Ordre", INTEGER, {
    {"Ventes (1 logement)", 1}, {"Rapprochées", 2}, {"Rapprochement fiable", 3}, {"Analysées", 4}
})
```

Colonne calculée dans `fait_ventes` (libellés lisibles) :

```dax
Méthode = SWITCH(fait_ventes[methode_rapprochement], "cle_ban", "Clé d'adresse exacte", "adresse_normalisee", "Adresse normalisée")
```

> Un nom de table accentué s'écrit entre apostrophes en DAX : `'Étapes'[Ordre]`.

| Visuel | Champs |
| --- | --- |
| 4 cartes | Ventes totales · Taux de rapprochement · Part analysée · Part clé exacte |
| Entonnoir | Catégorie : `Étapes[Étape]` · Valeurs : `Ventes par étape` |
| Courbes | Axe X : `dim_temps[annee]` · Axe Y : `Taux de rapprochement` (0 à 100 %) · Légende : `type_logement` |
| Anneau | Légende : `fait_ventes[Méthode]` · Valeurs : `Ventes rapprochées` |

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
| Maisons, Lyon | −11,7 % (5 664 → 5 000) |
| Maisons, reste du Rhône | −12,7 % (3 929 → 3 429) |
| Année 2022 | −14,6 % |
| Année 2025 | −17,7 % |

Page 2, tableau des communes (les plus grosses) :

| Commune | Ventes analysées | A-C | F-G | Décote |
| --- | --- | --- | --- | --- |
| Villeurbanne | 3 047 | 4 117 | 3 410 | −17,2 % |
| Lyon 3e | 2 474 | 5 051 | 4 442 | −12,1 % |
| Lyon 7e | 1 943 | 5 054 | 4 369 | −13,6 % |
| Villefranche-sur-Saône | 906 | 2 921 | 2 112 | −27,7 % |
| Meyzieu | 585 | 3 709 | 3 901 | +5,2 % |

Page 3 :

| Mesure | Valeur attendue |
| --- | --- |
| Entonnoir | 85 431 → 53 109 → 30 283 → 30 217 |
| Taux de rapprochement, appartements | 57,4 % (2022) → 82,1 % (2025) |
| Taux de rapprochement, maisons | 24,7 % (2022) → 40,4 % (2025) |
| Part clé exacte | 97,1 % (51 567 sur 53 109) |

Si un chiffre diffère, vérifier en priorité : les relations (sens du filtrage), le filtre `inclus_analyse`, et le tri de `etiquette_dpe`.

## 7. Publier dans le portfolio

1. Enregistrer le rapport sous `powerbi/observatoire_valeur_verte.pbix`.
2. Faire une capture de chaque page (`powerbi/dashboard_page1.png`, `…page2.png`, `…page3.png`).
3. Les captures s'affichent dans le README (section « Dashboard »).

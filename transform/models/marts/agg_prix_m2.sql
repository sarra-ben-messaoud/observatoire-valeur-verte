-- Prix au m² par commune, type de logement, année et classe DPE (périmètre d'analyse uniquement).
-- Pré-calculé ici car les médianes sont coûteuses à calculer dans Power BI.
-- Les cellules de moins de 10 ventes sont masquées (statistique non fiable, et confidentialité des données DVF).
select
    code_commune,
    type_logement,
    annee_vente,
    etiquette_dpe,
    count(*)                                    as nb_ventes,
    median(prix_m2)                             as prix_m2_median,
    quantile_cont(prix_m2, 0.25)                as prix_m2_q1,
    quantile_cont(prix_m2, 0.75)                as prix_m2_q3,
    median(surface)                             as surface_mediane
from {{ ref('fait_ventes') }}
where inclus_analyse
group by all
having count(*) >= 10

-- Suivi de la qualité du rapprochement DVF ↔ DPE, par commune, année et type de logement.
select
    code_commune,
    annee_vente,
    type_logement,
    count(*)                                                    as nb_ventes,
    count(*) filter (where est_rapprochee)                      as nb_rapprochees,
    count(*) filter (where est_rapprochement_fiable)            as nb_fiables,
    round(count(*) filter (where est_rapprochee) / count(*), 3) as taux_rapprochement,
    round(count(*) filter (where est_rapprochement_fiable) / count(*), 3) as taux_fiable
from {{ ref('fait_ventes') }}
group by all

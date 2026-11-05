-- Communes du périmètre. Lyon est découpée en 9 arrondissements (codes 69381 à 69389).
select
    code_commune,
    any_value(nom_commune)                                         as nom_commune,
    left(code_commune, 2)                                          as code_departement,
    case when code_commune between '69381' and '69389'
         then 'Lyon ' || right(code_commune, 1) || case right(code_commune, 1) when '1' then 'er' else 'e' end
         else any_value(nom_commune) end                          as libelle,
    code_commune between '69381' and '69389'                       as est_lyon,
    count(*)                                                       as nb_ventes_total
from {{ ref('int_dvf__ventes_logement') }}
group by code_commune

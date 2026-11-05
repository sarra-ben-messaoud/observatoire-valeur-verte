-- Table de faits : une ligne par vente d'un seul logement, avec le DPE rapproché quand il existe.
-- inclus_analyse = vente plausible + rapprochement fiable : c'est le périmètre des indicateurs de valeur verte.
select
    v.id_vente,
    v.date_vente,
    v.annee_vente,
    v.code_commune,
    v.type_logement,
    v.prix,
    v.surface,
    v.nb_pieces,
    v.prix_m2,
    v.avec_dependance,
    v.longitude,
    v.latitude,
    d.etiquette_dpe,
    d.etiquette_ges,
    d.conso_ep_m2,
    d.annee_construction,
    d.periode_construction,
    d.type_energie_principale_chauffage,
    d.issu_dpe_immeuble,
    r.numero_dpe,
    r.methode                                    as methode_rapprochement,
    r.ecart_surface,
    r.anciennete_dpe_jours,
    v.est_plausible,
    r.id_vente is not null                       as est_rapprochee,
    coalesce(r.est_fiable, false)                as est_rapprochement_fiable,
    v.est_plausible and coalesce(r.est_fiable, false) as inclus_analyse
from {{ ref('int_dvf__ventes_logement') }} v
left join {{ ref('int_rapprochement__ventes_dpe') }} r using (id_vente)
left join {{ ref('int_dpe__logements') }} d using (numero_dpe)

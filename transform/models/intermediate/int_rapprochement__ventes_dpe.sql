-- Rapprochement ventes DVF ↔ DPE : une ligne par vente rapprochée.
--
-- Cascade de méthodes (on garde pour chaque vente la méthode la plus fiable) :
--   1. « cle_ban »            : clé d'adresse exacte commune_voie_numéro[_suffixe] ;
--   2. « adresse_normalisee » : même commune, même numéro, nom de voie normalisé identique ou très proche.
-- Contraintes communes : même type de logement, surface à ±10 %, DPE établi avant la vente (3 ans max).
-- Choix final : surface la plus proche, puis DPE le plus récent avant la vente.

{% set tolerance_surface = 0.10 %}
{% set fenetre_mois = 36 %}

with ventes as (
    select * from {{ ref('int_dvf__ventes_logement') }}
),
dpe as (
    select * from {{ ref('int_dpe__logements') }}
),

-- deux jointures d'égalité séparées (bis/lettre) plutôt qu'un « OU » : DuckDB peut alors utiliser
-- une jointure par hachage au lieu de comparer chaque vente à chaque DPE
candidats_cle as (
    select distinct id_vente, numero_dpe, 1 as priorite, 'cle_ban' as methode from (
        select v.id_vente, d.numero_dpe
        from ventes v join dpe d on d.cle_adresse = v.cle_adresse and d.type_logement = v.type_logement
        union all
        select v.id_vente, d.numero_dpe
        from ventes v join dpe d on d.cle_adresse = v.cle_adresse_alt and d.type_logement = v.type_logement
        where v.cle_adresse_alt <> v.cle_adresse
    )
),

candidats_adresse as (
    select v.id_vente, d.numero_dpe, 2 as priorite, 'adresse_normalisee' as methode
    from ventes v
    join dpe d on d.code_commune = v.code_commune
             and d.numero_norm = v.numero_norm
             and d.type_logement = v.type_logement
             and (d.voie_norm = v.voie_norm or jaro_winkler_similarity(d.voie_norm, v.voie_norm) >= 0.92)
    where v.voie_norm <> ''
      and v.id_vente not in (select id_vente from candidats_cle)
),

candidats as (
    select c.*,
        v.date_vente, v.surface,
        d.date_dpe, d.surface_habitable, d.etiquette_dpe,
        abs(d.surface_habitable - v.surface) / v.surface   as ecart_surface,
        date_diff('day', d.date_dpe, v.date_vente)         as anciennete_dpe_jours
    from (select * from candidats_cle union all select * from candidats_adresse) c
    join ventes v using (id_vente)
    join dpe d using (numero_dpe)
    where abs(d.surface_habitable - v.surface) / v.surface <= {{ tolerance_surface }}
      and d.date_dpe <= v.date_vente
      and d.date_dpe >= v.date_vente - interval {{ fenetre_mois }} month
),

classes as (
    select *,
        row_number() over (partition by id_vente order by priorite, ecart_surface, anciennete_dpe_jours) as rang,
        count(*) over (partition by id_vente) as nb_candidats
    from candidats
),

meilleurs as (
    select * from classes where rang = 1
),

-- ambiguïté : un autre candidat de même méthode, presque aussi proche en surface (±2 points),
-- porte une étiquette différente → on ne sait pas laquelle est la bonne
ambiguites as (
    select m.id_vente, bool_or(c.etiquette_dpe <> m.etiquette_dpe) as etiquette_ambigue
    from meilleurs m
    join classes c on c.id_vente = m.id_vente and c.priorite = m.priorite and c.rang > 1
                  and c.ecart_surface <= m.ecart_surface + 0.02
    group by m.id_vente
)

select
    m.id_vente,
    m.numero_dpe,
    m.methode,
    round(m.ecart_surface, 3)                                  as ecart_surface,
    m.anciennete_dpe_jours,
    m.nb_candidats,
    coalesce(a.etiquette_ambigue, false)                       as etiquette_ambigue,
    -- un même DPE retenu pour plusieurs ventes : logements voisins de même taille dans un immeuble
    count(*) over (partition by m.numero_dpe) > 1              as dpe_partage,
    not coalesce(a.etiquette_ambigue, false)
        and count(*) over (partition by m.numero_dpe) = 1      as est_fiable
from meilleurs m
left join ambiguites a using (id_vente)

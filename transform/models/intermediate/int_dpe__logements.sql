-- DPE de logements utilisables pour le rapprochement.
--  - on écarte les DPE d'immeuble entier (pas d'étiquette par logement) ;
--  - on écarte les DPE remplacés par un DPE plus récent ;
--  - clé d'adresse = identifiant BAN, seulement s'il descend jusqu'au numéro (commune_voie_numéro[_suffixe]).
with dpe as (
    select * from {{ ref('stg_dpe__diagnostics') }}
),
remplaces as (
    select distinct numero_dpe_remplace as numero_dpe from dpe where numero_dpe_remplace is not null
)
select
    d.numero_dpe,
    d.date_dpe,
    d.etiquette_dpe,
    d.etiquette_ges,
    d.conso_ep_m2,
    d.ges_m2,
    d.cout_energie_annuel,
    case d.type_batiment when 'appartement' then 'Appartement' when 'maison' then 'Maison' end as type_logement,
    d.surface_habitable,
    d.annee_construction,
    d.periode_construction,
    d.type_energie_principale_chauffage,
    d.methode_application_dpe like '%généré à partir des données DPE immeuble%' as issu_dpe_immeuble,
    case when len(string_split(d.identifiant_ban, '_')) in (3, 4) then lower(d.identifiant_ban) end as cle_adresse,
    d.code_insee_ban                                as code_commune,
    {{ normaliser_numero('d.numero_voie_ban') }}    as numero_norm,
    {{ normaliser_voie('d.nom_rue_ban') }}          as voie_norm,
    d.latitude,
    d.longitude
from dpe d
where d.type_batiment in ('appartement', 'maison')
  and d.etiquette_dpe in ('A', 'B', 'C', 'D', 'E', 'F', 'G')
  and d.date_dpe is not null
  and d.numero_dpe not in (select numero_dpe from remplaces)

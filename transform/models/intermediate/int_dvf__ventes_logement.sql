-- Une ligne par vente d'un seul logement (appartement ou maison), prix et adresse normalisés.
--
-- Règles :
--  - nature « Vente » uniquement (on écarte VEFA/neuf, échanges, adjudications, expropriations) ;
--  - exactement un logement dans la vente, aucun local d'activité ; les dépendances (cave, parking) sont admises ;
--  - un seul montant pour toute la vente (sinon le prix du logement n'est pas isolable).

with lignes as (
    select * from {{ ref('stg_dvf__lignes') }}
    where nature_mutation = 'Vente'
),

composition as (
    select
        id_mutation,
        count(distinct case when type_local in ('Appartement', 'Maison')
              then concat_ws('|', id_parcelle, lot1_numero, type_local, surface_reelle_bati) end) as nb_logements,
        count(*) filter (where type_local = 'Local industriel. commercial ou assimilé')        as nb_locaux_activite,
        count(*) filter (where type_local = 'Dépendance')                                      as nb_dependances,
        count(distinct valeur_fonciere)                                                         as nb_montants,
        count(distinct id_parcelle)                                                             as nb_parcelles
    from lignes
    group by id_mutation
),

logement as (
    select *,
        row_number() over (partition by id_mutation order by surface_reelle_bati desc nulls last, id_parcelle, lot1_numero, adresse_numero) as rang  -- départage déterministe
    from lignes
    where type_local in ('Appartement', 'Maison')
)

select
    l.id_mutation                                   as id_vente,
    l.date_mutation                                 as date_vente,
    year(l.date_mutation)                           as annee_vente,
    l.valeur_fonciere                               as prix,
    l.type_local                                    as type_logement,
    l.surface_reelle_bati                           as surface,
    l.lot1_surface_carrez                           as surface_carrez,
    l.nombre_pieces_principales                     as nb_pieces,
    round(l.valeur_fonciere / l.surface_reelle_bati) as prix_m2,
    c.nb_dependances > 0                            as avec_dependance,
    c.nb_parcelles,
    l.adresse_numero,
    l.adresse_suffixe,
    l.adresse_nom_voie,
    l.code_postal,
    l.code_commune,
    l.nom_commune,
    l.id_parcelle,
    l.longitude,
    l.latitude,
    {{ normaliser_numero('l.adresse_numero') }}     as numero_norm,
    {{ normaliser_voie('l.adresse_nom_voie') }}     as voie_norm,
    -- clé d'adresse au format de l'identifiant BAN des DPE : commune_voie_numéro[_suffixe]
    -- (le suffixe « B » de DVF peut signifier « bis » ou la lettre b : on prépare les deux clés)
    {{ cle_adresse('l.code_commune', 'l.adresse_code_voie', 'l.adresse_numero', 'l.adresse_suffixe', 'principale') }} as cle_adresse,
    {{ cle_adresse('l.code_commune', 'l.adresse_code_voie', 'l.adresse_numero', 'l.adresse_suffixe', 'lettre') }}     as cle_adresse_alt,
    -- bornes métier : on garde les valeurs extrêmes mais on les signale (exclues de l'analyse en gold)
    (l.surface_reelle_bati between 9 and 1000
     and l.valeur_fonciere / l.surface_reelle_bati between 500 and 20000) as est_plausible
from logement l
join composition c using (id_mutation)
where l.rang = 1
  and c.nb_logements = 1
  and c.nb_locaux_activite = 0
  and c.nb_montants = 1
  and l.valeur_fonciere > 0
  and l.surface_reelle_bati > 0

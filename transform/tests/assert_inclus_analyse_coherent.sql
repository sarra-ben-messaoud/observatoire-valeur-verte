-- Une vente incluse dans l'analyse doit avoir une étiquette DPE et un prix au m² plausible.
select id_vente from {{ ref('fait_ventes') }}
where inclus_analyse and (etiquette_dpe is null or not est_plausible)

-- Un DPE rapproché doit toujours avoir été établi avant la vente.
select id_vente from {{ ref('fait_ventes') }}
where est_rapprochee and anciennete_dpe_jours < 0

-- Classes DPE (logements), seuils de la méthode 2021 et calendrier de la loi Climat et Résilience.
-- Seuils en énergie primaire (kWh/m²/an) ; l'étiquette finale retient aussi les émissions de GES (double seuil).
select * from (values
    ('A', 1, 'Très performant',     0,   70, cast(null as integer), false),
    ('B', 2, 'Performant',          71,  110, null,                 false),
    ('C', 3, 'Assez performant',    111, 180, null,                 false),
    ('D', 4, 'Peu performant',      181, 250, null,                 false),
    ('E', 5, 'Peu performant',      251, 330, 2034,                 false),
    ('F', 6, 'Passoire thermique',  331, 420, 2028,                 true),
    ('G', 7, 'Passoire thermique',  421, null, 2025,                true)
) as t(etiquette_dpe, ordre, libelle, conso_ep_min, conso_ep_max, annee_interdiction_location, est_passoire)

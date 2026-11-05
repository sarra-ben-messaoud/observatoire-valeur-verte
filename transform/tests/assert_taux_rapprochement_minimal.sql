-- Garde-fou de qualité : si le taux de rapprochement global chute sous 50 %, quelque chose s'est cassé
-- en amont (format d'adresse modifié par une source, ingestion incomplète…). Le test échoue s'il renvoie une ligne.
select sum(nb_rapprochees) / sum(nb_ventes) as taux
from {{ ref('suivi_rapprochement') }}
having sum(nb_rapprochees) / sum(nb_ventes) < 0.5

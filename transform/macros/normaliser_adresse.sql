{#
  Normalisation des noms de voie, pour comparer DVF (« AV GENERAL DE GAULLE », abréviations FANTOIR)
  et les DPE (« Avenue du Général de Gaulle », adresse BAN en toutes lettres).

  1. Majuscules, sans accents, sans ponctuation.
  2. Suppression du type de voie en tête (RUE, AV, AVENUE, CHE, CHEMIN…) : il est écrit différemment
     selon la source, et le nom propre suffit pour distinguer les voies d'une même commune.
  3. Développement des abréviations courantes à l'intérieur du nom (GDE → GRANDE, ST → SAINT…).
  4. Suppression des mots de liaison (DE, DU, LA, LES…).
  Exemple : « AV GENERAL DE GAULLE » et « Avenue du Général de Gaulle » → « GENERAL GAULLE ».
#}
{% macro normaliser_voie(col) -%}
{%- set mots -%}
string_split(trim(regexp_replace(regexp_replace(upper(strip_accents(coalesce({{ col }}, ''))), '[^A-Z0-9]', ' ', 'g'), '\s+', ' ', 'g')), ' ')
{%- endset -%}
array_to_string(
    list_filter(
        list_transform(
            {#- type de voie en tête, parfois répété dans DVF (« SQ SQUARE DU 1ER ZOUAVE ») -#}
            list_filter({{ mots }}, lambda mot, i:
                not ((i = 1 and mot in ({{ types_de_voie() }}))
                  or (i = 2 and ({{ mots }})[1] in ({{ types_de_voie() }}) and mot in ({{ types_de_voie() }})))),
            lambda mot: case mot
                when 'GDE' then 'GRANDE' when 'GD' then 'GRAND' when 'GDES' then 'GRANDES' when 'GDS' then 'GRANDS'
                when 'PTE' then 'PETITE' when 'PT' then 'PETIT' when 'PTES' then 'PETITES'
                when 'ST' then 'SAINT' when 'STE' then 'SAINTE' when 'STS' then 'SAINTS'
                when 'GAL' then 'GENERAL' when 'MAL' then 'MARECHAL' when 'PDT' then 'PRESIDENT'
                when 'DR' then 'DOCTEUR' when 'PROF' then 'PROFESSEUR'
                else mot end
        ),
        lambda mot: mot <> '' and mot not in ('DE', 'DU', 'DES', 'D', 'LA', 'LE', 'LES', 'L', 'AU', 'AUX', 'ET', 'EN', 'A')
    ),
    ' ')
{%- endmacro %}

{% macro types_de_voie() -%}
'RUE', 'R', 'AV', 'AVE', 'AVENUE', 'BD', 'BOULEVARD', 'CHE', 'CHEM', 'CHEMIN', 'RTE', 'ROUTE',
'ALL', 'ALLEE', 'ALLEES', 'IMP', 'IMPASSE', 'CRS', 'COURS', 'PL', 'PLACE', 'MTE', 'MONTEE', 'QUAI', 'QU',
'PAS', 'PASSAGE', 'PTR', 'GR', 'SQ', 'SQUARE', 'PROM', 'PROMENADE', 'ESP', 'ESPLANADE', 'RES', 'RESIDENCE',
'HAM', 'HAMEAU', 'VC', 'VOIE', 'CHS', 'CHAUSSEE', 'RPT', 'ROND', 'SEN', 'SENTIER', 'CITE', 'LOT', 'LOTISSEMENT',
'DOM', 'DOMAINE', 'VLA', 'VILLA', 'TRA', 'TRAVERSE', 'PRV', 'PARVIS', 'RLE', 'RUELLE', 'GPE', 'GROUPE',
'ENS', 'ENSEMBLE', 'CAR', 'CARREFOUR', 'LD', 'LIEU', 'FG', 'FBG', 'FAUBOURG', 'MAIL', 'CLOS', 'COUR', 'PARC',
'ZA', 'ZI', 'ZAC', 'QUA', 'QUARTIER', 'BRG', 'BOURG'
{%- endmacro %}

{# Numéro de voie sans zéros ni espaces : « 0012 » → « 12 » #}
{% macro normaliser_numero(col) -%}
nullif(ltrim(regexp_replace(coalesce({{ col }}, ''), '[^0-9]', '', 'g'), '0'), '')
{%- endmacro %}

{#
  Clé d'adresse au format de l'identifiant BAN : « 69266_2275_00006 », « 69149_0046_00014_bis ».
  mode 'principale' : B → bis, T → ter, Q → quater ; mode 'lettre' : B → b, T → t…
#}
{% macro cle_adresse(commune, code_voie, numero, suffixe, mode='principale') -%}
case when {{ code_voie }} is not null and {{ normaliser_numero(numero) }} is not null then
    {{ commune }} || '_' || lower({{ code_voie }}) || '_' || lpad({{ normaliser_numero(numero) }}, 5, '0')
    || coalesce('_' || {% if mode == 'principale' -%}
        case upper({{ suffixe }}) when 'B' then 'bis' when 'T' then 'ter' when 'Q' then 'quater' else lower({{ suffixe }}) end
    {%- else -%}
        lower({{ suffixe }})
    {%- endif %}, '')
end
{%- endmacro %}

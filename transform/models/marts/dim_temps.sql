-- Calendrier couvrant la période des ventes.
select
    cast(d as date)                         as date,
    year(d)                                 as annee,
    quarter(d)                              as trimestre,
    month(d)                                as mois,
    strftime(d, '%Y-%m')                    as annee_mois,
    year(d) || '-T' || quarter(d)           as annee_trimestre
from range(date '2022-01-01', date '2026-01-01', interval 1 day) as t(d)

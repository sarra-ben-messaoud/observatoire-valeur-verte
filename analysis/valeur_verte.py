"""Étape 7 — Mesurer la valeur verte « toutes choses égales par ailleurs » (régression hédonique).

    python analysis/valeur_verte.py      (depuis la racine du projet, après dbt build)

Principe : on explique le logarithme du prix au m² par la classe DPE et par les autres caractéristiques
du logement. Le coefficient d'une classe, transformé en pourcentage (exp(b) - 1), est l'écart de prix
par rapport à la classe de référence C, à caractéristiques égales.

Les erreurs standard sont regroupées par commune (« cluster ») : les ventes d'une même commune ne sont pas
indépendantes, et ne pas en tenir compte donnerait des intervalles de confiance trop optimistes.

Sorties : analysis/resultats/*.csv et analysis/resultats/effets_dpe.png
"""

from pathlib import Path

import duckdb
import matplotlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold"
OUT = ROOT / "analysis" / "resultats"

CLASSES = ["A", "B", "D", "E", "F", "G"]          # C = référence (classe la plus fréquente)
DPE = "C(etiquette_dpe, Treatment('C'))"
GROUPE = "C(groupe_dpe, Treatment('C'))"

# Spécifications emboîtées : chaque modèle ajoute des contrôles au précédent
MODELES = {
    "1. Brut": "",
    "2. + type et surface": " + type_logement + log_surface",
    "3. + commune et trimestre": " + type_logement + log_surface + C(code_commune) + C(annee_trimestre)",
    "4. + période de construction": " + type_logement + log_surface + C(code_commune) + C(annee_trimestre)"
                                    " + C(periode_construction)",
}
PRINCIPAL = "3. + commune et trimestre"


def charger() -> pd.DataFrame:
    df = duckdb.connect().execute(f"""
        select f.*, c.est_lyon, t.annee_trimestre
        from '{GOLD / "fait_ventes.parquet"}' f
        join '{GOLD / "dim_commune.parquet"}' c using (code_commune)
        join '{GOLD / "dim_temps.parquet"}' t on t.date = f.date_vente
        where f.inclus_analyse
    """).df()
    df["log_prix_m2"] = np.log(df["prix_m2"])
    df["log_surface"] = np.log(df["surface"])
    df["groupe_dpe"] = df["etiquette_dpe"].map(
        {"A": "A-B", "B": "A-B", "C": "C", "D": "D", "E": "E", "F": "F-G", "G": "F-G"})
    df["zone"] = np.where(df["est_lyon"], "Lyon", "Reste du Rhône")
    return df


def ajuster(df: pd.DataFrame, formule: str):
    groupes = df["code_commune"].astype("category").cat.codes
    return smf.ols(formule, df).fit(cov_type="cluster", cov_kwds={"groups": groupes})


def effets(modele, variable: str, niveaux: list[str]) -> pd.DataFrame:
    """Coefficients transformés en écarts de prix (%) avec intervalle de confiance à 95 %."""
    ic = modele.conf_int()
    lignes = []
    for niv in niveaux:
        nom = f"{variable}[T.{niv}]"
        b, (bas, haut) = modele.params[nom], ic.loc[nom]
        lignes.append({"classe": niv,
                       "effet_pct": 100 * (np.exp(b) - 1),
                       "ic_bas_pct": 100 * (np.exp(bas) - 1),
                       "ic_haut_pct": 100 * (np.exp(haut) - 1),
                       "p_valeur": modele.pvalues[nom]})
    return pd.DataFrame(lignes)


def effet_passoires(df: pd.DataFrame, controles: str) -> dict:
    """Écart F-G vs C, avec intervalle de confiance, sur un sous-échantillon."""
    m = ajuster(df, f"log_prix_m2 ~ {GROUPE}{controles}")
    e = effets(m, GROUPE, ["F-G"]).iloc[0]
    return {"n": int(m.nobs), "effet_pct": e.effet_pct, "ic_bas_pct": e.ic_bas_pct, "ic_haut_pct": e.ic_haut_pct}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = charger()
    print(f"{len(df):,} ventes analysées\n".replace(",", " "))

    # 1. Modèles emboîtés : de l'écart brut à l'effet « toutes choses égales par ailleurs »
    tables = []
    for nom, controles in MODELES.items():
        m = ajuster(df, f"log_prix_m2 ~ {DPE}{controles}")
        t = effets(m, DPE, CLASSES)
        t.insert(0, "modele", nom)
        t["r2"] = m.rsquared
        tables.append(t)
        resume = "  ".join(f"{r.classe} {r.effet_pct:+.1f}%" for r in t.itertuples())
        print(f"{nom:<32} R² {m.rsquared:.2f}   {resume}")
    modeles = pd.concat(tables)
    modeles.to_csv(OUT / "effets_par_modele.csv", index=False, float_format="%.3f")

    # 2. Segments : l'effet F-G vs C est-il le même partout ?
    c3, c4 = MODELES[PRINCIPAL], MODELES["4. + période de construction"]
    segments = []
    for nom, sous in [("Tous logements", df),
                      ("Appartements", df[df.type_logement == "Appartement"]),
                      ("Maisons", df[df.type_logement == "Maison"]),
                      ("Lyon", df[df.zone == "Lyon"]),
                      ("Reste du Rhône", df[df.zone == "Reste du Rhône"]),
                      ("Appartements, reste du Rhône", df[(df.type_logement == "Appartement") & (df.zone == "Reste du Rhône")])]:
        ctl3 = c3.replace(" + type_logement", "") if sous.type_logement.nunique() == 1 else c3
        ctl4 = c4.replace(" + type_logement", "") if sous.type_logement.nunique() == 1 else c4
        segments.append({"segment": nom, "controles": "commune et trimestre", **effet_passoires(sous, ctl3)})
        segments.append({"segment": nom, "controles": "+ période de construction", **effet_passoires(sous, ctl4)})
    segments = pd.DataFrame(segments)
    segments.to_csv(OUT / "effets_par_segment.csv", index=False, float_format="%.3f")
    print("\nF-G vs C par segment :")
    print(segments.to_string(index=False, float_format=lambda x: f"{x:.1f}"))

    # 3. L'écart se creuse-t-il dans le temps, à caractéristiques égales ?
    # Variables d'interaction explicites « passoire × année » (2022 = référence) : l'effet année lui-même
    # est déjà absorbé par les effets fixes trimestre, qu'on ne peut pas inclure deux fois.
    annees = sorted(df.annee_vente.unique())
    for annee in annees[1:]:
        df[f"fg_{annee}"] = ((df.groupe_dpe == "F-G") & (df.annee_vente == annee)).astype(int)
    interactions = " + ".join(f"fg_{a}" for a in annees[1:])
    m = ajuster(df, f"log_prix_m2 ~ {GROUPE} + {interactions}{c3}")
    base = m.params[f"{GROUPE}[T.F-G]"]
    tendance = [{"annee": annees[0], "effet_pct": 100 * (np.exp(base) - 1), "p_ecart_vs_premiere_annee": np.nan}]
    for annee in annees[1:]:
        b = base + m.params[f"fg_{annee}"]
        tendance.append({"annee": annee, "effet_pct": 100 * (np.exp(b) - 1),
                         "p_ecart_vs_premiere_annee": m.pvalues[f"fg_{annee}"]})
    tendance = pd.DataFrame(tendance)
    tendance.to_csv(OUT / "effet_fg_par_annee.csv", index=False, float_format="%.4f")
    print("\nF-G vs C par année (commune et trimestre contrôlés) ; p = test de l'écart avec la première année :")
    print(tendance.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # 4. Robustesse : le résultat tient-il si l'on change les règles d'échantillon ?
    robustesse = pd.DataFrame([
        {"variante": "Modèle principal", **effet_passoires(df, c3)},
        {"variante": "Sans les DPE générés à partir d'un DPE d'immeuble", **effet_passoires(df[~df.issu_dpe_immeuble.fillna(False)], c3)},
        {"variante": "Rapprochement strict (surface à ±5 %)", **effet_passoires(df[df.ecart_surface <= 0.05], c3)},
        {"variante": "DPE de moins d'un an avant la vente", **effet_passoires(df[df.anciennete_dpe_jours <= 365], c3)},
        {"variante": "Hors 1 % des prix extrêmes", **effet_passoires(
            df[df.prix_m2.between(df.prix_m2.quantile(0.01), df.prix_m2.quantile(0.99))], c3)},
    ])
    robustesse.to_csv(OUT / "robustesse.csv", index=False, float_format="%.3f")
    print("\nRobustesse (F-G vs C, commune et trimestre contrôlés) :")
    print(robustesse.to_string(index=False, float_format=lambda x: f"{x:.1f}"))

    tracer(modeles)
    print(f"\nRésultats écrits dans {OUT.relative_to(ROOT)}/")


def tracer(modeles: pd.DataFrame) -> None:
    """Effet de chaque classe vs C, avec intervalle de confiance, pour 3 modèles."""
    couleurs = {"1. Brut": "#9CA3AF", PRINCIPAL: "#1F2933", "4. + période de construction": "#3B6FB6"}
    libelles = {"1. Brut": "Écart brut", PRINCIPAL: "À commune, période, type et surface égaux",
                "4. + période de construction": "… et à époque de construction égale"}
    fig, ax = plt.subplots(figsize=(11, 6), dpi=130)
    ordre = ["A", "B", "C", "D", "E", "F", "G"]
    for i, (nom, couleur) in enumerate(couleurs.items()):
        t = modeles[modeles.modele == nom].set_index("classe")
        xs = np.arange(len(ordre)) + (i - 1) * 0.22
        ys = [0 if c == "C" else t.loc[c, "effet_pct"] for c in ordre]
        bas = [0 if c == "C" else t.loc[c, "effet_pct"] - t.loc[c, "ic_bas_pct"] for c in ordre]
        haut = [0 if c == "C" else t.loc[c, "ic_haut_pct"] - t.loc[c, "effet_pct"] for c in ordre]
        ax.errorbar(xs, ys, yerr=[bas, haut], fmt="o", color=couleur, ms=7, capsize=3, lw=1.5, label=libelles[nom])
    ax.axhline(0, color="#9CA3AF", lw=1)
    ax.set_xticks(range(len(ordre)), [f"Classe {c}" + (" (réf.)" if c == "C" else "") for c in ordre])
    ax.set_ylabel("Écart de prix au m² par rapport à la classe C (%)")
    ax.set_title("À localisation égale, une passoire thermique se vend 20 % moins cher qu'un logement C",
                 loc="left", fontsize=13, weight="bold", pad=26)
    ax.text(0, 1.015, "Rhône, ventes 2022-2025 · intervalles de confiance à 95 %, erreurs regroupées par commune",
            transform=ax.transAxes, fontsize=9.5, color="#6B7280")
    ax.yaxis.grid(True, color="#E5E7EB")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc="lower left", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(OUT / "effets_dpe.png")


if __name__ == "__main__":
    main()

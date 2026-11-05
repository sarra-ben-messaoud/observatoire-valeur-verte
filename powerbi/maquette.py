"""Maquette de la page 1 du dashboard, générée à partir de la couche gold.

    python powerbi/maquette.py      (depuis la racine du projet, après dbt build)
"""

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

DPE = {"A": "#009036", "B": "#55AB26", "C": "#C8D200", "D": "#FFED00", "E": "#FBBA00", "F": "#EB6909", "G": "#E2001A"}
GROUPES = {"A-C": "#55AB26", "D-E": "#E0A800", "F-G": "#E2001A"}
INK, MUTED, GRID, BG, PANEL = "#1F2933", "#6B7280", "#E5E7EB", "#FFFFFF", "#F7F8FA"
fmt = lambda x: f"{x:,.0f}".replace(",", " ")
pct = lambda x: f"{x * 100:+.1f} %".replace(".", ",").replace("-", "−")

con = duckdb.connect()
con.execute("CREATE VIEW f AS SELECT * FROM 'data/gold/fait_ventes.parquet'")
total, analysees = con.execute("SELECT count(*), count(*) FILTER (WHERE inclus_analyse) FROM f").fetchone()
med, ac, fg, part = con.execute("""
    SELECT median(prix_m2), median(prix_m2) FILTER (WHERE etiquette_dpe IN ('A','B','C')),
           median(prix_m2) FILTER (WHERE etiquette_dpe IN ('F','G')),
           count(*) FILTER (WHERE etiquette_dpe IN ('F','G')) / count(*)
    FROM f WHERE inclus_analyse""").fetchone()
classes = con.execute("SELECT etiquette_dpe, count(*), median(prix_m2) FROM f WHERE inclus_analyse GROUP BY 1 ORDER BY 1").fetchall()
annees = con.execute("""
    SELECT annee_vente, CASE WHEN etiquette_dpe IN ('A','B','C') THEN 'A-C' WHEN etiquette_dpe IN ('D','E') THEN 'D-E' ELSE 'F-G' END,
           median(prix_m2)
    FROM f WHERE inclus_analyse GROUP BY ALL ORDER BY 1""").fetchall()
serie = {g: [(a, p) for a, gg, p in annees if gg == g] for g in GROUPES}
ecart = {a: p_fg / p_ac - 1 for (a, p_ac), (_, p_fg) in zip(serie["A-C"], serie["F-G"])}
surf = dict(con.execute("SELECT etiquette_dpe, median(surface) FROM f WHERE inclus_analyse AND type_logement = 'Appartement' GROUP BY 1").fetchall())

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED})
fig = plt.figure(figsize=(16, 9), dpi=110, facecolor=BG)
fig.text(0.03, 0.94, "Observatoire de la valeur verte — Rhône, 2022-2025", fontsize=20, weight="bold")
fig.text(0.03, 0.905, "Ventes d'un seul logement rapprochées de façon fiable d'un DPE · sources DVF (DGFiP) et ADEME",
         fontsize=11, color=MUTED)
for i, (lab, val) in enumerate([("Type de logement", "Tous"), ("Année", "Toutes"), ("Territoire", "Rhône")]):
    x = 0.62 + i * 0.125
    fig.patches.append(FancyBboxPatch((x, 0.895), 0.115, 0.05, boxstyle="round,pad=0.002,rounding_size=0.006",
                                      transform=fig.transFigure, fc=PANEL, ec=GRID))
    fig.text(x + 0.008, 0.928, lab, fontsize=8.5, color=MUTED)
    fig.text(x + 0.008, 0.905, val + "  ▾", fontsize=10.5)
kpis = [("Ventes analysées", fmt(analysees), f"sur {fmt(total)} ventes"),
        ("Prix médian", f"{fmt(med)} €/m²", "toutes classes"),
        ("Décote F-G vs A-C", pct(fg / ac - 1), f"{fmt(fg)} vs {fmt(ac)} €/m²"),
        ("Part de passoires F-G", f"{part * 100:.1f} %".replace(".", ","), "des ventes analysées")]
for i, (titre, valeur, sous) in enumerate(kpis):
    x = 0.03 + i * 0.2375
    fig.patches.append(FancyBboxPatch((x, 0.70), 0.225, 0.16, boxstyle="round,pad=0.002,rounding_size=0.01",
                                      transform=fig.transFigure, fc=PANEL, ec=GRID))
    fig.text(x + 0.015, 0.825, titre, fontsize=11, color=MUTED)
    fig.text(x + 0.015, 0.758, valeur, fontsize=26, weight="bold", color="#B91C1C" if valeur.startswith("−") else INK)
    fig.text(x + 0.015, 0.718, sous, fontsize=9.5, color=MUTED)

ax = fig.add_axes([0.05, 0.12, 0.42, 0.47])
bars = ax.bar(range(7), [c[2] for c in classes], color=[DPE[c[0]] for c in classes], width=0.62, edgecolor=BG, linewidth=2)
for b, c in zip(bars, classes):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 60, fmt(c[2]), ha="center", fontsize=10)
ax.set_xticks(range(7))
ax.set_xticklabels([f"{c[0]}\nn = {fmt(c[1])}" for c in classes], fontsize=10, color=INK)
ax.set_title("Prix médian au m² par classe DPE", loc="left", fontsize=13, weight="bold", pad=12)
ax.set_ylim(0, 5000)
ax.set_ylabel("€/m²")

ax2 = fig.add_axes([0.55, 0.12, 0.40, 0.47])
for g, couleur in GROUPES.items():
    xs, ys = zip(*serie[g])
    ax2.plot(xs, ys, color=couleur, lw=2.2, marker="o", ms=7, markeredgecolor=BG, markeredgewidth=1.5)
    ax2.text(xs[-1] + 0.08, ys[-1], f"{g}  {fmt(ys[-1])} €", va="center", fontsize=10)
premiere, derniere = min(ecart), max(ecart)
ax2.set_title("Évolution du prix médian au m² par groupe de classes", loc="left", fontsize=13, weight="bold", pad=24)
ax2.text(0, 1.02, f"L'écart F-G / A-C se creuse : {pct(ecart[premiere])} en {premiere}, {pct(ecart[derniere])} en {derniere}",
         transform=ax2.transAxes, fontsize=10, color=MUTED)
ax2.set_xticks(sorted(ecart))
ax2.set_xlim(premiere - 0.2, derniere + 0.9)
ax2.set_ylim(3000, 4800)
ax2.set_ylabel("€/m²")
for a in (ax, ax2):
    a.yaxis.grid(True, color=GRID)
    a.set_axisbelow(True)
    for s in ("top", "right", "left"):
        a.spines[s].set_visible(False)
    a.spines["bottom"].set_color(GRID)
fig.text(0.03, 0.02, f"Écarts bruts, non corrigés de la surface ni de la localisation (les appartements G font {fmt(surf['G'])} m² "
         f"médians, contre {fmt(surf['C'])} m² pour les C). Analyse « toutes choses égales par ailleurs » : étape 7.",
         fontsize=9, color=MUTED)
fig.savefig("powerbi/maquette_page1.png", facecolor=BG)
print("Maquette enregistrée : powerbi/maquette_page1.png")

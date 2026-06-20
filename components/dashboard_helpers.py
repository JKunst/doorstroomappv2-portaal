"""
Gedeelde helpers voor de dashboard-pagina's (examenresultaten, onderbouw, cohort).

Bevat:
- categorie-mappings voor examenklassen en onderbouw
- een gebroken-y-as lijngrafiek (twee gestapelde subplots) in Plotly,
  zodat de hoge lijn (geslaagd/doorgestroomd) en de lage categorieën
  allebei goed leesbaar zijn.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Corderius-palet (consistent met styling.py)
KLEUREN = {
    "Geslaagd of opgestroomd": "#0D5259",
    "Doorgestroomd":           "#0D5259",
    "Geslaagd":                "#0D5259",
    "Doublure":                "#E8612A",
    "Afgewezen (VAVO/MBO)":    "#B04A3F",
    "Afgestroomd":             "#C98A2B",
    "VO verlater":             "#8A6D9C",
    "Opleiding elders/onbekend": "#9AA3A2",
    "Overig":                  "#B8BCB8",
    "Onbekend/overig":         "#B8BCB8",
}


def geldige_jaargrens(df):
    """
    De simulatie voegt een 'vorig jaar' (laagste) en een 'volgend jaar' (hoogste)
    toe als context. Die randjaren hebben duidelijk minder records dan de echte
    databestand-jaren. We snijden ze weg door het laagste en hoogste jaar te
    verwerpen als hun volume onder ~85% van de mediaan van de tussenliggende
    jaren ligt.
    """
    per_jaar = df["Schooljaar"].value_counts().sort_index()
    if len(per_jaar) <= 2:
        return (int(per_jaar.index.min()), int(per_jaar.index.max()))
    jaren = list(per_jaar.index)
    midden = per_jaar.iloc[1:-1]
    drempel = midden.median() * 0.85
    lo, hi = jaren[0], jaren[-1]
    if per_jaar.iloc[0] < drempel:
        lo = jaren[1]
    if per_jaar.iloc[-1] < drempel:
        hi = jaren[-2]
    return (int(lo), int(hi))


def kale_fase(serie: pd.Series) -> pd.Series:
    """Strip de _doublure-suffix zodat fasen vergelijkbaar zijn."""
    return serie.astype(str).str.replace("_doublure", "", regex=False)


# ── Categorie-indeling examenklassen ─────────────────────────────────────────
def categorie_examen(d):
    if d in ("Geslaagd", "Geslaagd (prognose)", "Opstroom"):
        return "Geslaagd of opgestroomd"
    if d == "Doublure":
        return "Doublure"
    if d in ("Afgewezen", "Afgewezen (prognose)"):
        return "Afgewezen (VAVO/MBO)"
    if d == "VO verlater":
        return "VO verlater"
    return "Overig"


CATS_EXAMEN = ["Geslaagd of opgestroomd", "Doublure",
               "Afgewezen (VAVO/MBO)", "VO verlater", "Overig"]


# ── Categorie-indeling onderbouw ─────────────────────────────────────────────
def categorie_onderbouw(d):
    if d in ("Doorstroom", "Opstroom"):
        return "Doorgestroomd"
    if d == "Doublure":
        return "Doublure"
    if d == "Afstroom":
        return "Afgestroomd"
    if d == "VO verlater":
        return "VO verlater"
    if d == "Opleiding elders/onbekend":
        return "Opleiding elders/onbekend"
    return "Onbekend/overig"


CATS_ONDERBOUW = ["Doorgestroomd", "Doublure", "Afgestroomd",
                  "VO verlater", "Opleiding elders/onbekend", "Onbekend/overig"]


def percentages_per_jaar(df, fase, catfn, cats, drop_laatste_jaar=False,
                         geldige_jaren=None):
    """
    Bouwt een tabel met percentages en absolute aantallen per schooljaar
    voor één leerfase.
    geldige_jaren: optionele (min, max) tuple om simulatie-randjaren te weren.
    Retourneert (jaren, perc_dict, count_dict, totaal_lijst, overig_detail).
    """
    sub = df[kale_fase(df["Leerfase (afk)"]) == fase].copy()
    if geldige_jaren is not None:
        lo, hi = geldige_jaren
        sub = sub[(sub["Schooljaar"] >= lo) & (sub["Schooljaar"] <= hi)]
    sub["U"] = sub["Doorstroom"].apply(catfn)
    cnt = pd.crosstab(sub["Schooljaar"], sub["U"])
    for c in cats:
        if c not in cnt.columns:
            cnt[c] = 0
    cnt = cnt[cats]

    if drop_laatste_jaar and len(cnt) > 0:
        # Laat het lopende jaar weg als dat (vrijwel) volledig onbekend is
        laatste = cnt.index.max()
        rij = cnt.loc[laatste]
        leeg_kol = cats[-1]
        if rij.sum() > 0 and rij[leeg_kol] / rij.sum() > 0.8:
            cnt = cnt.drop(laatste)

    tot = cnt.sum(axis=1)
    perc = (cnt.div(tot, axis=0) * 100).round(1)
    jaren = [int(x) for x in cnt.index]
    perc_d = {c: [float(x) for x in perc[c]] for c in cats}
    cnt_d = {c: [int(x) for x in cnt[c]] for c in cats}
    overig_detail = (
        sub[sub["U"] == cats[-1]]["Doorstroom"].fillna("(leeg)").value_counts().to_dict()
    )
    return jaren, perc_d, cnt_d, [int(x) for x in tot], overig_detail


def gebroken_lijngrafiek(jaren, perc_d, cnt_d, cats, titel,
                         hoog=(70, 100), laag=(0, 20)):
    """
    Twee verticaal gestapelde subplots met een gebroken y-as:
    boven het smalle hoge bereik, onder het ruime lage bereik.
    De hoge lijn blijft leesbaar zonder de lage lijnen plat te drukken.
    """
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.32, 0.68], vertical_spacing=0.04,
    )

    for c in cats:
        kleur = KLEUREN.get(c, "#666")
        ydata = perc_d[c]
        counts = cnt_d[c]
        hover = [
            f"{c}<br>{jaar}: {y:.1f}%  ({n})"
            for jaar, y, n in zip(jaren, ydata, counts)
        ]
        # bovenste pane
        fig.add_trace(go.Scatter(
            x=jaren, y=ydata, name=c, legendgroup=c, mode="lines+markers",
            line=dict(color=kleur, width=2.5), marker=dict(size=6),
            hovertext=hover, hoverinfo="text", showlegend=True,
        ), row=1, col=1)
        # onderste pane (zelfde data, andere y-as), legenda niet dubbel
        fig.add_trace(go.Scatter(
            x=jaren, y=ydata, name=c, legendgroup=c, mode="lines+markers",
            line=dict(color=kleur, width=2.5), marker=dict(size=6),
            hovertext=hover, hoverinfo="text", showlegend=False,
        ), row=2, col=1)

    fig.update_yaxes(range=[hoog[0], hoog[1]], row=1, col=1,
                     ticksuffix="%", dtick=10, gridcolor="#E8E4DA")
    fig.update_yaxes(range=[laag[0], laag[1]], row=2, col=1,
                     ticksuffix="%", dtick=5, gridcolor="#E8E4DA")
    fig.update_xaxes(dtick=1, row=2, col=1, gridcolor="#F0EEE6")

    fig.update_layout(
        title=titel,
        height=520, hovermode="closest",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#1A1A2E"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                    xanchor="center", x=0.5),
        margin=dict(t=60, b=40, l=50, r=20),
    )
    # zigzag-annotatie tussen de twee panes (visuele breukmarkering)
    fig.add_annotation(
        text="≈", xref="paper", yref="paper",
        x=-0.035, y=0.66, showarrow=False,
        font=dict(size=22, color="#C9C2B2"),
    )
    return fig

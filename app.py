from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

DOSSIER = Path(__file__).parent / "donnees"

st.set_page_config(page_title="L'électricité dans 12 quartiers", page_icon=" ", layout="wide")

st.title("L'électricité dans 12 quartiers")
st.caption("Relevés mensuels de janvier 2024 à décembre 2025. Données fictives.")


@st.cache_data
def charger_donnees():
    return pd.read_csv(DOSSIER / "consommation_propre.csv")


conso = charger_donnees()

st.write(
    "Une compagnie d'électricité (fictive) a relevé la consommation de 12 quartiers de Port-au-Prince, "
    "Delmas, Pétion-Ville et Cap-Haïtien. "
    "Le directeur veut savoir si la consommation suit la chaleur, ou les heures de courant."
)

# Étape 3 : les filtres
st.sidebar.header("Filtres")
toutes_les_communes = sorted(conso["commune"].unique())
communes = st.sidebar.multiselect("Communes", toutes_les_communes, default=toutes_les_communes)
annees = sorted(int(a) for a in conso["annee"].unique())
annee = st.sidebar.selectbox("Année", annees, index=annees.index(2025))

if not communes:
    st.warning("Choisissez au moins une commune dans la barre latérale.")
    st.stop()

conso_communes = conso[conso["commune"].isin(communes)]
df = conso_communes[conso_communes["annee"] == annee]

# Étape 4 : les indicateurs
col1, col2, col3 = st.columns(3)
col1.metric(f"Consommation totale en {annee}", f"{df['kwh'].sum() / 1e6:.2f} millions de kWh")
col2.metric("Consommation par abonné", f"{df['kwh_par_abonne'].mean():.1f} kWh")
col3.metric("Courant par jour", f"{df['heures_courant'].mean():.1f} heures")

# Étape 5 : un onglet par question
onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs(
    ["Quartiers", "Évolution", "Chaleur ou courant ?", "Coupures", "Relevés atypiques"]
)

with onglet1:
    st.subheader("Quels quartiers consomment le plus par abonné ?")
    classement = df.groupby("quartier")["kwh_par_abonne"].mean().round(1).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    classement.sort_values().plot.barh(ax=ax, color="steelblue")
    ax.set_xlabel("kWh par abonné (moyenne mensuelle)")
    ax.set_ylabel("")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    st.write(
        f"En {annee}, {classement.index[0]} est en tête avec {classement.iloc[0]} kWh par abonné, "
        f"et {classement.index[-1]} ferme la marche avec {classement.iloc[-1]} kWh."
    )

with onglet2:
    st.subheader("Comment la consommation évolue-t-elle, commune par commune ?")
    st.caption("Les deux années sont comparées, quelle que soit l'année choisie dans la barre latérale.")
    courbes = conso_communes.groupby(["mois", "commune"])["kwh_par_abonne"].mean().unstack()
    st.line_chart(courbes, y_label="kWh par abonné")
    totaux = conso_communes.pivot_table(index="commune", columns="annee", values="kwh", aggfunc="sum")
    hausse = ((totaux[2025] / totaux[2024] - 1) * 100).sort_values(ascending=False)
    if len(hausse) == 1:
        st.write(
            f"{hausse.index[0]} : {hausse.iloc[0]:+.1f} % de consommation totale entre 2024 et 2025 "
            f"({totaux.loc[hausse.index[0], 2024] / 1e6:.2f} à {totaux.loc[hausse.index[0], 2025] / 1e6:.2f} millions de kWh)."
        )
    else:
        st.write(
            f"Entre 2024 et 2025, {hausse.index[0]} progresse le plus ({hausse.iloc[0]:+.1f} %) "
            f"et {hausse.index[-1]} le moins ({hausse.iloc[-1]:+.1f} %)."
        )

with onglet3:
    st.subheader("La consommation suit-elle la chaleur, ou les heures de courant ?")
    st.caption("Quartiers résidentiels des communes choisies, sur les deux années.")
    residentiels = conso_communes[conso_communes["type"] == "Résidentiel"]
    if len(residentiels) < 3:
        st.info("Pas assez de relevés résidentiels pour calculer une corrélation.")
    else:
        st.scatter_chart(
            residentiels,
            x="heures_courant",
            y="kwh_par_abonne",
            x_label="Heures de courant par jour",
            y_label="kWh par abonné",
        )
        corr_courant = residentiels["kwh_par_abonne"].corr(residentiels["heures_courant"])
        corr_temperature = residentiels["kwh_par_abonne"].corr(residentiels["temperature_c"])
        st.write(
            f"La corrélation de la consommation par abonné est de {corr_courant:.2f} avec les heures de courant "
            f"et de {corr_temperature:.2f} avec la température."
        )

with onglet4:
    st.subheader("Où les coupures sont-elles les plus longues ?")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(df["heures_courant"], bins=10, color="steelblue", edgecolor="white")
    ax.set_xlabel("Heures de courant par jour")
    ax.set_ylabel("Nombre de relevés")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    medianes = df.groupby("commune")["heures_courant"].median()
    faibles = df[df["heures_courant"] < 8]
    phrase = (
        f"En {annee}, la médiane des heures de courant est la plus basse à {medianes.idxmin()} "
        f"({medianes.min():.1f} heures par jour). "
        f"{len(faibles)} relevé(s) ont moins de 8 heures de courant par jour"
    )
    if len(faibles) > 0:
        phrase += " : " + ", ".join(sorted(faibles["quartier"].unique()))
    st.write(phrase + ".")

with onglet5:
    st.subheader("Quels relevés sortent du lot ?")
    plus_gros = df.nlargest(3, "kwh")[["mois", "quartier", "type", "kwh"]]
    fig, ax = plt.subplots(figsize=(8, 3))
    etiquettes = plus_gros["quartier"] + " (" + plus_gros["mois"] + ")"
    ax.barh(etiquettes[::-1], plus_gros["kwh"][::-1], color="steelblue")
    ax.set_xlabel("kWh")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    premier = plus_gros.iloc[0]
    kwh_premier = f"{premier['kwh']:,}".replace(",", " ")
    st.write(
        f"Le plus gros relevé de {annee} est celui de {premier['quartier']} en {premier['mois']} : {kwh_premier} kWh."
    )

# Étape 6 : la conclusion et les données
st.markdown(
    """
### Conclusion

Dans les quartiers résidentiels, la consommation par abonné suit les heures de courant (corrélation de 0.76) et non la chaleur (corrélation de -0.15 avec la température).
Une corrélation montre seulement que deux séries varient ensemble : elle ne prouve pas que plus d'heures de courant *provoquent* plus de consommation, ni qu'aucun autre facteur (type de quartier, nombre d'appareils, tarif) n'intervient.
Pour trancher, il faudrait comparer un même quartier avant et après un changement de ses heures de courant.
"""
)

with st.expander("Voir les données filtrées"):
    st.dataframe(df, hide_index=True)

import streamlit as st
import pandas as pd
import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import time
import plotly.express as px

st.set_page_config(page_title="Scraper Multi-DB", layout="wide")

# ---------------------------
# STYLE CSS MODERNE
# ---------------------------
st.markdown("""
<style>
[data-testid="stSidebar"] {background-color: #f7f9fc; display: flex; flex-direction: column;}
.big-font {font-size:28px !important; font-weight:bold; color:#0B3D91; margin-bottom:15px;}
.stMetricValue {color: #1E81B0; font-weight:bold;}
.stMetricLabel {color: #0B3D91; font-weight:bold;}
.card {background-color:#ffffff; padding:15px; border-radius:12px; box-shadow: 0 4px 8px rgba(0,0,0,0.15); margin-bottom:15px;}
.card-title {font-size:16px; font-weight:bold; color:#0B3D91;}
.card-text {font-size:14px; color:#333;}
div.stButton > button:first-child {
    background-color: #003366;
    color: white;
    border-radius: 4px;
    padding: 8px 20px;
    border: none;
    font-size: 15px;
}
div.stButton > button:first-child:hover {
    background-color: #0055a5;
}
.eval-title {
    font-size: 32px;
    font-weight: bold;
    text-align: center;
    margin-bottom: 30px;
    color: #0b3d91;
}
.stLinkButton > a {
    display: inline-block;
    padding: 14px 28px;
    border-radius: 8px;
    font-weight: 600;
    text-align: center;
    transition: all 0.3s ease;
    background-color: #0b3d91;
    color: white;
    border: none;
}
.stLinkButton > a:hover {
    background-color: #072c66;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# CONFIG BASES
# ---------------------------
db_config = {
    "Article1.db": {"table": "IM_table",  "col1": "type_habits",    "url": "https://sn.coinafrique.com/categorie/vetements-homme"},
    "Article2.db": {"table": "IM_table2", "col1": "type_chaussures", "url": "https://sn.coinafrique.com/categorie/chaussures-homme"},
    "Article3.db": {"table": "IM_table3", "col1": "type_habits",    "url": "https://sn.coinafrique.com/categorie/vetements-enfants"},
    "Article4.db": {"table": "IM_table4", "col1": "type_chaussures", "url": "https://sn.coinafrique.com/categorie/chaussures-enfants"},
}

# ---------------------------
# INIT DATABASES
# ---------------------------
def init_db():
    for db_name, cfg in db_config.items():
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        col1 = cfg["col1"]
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS {cfg['table']} (
                {col1}     TEXT,
                prix       TEXT,
                adresse    TEXT,
                image_lien TEXT
            )
        """)
        conn.commit()
        conn.close()

init_db()

# ---------------------------
# BEAUTIFULSOUP SCRAPER
# ---------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def nettoyer_prix(texte):
    """Garde uniquement les chiffres du prix."""
    if not texte:
        return ""
    chiffres = re.sub(r"[^\d]", "", texte)
    return chiffres if chiffres else ""

def nettoyer_texte(texte):
    """Supprime les espaces superflus."""
    if not texte:
        return ""
    return " ".join(texte.split()).strip()

def scrape_logic(nb_pages, url, col1):
    """
    Scrape nb_pages pages de l'URL avec BeautifulSoup.
    Retourne un DataFrame avec les colonnes [col1, prix, adresse, image_lien].
    """
    data = []

    for p in range(1, nb_pages + 1):
        page_url = f"{url}?page={p}"
        try:
            response = requests.get(page_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Sélecteur principal des annonces sur CoinAfrique
            annonces = soup.find_all("div", class_="col s6 m4 l3")

            # Fallback si la structure change
            if not annonces:
                annonces = soup.find_all("div", class_=lambda c: c and "ad__card" in c)

            for annonce in annonces:
                try:
                    # Type / nom du produit
                    type_elem = (
                        annonce.find("p", class_="ad__card-description") or
                        annonce.find("a", attrs={"title": True})
                    )
                    type_val = nettoyer_texte(
                        type_elem.get("title") or type_elem.get_text()
                        if type_elem else ""
                    )

                    # Prix
                    prix_elem = annonce.find("p", class_="ad__card-price")
                    prix_val = nettoyer_prix(prix_elem.get_text() if prix_elem else "")

                    # Adresse
                    adresse_elem = annonce.find("p", class_="ad__card-location")
                    adresse_val = nettoyer_texte(adresse_elem.get_text() if adresse_elem else "")

                    # Image
                    img_elem = annonce.find("img")
                    image_lien = ""
                    if img_elem:
                        image_lien = (
                            img_elem.get("src") or
                            img_elem.get("data-src") or
                            img_elem.get("data-original") or ""
                        )

                    data.append({
                        col1:        type_val,
                        "prix":      prix_val,
                        "adresse":   adresse_val,
                        "image_lien": image_lien,
                    })

                except Exception:
                    continue

            time.sleep(1)  # Pause polie entre les pages

        except Exception as e:
            st.warning(f"⚠️ Erreur page {p} ({page_url}) : {e}")
            continue

    return pd.DataFrame(data, columns=[col1, "prix", "adresse", "image_lien"])


# ---------------------------
# SIDEBAR - MENU BOUTONS
# ---------------------------
with st.sidebar:
    st.markdown("## Navigation")
    st.markdown("---")

    if "choice" not in st.session_state:
        st.session_state.choice = "Scraper Live"

    if st.button("Scraper Live", use_container_width=True):
        st.session_state.choice = "Scraper Live"
    if st.button("Upload Web Scraper", use_container_width=True):
        st.session_state.choice = "Upload Web Scraper"
    if st.button("Dashboard", use_container_width=True):
        st.session_state.choice = "Dashboard"
    if st.button("Évaluation", use_container_width=True):
        st.session_state.choice = "Évaluation"

    st.markdown("---")
    db_choice = st.selectbox("Choisir la base", list(db_config.keys()))

choice = st.session_state.choice
table  = db_config[db_choice]["table"]
col1   = db_config[db_choice]["col1"]


# ---------------------------
# SCRAPER LIVE
# ---------------------------
if choice == "Scraper Live":
    st.markdown('<p class="big-font">🌍 CoinAfrique Scraper Live</p>', unsafe_allow_html=True)

    with st.expander("Paramètres du scraping", expanded=True):
        nb_pages = st.number_input("Nombre de pages à scraper", min_value=1, max_value=5, value=1, step=1)

        if st.button("Lancer le scraping"):
            url = db_config[db_choice]["url"]

            progress_text = st.empty()
            progress_bar  = st.progress(0)
            status_placeholder = st.empty()

            data_all = pd.DataFrame()

            for i in range(1, nb_pages + 1):
                progress_text.text(f"🌐 Scraping page {i}/{nb_pages} ...")
                df_page = scrape_logic(1, f"{url}?page={i}", col1)
                data_all = pd.concat([data_all, df_page], ignore_index=True)
                progress_bar.progress(int(i / nb_pages * 100))

            # Sauvegarde en base
            conn   = sqlite3.connect(db_choice)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            existing_cols = [row[1] for row in cursor.fetchall()]
            for c in data_all.columns:
                if c not in existing_cols:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {c} TEXT")
            conn.commit()
            data_all.to_sql(table, conn, if_exists="append", index=False)
            conn.close()

            status_placeholder.success(
                f"✅ Scraping terminé : {len(data_all)} éléments ajoutés dans {db_choice} !"
            )
            st.dataframe(data_all.head(), use_container_width=True)
            progress_text.empty()
            progress_bar.empty()


# ---------------------------
# UPLOAD WEB SCRAPER
# ---------------------------
elif choice == "Upload Web Scraper":
    uploaded_file = st.file_uploader("Choisir un fichier CSV", type="csv")
    if uploaded_file:
        try:
            df_raw = pd.read_csv(uploaded_file, on_bad_lines="skip", sep=None, engine="python")
            st.success(f"CSV chargé : {df_raw.shape[0]} lignes, {df_raw.shape[1]} colonnes")
        except Exception as e:
            st.error(f"Erreur chargement CSV : {e}")
            df_raw = None

        if df_raw is not None:
            st.dataframe(df_raw.head(), use_container_width=True)

            if st.button("Nettoyer et sauvegarder"):
                df_clean = df_raw.dropna().drop_duplicates()

                col_mapping = {}
                if df_clean.shape[1] >= 4:
                    col_mapping = {
                        df_clean.columns[0]: col1,
                        df_clean.columns[1]: "prix",
                        df_clean.columns[2]: "adresse",
                        df_clean.columns[3]: "image_lien",
                    }
                df_final = df_clean.rename(columns=col_mapping)
                df_final["source"] = "Web Scraper Ext"
                df_final = df_final.loc[:, ~df_final.columns.duplicated()]

                conn   = sqlite3.connect(db_choice)
                cursor = conn.cursor()
                columns_sql = ", ".join([f"{c} TEXT" for c in df_final.columns])
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns_sql})")
                cursor.execute(f"PRAGMA table_info({table})")
                existing_cols = [row[1] for row in cursor.fetchall()]
                for c in df_final.columns:
                    if c not in existing_cols:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {c} TEXT")
                conn.commit()
                df_final.to_sql(table, conn, if_exists="append", index=False)
                conn.close()

                st.success(f"✅ {len(df_final)} lignes ajoutées dans {db_choice} !")


# ---------------------------
# DASHBOARD
# ---------------------------
elif choice == "Dashboard":
    conn = sqlite3.connect(db_choice)
    df   = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()

    if df.empty:
        st.warning("Base vide. Lancez d'abord le scraper.")
    else:
        df["prix_num"] = (
            df["prix"].astype(str)
            .str.replace(r"[^\d]", "", regex=True)
            .replace("", "0")
            .astype(float)
        )

        st.markdown('<p class="big-font">📊 Dashboard Produits</p>', unsafe_allow_html=True)

        type_unique   = df[col1].dropna().unique()
        selected_type = st.selectbox(f"Filtrer par {col1}", ["Tous"] + list(type_unique))
        if selected_type != "Tous":
            df = df[df[col1] == selected_type]

        colA, colB, colC = st.columns(3)
        colA.metric("Prix min",   f"{df['prix_num'].min():,.0f} FCFA")
        colB.metric("Prix max",   f"{df['prix_num'].max():,.0f} FCFA")
        colC.metric("Prix moyen", f"{df['prix_num'].mean():,.0f} FCFA")

        st.markdown("---")

        st.subheader(f"Répartition par {col1}")
        df_counts = df[col1].value_counts().reset_index()
        df_counts.columns = [col1, "Count"]
        fig_type = px.bar(df_counts, x=col1, y="Count", color="Count",
                          color_continuous_scale=px.colors.sequential.Teal)
        st.plotly_chart(fig_type, use_container_width=True)

        st.subheader("Répartition par adresse")
        df_addr = df["adresse"].value_counts().reset_index()
        df_addr.columns = ["Adresse", "Count"]
        df_addr = df_addr.head(10)
        fig_addr = px.bar(df_addr, x="Adresse", y="Count", color="Count",
                          color_continuous_scale=px.colors.sequential.Plasma)
        st.plotly_chart(fig_addr, use_container_width=True)

        st.subheader("Top 10 produits")
        df_top = df.head(10).reset_index(drop=True)
        for i in range(len(df_top)):
            st.markdown("<hr>", unsafe_allow_html=True)
            col_img, col_info = st.columns([1, 3])
            with col_img:
                if pd.notna(df_top.loc[i, "image_lien"]) and df_top.loc[i, "image_lien"]:
                    st.image(df_top.loc[i, "image_lien"], width=150)
            with col_info:
                st.markdown(f"**Type :** {df_top.loc[i, col1]}")
                st.markdown(f"**Prix :** {df_top.loc[i, 'prix']}")
                st.markdown(f"**Adresse :** {df_top.loc[i, 'adresse']}")


# ---------------------------
# ÉVALUATION
# ---------------------------
elif choice == "Évaluation":
    st.markdown('<p class="big-font">Votre avis nous intéresse</p>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.link_button("📋 Formulaire Kobo", "https://ee.kobotoolbox.org/x/mDA0mZRs")
    with col_b:
        st.link_button("📋 Formulaire Google Forms", "https://forms.gle/pap2BDj6Eab9d9zC7")

import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os
from dotenv import load_dotenv



#1 --- INICJALIZACJA ZMIENNYCH ---
load_dotenv()
NEON_DATABASE_URL = os.getenv('DATABASE_URL')
st.set_page_config(page_title="Analiza Mieszkaniowa GUS", layout="wide")
@st.cache_data


#2 --- FUNKCJE POMOCNICZE ---
def get_data():
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cur = conn.cursor()

    cur.execute("SELECT unit_name, year, quarter, value FROM housing_data")
    data = cur.fetchall()

    colnames = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()

    df = pd.DataFrame(data, columns=colnames)
    # Tworzymy czytelną datę dla szeregów czasowych
    df['period'] = df['year'].astype(str) + " Q" + df['quarter'].astype(str)
    return df

# Pobranie danych
df = get_data()

all_units = sorted(df['unit_name'].unique())
palette = px.colors.qualitative.Set3
color_map = {}
for i, unit in enumerate(all_units):
    color_map[unit] = palette[i % len(palette)]

st.title("📊 System Analizy Statystycznej Rynku Mieszkaniowego")
st.markdown("Dane pochodzą z API GUS BDL (2019-2024)")

#SIDEBAR
st.sidebar.header("⚙️ Filtry")

#Filtr Jednostki (Multiselect)
selected_units = st.sidebar.multiselect(
    "1. Wybierz powiaty:", 
    options=sorted(df['unit_name'].unique()), 
    default=["Powiat m. Kraków"]
)

#Filtr Lat (Slider)
year_range = st.sidebar.slider(
    "2. Zakres lat:", 
    int(df['year'].min()), int(df['year'].max()), 
    (2020, 2024)
)

#Filtr Kwartałów (Checkbox/Multiselect)
selected_quarters = st.sidebar.multiselect(
    "3. Wybierz kwartały:", 
    options=[1, 2, 3, 4], 
    default=[1, 2, 3, 4]
)

#Filtr Wartości Minimalnej (Input)
min_val = st.sidebar.number_input(
    "4. Minimalna cena za m2:", 
    min_value=0, 
    value=0)

#Filtr Nazwy (Search)
search_query = st.sidebar.text_input("5. Szukaj w nazwie powiatu:", "")

# ZASTOSOWANIE FILTRÓW
filtered_df = df[
    (df['unit_name'].isin(selected_units)) &
    (df['year'] >= year_range[0]) & (df['year'] <= year_range[1]) &
    (df['quarter'].isin(selected_quarters)) &
    (df['value'] >= min_val) &
    (df['unit_name'].str.contains(search_query, case=False))
]

#3 --- WIZUALIZACJE ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Szeregi Czasowe (Time Series)")
    if not filtered_df.empty:
        fig_time = px.line(
            filtered_df.sort_values(['year', 'quarter']), 
            x='period', y='value', color='unit_name',
            labels={'value': 'Mediany cen mieszkań za m2', 'period': 'Okres'},
            markers=True,
            color_discrete_map=color_map
        )
        fig_time.update_xaxes(tickangle=45)
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.warning("Brak danych dla wybranych filtrów.")

with col2:
    st.subheader("📊 Analiza Ilościowa (Porównanie)")
    if not filtered_df.empty:
        # Agregujemy dane, aby pokazać sumę dla wybranych filtrów
        summary_df = filtered_df.groupby('unit_name')['value'].mean().reset_index()
        fig_bar = px.bar(
            summary_df, 
            x='unit_name', y='value', color='unit_name',
            labels={'value': 'Średnia cena za m2 w wybranym okresie', 'unit_name': 'Powiat'},
            text_auto='.2f',
            color_discrete_map=color_map
        )
        fig_bar.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_bar, use_container_width=True)

# TABELA Z DANYMI
st.subheader("📋 Dane źródłowe")
st.dataframe(filtered_df.sorst_values(['year', 'quarter'], ascending=False), use_container_width=True)
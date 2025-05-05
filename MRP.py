import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import hashlib
import os
import urllib.parse
import gdown
from statsmodels.tsa.arima.model import ARIMA
import numpy as np
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# ----------------- PAGE CONFIG -----------------
st.set_page_config(page_title="Predictive Healthcare Analytics", layout="wide")

# ----------------- GOOGLE DRIVE / SHEET SETUP -----------------
sheet_id = "1hJEb7aMjrD-EfAoN9jdhwBK2m9o0U-mh"
sheet_name = "not_vaccinated_analysis (3)"
encoded_sheet = urllib.parse.quote(sheet_name)
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"

census_file_id = "1Fswh6Eq_wrsf5FbpaaUve9K0KOZ6q3zg"
geojson_file_id = "1gnux_uKipCE4f-hiThO7c_WHF8kx8nh8"

census_filename = "d5f13b5b-c3c7-46ca-a8fc-ce4450a8b9cc.csv"
geojson_filename = "California_Incorporated_Cities.geojson"

def download_file(file_id, filename):
    if not os.path.exists(filename):
        gdown.download(f"https://drive.google.com/uc?id={file_id}", filename, quiet=False)

download_file(census_file_id, census_filename)
download_file(geojson_file_id, geojson_filename)

# ----------------- DATABASE SETUP -----------------
DB_FILE = "vaccination_data.db"
USER_DB = "users.db"

def create_connection(path):
    return sqlite3.connect(path)

def setup_user_db():
    conn = create_connection(USER_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )""")
    conn.commit()
    conn.close()

def setup_vaccine_db():
    conn = create_connection(DB_FILE)
    conn.execute("""CREATE TABLE IF NOT EXISTS vaccination_data (
        STATE TEXT, CITY TEXT, AGE_GROUP TEXT, GENDER TEXT,
        ETHNICITY TEXT, VACCINATED BOOLEAN, Year INTEGER, DESCRIPTION TEXT
    )""")
    conn.commit()
    conn.close()

def is_data_present():
    conn = create_connection(DB_FILE)
    count = conn.execute("SELECT COUNT(*) FROM vaccination_data").fetchone()[0]
    conn.close()
    return count > 0

def load_data():
    if not is_data_present():
        try:
            df = pd.read_csv(sheet_url)
            conn = create_connection(DB_FILE)
            df.to_sql("vaccination_data", conn, if_exists="replace", index=False)
            conn.close()
            print("✅ Data loaded to DB")
        except Exception as e:
            print("❌ Failed to load Google Sheet:", e)

setup_user_db()
setup_vaccine_db()
load_data()

# ----------------- AUTHENTICATION -----------------
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def user_exists(username):
    conn = create_connection(USER_DB)
    res = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return res

def add_user(username, pw):
    conn = create_connection(USER_DB)
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_pw(pw)))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def authenticate(username, pw):
    conn = create_connection(USER_DB)
    stored_pw = conn.execute("SELECT password FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return stored_pw and stored_pw[0] == hash_pw(pw)

# ----------------- LOGIN / SIGNUP -----------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "signup" not in st.session_state:
    st.session_state["signup"] = False

def login():
    st.title("🔐 Login")
    u, p = st.text_input("Username"), st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(u, p):
            st.session_state["authenticated"] = True
            st.session_state["username"] = u
            st.rerun()
        else:
            st.error("Invalid credentials.")
    if st.button("Sign Up"):
        st.session_state["signup"] = True
        st.rerun()

def signup():
    st.title("📝 Sign Up")
    u, p, cp = st.text_input("Username"), st.text_input("Password", type="password"), st.text_input("Confirm", type="password")
    if st.button("Register"):
        if p != cp:
            st.error("Passwords do not match.")
        elif user_exists(u):
            st.error("Username exists.")
        elif add_user(u, p):
            st.success("Registered! Please log in.")
            st.session_state["signup"] = False
            st.rerun()
        else:
            st.error("Registration failed.")
    if st.button("Back to Login"):
        st.session_state["signup"] = False
        st.rerun()

if not st.session_state["authenticated"]:
    if st.session_state["signup"]:
        signup()
    else:
        login()
    st.stop()

# ----------------- DASHBOARD -----------------
st.title("📊 Vaccination Dashboard")

if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

conn = create_connection(DB_FILE)
df = pd.read_sql("SELECT * FROM vaccination_data", conn)
conn.close()

st.write("### 🧾 Raw Data")
st.dataframe(df.head())

# ----------------- FILTERING -----------------
st.sidebar.header("Filter")
state = st.sidebar.selectbox("State", df["STATE"].dropna().unique())
city = st.sidebar.selectbox("City", df[df["STATE"] == state]["CITY"].dropna().unique())
vaccine = st.sidebar.multiselect("Vaccine Type", df["DESCRIPTION"].dropna().unique())

filtered_df = df[(df["STATE"] == state) & (df["CITY"] == city) & (df["DESCRIPTION"].isin(vaccine))]
st.write(f"## Data for {city}, {state}")
st.dataframe(filtered_df)

# ----------------- MAP -----------------
map_data = filtered_df[["LAT", "LON"]].dropna().rename(columns={"LAT": "lat", "LON": "lon"})
if not map_data.empty:
    st.write("### 🗺 Map")
    st.map(map_data)
else:
    st.warning("No coordinates to display.")

# ----------------- METRICS -----------------
total_vax = filtered_df[filtered_df["VACCINATED"] == 1].shape[0]
total_non = filtered_df[filtered_df["VACCINATED"] == 0].shape[0]
total = total_vax + total_non
col1, col2, col3 = st.columns(3)
col1.metric("✅ Vaccinated", total_vax)
col2.metric("❌ Non-Vaccinated", total_non)
col3.metric("📊 Total", total)

# ----------------- CHARTS -----------------
st.write("### 📊 Vaccination Comparison")
vax_df = filtered_df[filtered_df["VACCINATED"] == 1]
non_df = filtered_df[filtered_df["VACCINATED"] == 0]

col1, col2 = st.columns(2)
col1.plotly_chart(px.pie(vax_df, names="ETHNICITY", title="Vaccinated by Ethnicity"))
col2.plotly_chart(px.pie(non_df, names="ETHNICITY", title="Non-Vaccinated by Ethnicity"))

# ----------------- FORECAST -----------------
st.write("### 🔮 Forecast")
try:
    full_df = pd.read_csv(sheet_url)
    full_df["VACCINATED"] = full_df["VACCINATED"].astype(str).str.lower().map({"true": 1, "false": 0})
    vax_full = full_df[full_df["VACCINATED"] == 1]
    yearly = vax_full.groupby("YEAR").size().reset_index(name="vaccinated_count")
    model = ARIMA(yearly["vaccinated_count"], order=(1, 1, 1)).fit()
    future = model.forecast(steps=5)
    years = list(range(int(yearly["YEAR"].max()) + 1, int(yearly["YEAR"].max()) + 6))
    forecast_df = pd.DataFrame({"YEAR": years, "vaccinated_count": future})
    combined = pd.concat([yearly, forecast_df])
    st.plotly_chart(px.line(combined, x="YEAR", y="vaccinated_count", markers=True, title="5-Year Forecast"))
except Exception as e:
    st.warning(f"Forecast failed: {e}")

# ----------------- REAL-TIME COMPARISON -----------------
st.write("### 📡 Synthea vs Real-Time Census Data")
if os.path.exists(census_filename):
    realtime_df = pd.read_csv(census_filename)
    full = realtime_df["fully_vaccinated"].replace(np.nan, 0).sum()
    partial = realtime_df["partially_vaccinated"].replace(np.nan, 0).sum()
    real_total = full + partial
else:
    st.warning("Census file missing.")
    real_total = 0

compare_df = pd.DataFrame({
    "Dataset": ["Synthea", "Census"],
    "Vaccinated": [total_vax, real_total]
})
st.plotly_chart(px.bar(compare_df, x="Dataset", y="Vaccinated", text_auto=True))


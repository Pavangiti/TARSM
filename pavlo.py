import pandas as pd
import requests
import sqlite3
import streamlit as st
import urllib.parse
from io import StringIO, BytesIO
from geopy.geocoders import Nominatim
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# ----------------- DATABASE & FILE PATH SETUP -----------------
DB_FILE = "vaccination_data.db"
USER_DB = "users.db"

# ----------------- GOOGLE DRIVE FILE IDS -----------------
# File 1: Google Sheet
sheet_id = "1hJEb7aMjrD-EfAoN9jdhwBK2m9o0U-mh"
sheet_name = "not_vaccinated_analysis (3)"
encoded_sheet_name = urllib.parse.quote(sheet_name)
DATASET_URL_1 = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"

# File 2: Public CSV from Google Drive
file_id_2 = "1Fswh6Eq_wrsf5FbpaaUve9K0KOZ6q3zg"
DATASET_URL_2 = f"https://drive.google.com/uc?id={file_id_2}"

# File 3: GeoJSON file from Google Drive (used for mapping only)
file_id_3 = "1gnux_uKipCE4f-hiThO7c_WHF8kx8nh8"
GEOJSON_URL = f"https://drive.google.com/uc?id={file_id_3}"


# Load the Google Sheet into a DataFrame
try:
    df = pd.read_csv(DATASET_URL_1)
    st.success("Dataset loaded successfully from Google Sheets.")
except Exception as e:
    st.error(f"Error loading dataset: {e}")
    df = pd.DataFrame()  # fallback to empty DataFrame
# Function to create database connection
def create_connection(db_path):
    return sqlite3.connect(db_path)

# Function to create user database
def setup_user_database():
    conn = create_connection(USER_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT
                      )''')
    conn.commit()
    conn.close()

# Function to create vaccination database
def setup_vaccination_database():
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS vaccination_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        STATE TEXT,
                        CITY TEXT,
                        AGE_GROUP TEXT,
                        GENDER TEXT,
                        ETHNICITY TEXT,
                        VACCINATED BOOLEAN,
                        Year INTEGER,
                        DESCRIPTION TEXT
                      )''')
    conn.commit()
    conn.close()

# Function to check if data exists in the table
def is_data_present():
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vaccination_data")
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# Function to load dataset into the database (only if empty)
def load_data_into_db():
    if not is_data_present():
        try:
            df = pd.read_csv(DATASET_URL)  # Load directly from Google Sheets
            conn = create_connection(DB_FILE)
            df.to_sql("vaccination_data", conn, if_exists="replace", index=False)
            conn.close()
            print("✅ Data loaded into the database successfully!")
        except Exception as e:
            print(f"❌ Error loading dataset: {e}")


# Initialize databases
setup_user_database()
setup_vaccination_database()
load_data_into_db()



















# ----------------- FUNCTION TO LOAD CSV FILES -----------------
def load_csv_from_url(url, label):
    try:
        response = requests.get(url)
        df = pd.read_csv(StringIO(response.text))
        st.success(f"{label} loaded successfully.")
        return df
    except Exception as e:
        st.error(f"Error loading {label}: {e}")
        return pd.DataFrame()

# ----------------- LOAD DATASETS -----------------
df1 = load_csv_from_url(DATASET_URL_1, "Google Sheet Data")
df2 = load_csv_from_url(DATASET_URL_2, "Drive File 2")
# Note: DO NOT LOAD df3 here — it's used only as GeoJSON in map section

# ----------------- DATABASE FUNCTIONS -----------------
def create_connection(db_path):
    return sqlite3.connect(db_path)

def setup_user_database():
    conn = create_connection(USER_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT
                      )''')
    conn.commit()
    conn.close()

def setup_vaccination_database():
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS vaccination_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        STATE TEXT,
                        CITY TEXT,
                        AGE_GROUP TEXT,
                        GENDER TEXT,
                        ETHNICITY TEXT,
                        VACCINATED BOOLEAN,
                        Year INTEGER,
                        DESCRIPTION TEXT
                      )''')
    conn.commit()
    conn.close()

def is_data_present():
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vaccination_data")
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# ----------------- MAP & SUMMARY SECTION -----------------
st.header("🗺 City Map Viewer")

city = st.text_input("Enter City Name", "Los Angeles")
state = st.text_input("Enter State Name", "California")

try:
    # Load GeoJSON from Google Drive
    response = requests.get(GEOJSON_URL)
    if response.status_code != 200:
        raise Exception("Failed to download GeoJSON from Google Drive")

    geojson_bytes = BytesIO(response.content)
    city_gdf = gpd.read_file(geojson_bytes)

    # Filter for selected city
    selected_city_boundary = city_gdf[city_gdf["CITY"].str.lower() == city.lower()]

    if not selected_city_boundary.empty:
        # Use representative point as map center
        city_center = selected_city_boundary.geometry.representative_point().iloc[0].coords[0][::-1]

        # Create Folium map
        m = folium.Map(location=city_center, zoom_start=11)

        # Add city outline
        folium.GeoJson(
            selected_city_boundary.geometry,
            style_function=lambda x: {
                "fillOpacity": 0,
                "color": "blue",
                "weight": 3
            }
        ).add_to(m)

        st.write(f"### 🗺 City Outline for {city.title()}")
        st_folium(m, width=800, height=500)
    else:
        st.warning(f"City '{city}' not found in the GeoJSON file.")

except Exception as e:
    st.error(f"Map rendering failed: {e}")

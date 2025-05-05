import pandas as pd
import sqlite3
import urllib.parse
import streamlit as st
import requests
from io import StringIO

# ----------------- DATABASE & FILE PATH SETUP -----------------
DB_FILE = "vaccination_data.db"
USER_DB = "users.db"

# ----------------- GOOGLE DRIVE LINKS -----------------

# 1. Google Sheet (Public, CSV Export)
sheet_id = "1hJEb7aMjrD-EfAoN9jdhwBK2m9o0U-mh"
sheet_name = "not_vaccinated_analysis (3)"
encoded_sheet_name = urllib.parse.quote(sheet_name)
DATASET_URL_1 = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"

# 2. Public CSV from Google Drive
file_id_2 = "1Fswh6Eq_wrsf5FbpaaUve9K0KOZ6q3zg"
DATASET_URL_2 = f"https://drive.google.com/uc?id={file_id_2}"

# 3. Another Public CSV from Google Drive
file_id_3 = "1gnux_uKipCE4f-hiThO7c_WHF8kx8nh8"
DATASET_URL_3 = f"https://drive.google.com/uc?id={file_id_3}"

# ----------------- LOAD DATASETS -----------------

def load_csv_from_url(url, label):
    try:
        response = requests.get(url)
        df = pd.read_csv(StringIO(response.text))
        st.success(f"{label} loaded successfully.")
        return df
    except Exception as e:
        st.error(f"Error loading {label}: {e}")
        return pd.DataFrame()

# Load all three datasets
df1 = load_csv_from_url(DATASET_URL_1, "Google Sheet Data")
df2 = load_csv_from_url(DATASET_URL_2, "Drive File 2")
df3 = load_csv_from_url(DATASET_URL_3, "Drive File 3")

# ----------------- DATABASE FUNCTIONS -----------------

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

# Function to check if data exists in the table (placeholder)
def is_data_present():
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vaccination_data")
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px

# --- הגדרות וחיבורים ---
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# בדיקה שהמפתחות קיימים למניעת קריסה
if not url or not key:
    st.error("Missing Supabase Credentials. Please check your Secrets/Env.")
    st.stop()

supabase: Client = create_client(url, key)

# הגדרות דף רחב ומצב כהה
st.set_page_config(page_title="TurtleSoup Pro Hub", layout="wide", initial_sidebar_state="collapsed")

# --- עיצוב CSS מתקדם לממשק מקצועי ---
st.markdown("""
    <style>
    /* רקע כללי */
    .main { background-color: #0e1117; }
    
    /* עיצוב ריבועי לוח השנה */
    .calendar-day {
        height: 90px;
        border-radius: 8px;
        padding: 8px;
        margin: 2px;
        text-align: right;
        color: white;
        font-family: sans-serif;
    }
    .win-day { 
        background-color: #1b5e20; 
        border: 1px solid #00ffcc; 
        box-shadow: 0px 0px 5px rgba(0, 255, 204, 0.3);
    }
    .loss-day { 
        background-color: #b71c1c; 
        border: 1px solid #ff4b4b;
        box-shadow: 0px 0px 5px rgba(255, 75, 75, 0.3);
    }
    .neutral-day { 
        background-color: #1e2130; 
        border: 1px solid #3e4255;
    }
    
    /* עיצוב מטריקות */
    div[data-testid="stMetric"] {
        background-color: #1e2130;
        border: 1px solid #3e4255;
        padding: 15px;
        border-radius: 12px;
    }
    
    /* כותרות */
    h1, h2, h3 { color: #00ffcc !important; font-family: 'Segoe UI', sans-serif; }
    
    /* טפסים */
    .stForm {
        background-color: #1e2130;
        border-radius: 15px;
        border: 1px solid #3e4255;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- פונקציות שליפת נתונים ---
@st.cache_data(ttl=10)
def fetch_data():
    try:
        res = supabase.table("turtle_soup_journal").select("*").order("trade_date", desc=True).execute()
        temp_df = pd.DataFrame(res.data)
        if not temp_df.empty:
            temp_df['trade_date'] = pd.to_datetime(temp_df['trade_date'])
            temp_df['date_only'] = temp_df['trade_date'].dt.date
        return temp_df
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return pd.DataFrame()

df = fetch_data()

import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px

# --- 1. טעינת הגדרות ואבטחה ---
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# פונקציית חיבור יציבה
@st.cache_resource
def get_supabase():
    if not url or not key:
        return None
    return create_client(url, key)

supabase = get_supabase()

# --- 2. הגדרות תצוגה ---
st.set_page_config(page_title="TurtleSoup Pro Hub", layout="wide")

st.markdown("""
    <style>
    .calendar-day { height: 80px; border-radius: 8px; padding: 10px; margin: 2px; text-align: center; color: white; }
    .win-day { background-color: #1b5e20; border: 1px solid #00ffcc; }
    .loss-day { background-color: #b71c1c; border: 1px solid #ff4b4b; }
    .neutral-day { background-color: #1e2130; border: 1px solid #3e4255; }
    div[data-testid="stMetric"] { background-color: #1e2130; border: 1px solid #3e4255; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. לוגיקת נתונים ---
def fetch_data():
    if not supabase:
        return pd.DataFrame()
    try:
        res = supabase.table("turtle_soup_journal").select("*").execute()
        if res.data:
            temp_df = pd.DataFrame(res.data)
            temp_df['trade_date'] = pd.to_datetime(temp_df['trade_date'])
            temp_df['date_only'] = temp_df['trade_date'].dt.date
            return temp_df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"שגיאה במשיכת נתונים: {e}")
        return pd.DataFrame()

# טעינת הנתונים
df = fetch_data()

# --- 4. בניית הממשק ---
st.title("🐢 TurtleSoup Ultimate Trading Hub")

if not supabase:
    st.warning("⚠️ המפתחות ל-Supabase חסרים ב-Secrets. המערכת לא יכולה להתחבר.")
    st.stop()

# שורה עליונה: סטטיסטיקה וגרף
col1, col2 = st.columns([1, 2])

with col1:
    if not df.empty:
        total_pnl = df['pnl'].sum()
        wr = (len(df[df['pnl'] > 0]) / len(df)) * 100
        st.metric("Total Net PNL", f"${total_pnl:,.2f}")
        st.metric("Win Rate", f"{wr:.1f}%")
        st.metric("Trades", len(df))
    else:
        st.info("ממתין לעסקה הראשונה שלך...")

with col2:
    if not df.empty:
        df_sorted = df.sort_values('trade_date')
        df_sorted['cum_pnl'] = df_sorted['pnl'].cumsum()
        fig = px.area(df_sorted, x='trade_date', y='cum_pnl', title="Equity Curve")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=300)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# שורה אמצעית: לוח שנה וטופס
c_cal, c_form = st.columns([2, 1])

with c_cal:
    st.subheader("📅 Trading Calendar")
    now = datetime.now()
    cal = calendar.monthcalendar(now.year, now.month)
    
    # כותרות ימים
    cols = st.columns(7)
    for i, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        cols[i].write(f"**{day_name}**")
    
    # ציור הריבועים
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                date_obj = datetime(now.year, now.month, day).date()
                day_trades = df[df['date_only'] == date_obj] if not df.empty else pd.DataFrame()
                day_pnl = day_trades['pnl'].sum() if not day_trades.empty else 0
                
                status = "neutral-day"
                if not day_trades.empty:
                    status = "win-day" if day_pnl >= 0 else "loss-day"
                
                cols[i].markdown(f"""
                    <div class="calendar-day {status}">
                        <div style="font-size: 10px;">{day}</div>
                        <div style="font-size: 14px;">${day_pnl:.0f}</div>
                    </div>
                    """, unsafe_allow_html=True)

with c_form:
    st.subheader("➕ New Entry")
    with st.form("main_form"):
        new_pnl = st.number_input("PNL ($)", step=10.0)
        new_date = st.date_input("Date", datetime.now())
        new_notes = st.text_input("Notes")
        
        # Checkboxes לאישורים
        st.write("Confirmations:")
        c_a, c_b = st.columns(2)
        f_ts = c_a.checkbox("Turtle Soup")
        f_liq = c_b.checkbox("Liquidity")
        
        submitted = st.form_submit_button("Save Trade")
        
        if submitted:
            trade_to_save = {
                "pnl": new_pnl,
                "trade_date": str(new_date),
                "notes": new_notes,
                "liquidity_taken": f_liq,
                "tp_points": 0,
                "stop_points": 0
            }
            try:
                supabase.table("turtle_soup_journal").insert(trade_to_save).execute()
                st.success("נשמר!")
                # שימוש בשיטה בטוחה יותר לרענון
                st.info("מרענן נתונים... לחץ F5 אם לא התעדכן")
            except Exception as e:
                st.error(f"שגיאה בשמירה: {e}")

# שורה תחתונה: טבלת עסקאות
st.markdown("---")
st.subheader("📜 Recent Trades")
if not df.empty:
    st.table(df[['trade_date', 'pnl', 'notes']].head(10))

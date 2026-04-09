import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os
from supabase import create_client, Client
import plotly.express as px

# ==========================================
# 1. הגדרות תצוגה ראשוניות (חייב להיות בהתחלה)
# ==========================================
st.set_page_config(page_title="TurtleSoup Ultimate Hub", layout="wide")

# CSS מתקדם
st.markdown("""
    <style>
    .calendar-day { height: 90px; border-radius: 8px; padding: 10px; margin: 3px; text-align: center; color: white; display: flex; flex-direction: column; justify-content: space-between; }
    .win-day { background-color: #1b5e20; border: 1px solid #00ffcc; box-shadow: 0px 0px 5px rgba(0, 255, 204, 0.2); }
    .loss-day { background-color: #b71c1c; border: 1px solid #ff4b4b; box-shadow: 0px 0px 5px rgba(255, 75, 75, 0.2); }
    .neutral-day { background-color: #1e2130; border: 1px solid #3e4255; }
    div[data-testid="stMetric"] { background-color: #1e2130; border: 1px solid #3e4255; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. חיבור מאובטח ל-Supabase
# ==========================================
@st.cache_resource
def init_connection():
    # ניסיון למשוך מפתחות מ-Streamlit Cloud Secrets
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        # פולבק (Fallback) לסביבה המקומית
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        return None
    return create_client(url, key)

supabase = init_connection()

if not supabase:
    st.error("⚠️ מפתחות ההתחברות ל-Supabase חסרים! אנא ודא שהם מוגדרים ב-Settings -> Secrets.")
    st.stop()

# ==========================================
# 3. משיכת נתונים עם חגורת בטיחות
# ==========================================
def fetch_data():
    try:
        res = supabase.table("turtle_soup_journal").select("*").execute()
        df = pd.DataFrame(res.data)
        
        # בניית עמודות גם אם הטבלה ריקה כדי למנוע קריסות
        expected_cols = ['id', 'pnl', 'trade_date', 'notes', 'liquidity_taken']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
                
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df['date_only'] = df['trade_date'].dt.date
            df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"⚠️ שגיאה במשיכת הנתונים (בדוק אם הטבלה קיימת ב-Supabase): {e}")
        return pd.DataFrame()

df = fetch_data()

# ==========================================
# 4. בניית הממשק (Dashboard)
# ==========================================
st.title("🐢 TurtleSoup Ultimate Trading Hub")

# --- שורה עליונה: מטריקות וגרף ---
col_stats, col_graph = st.columns([1, 2.5])

with col_stats:
    total_pnl = df['pnl'].sum() if not df.empty else 0
    total_trades = len(df) if not df.empty else 0
    wins = len(df[df['pnl'] > 0]) if not df.empty else 0
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    
    st.metric("Total Net PNL", f"${total_pnl:,.2f}")
    st.metric("Win Rate", f"{win_rate:.1f}%")
    st.metric("Total Trades", total_trades)

with col_graph:
    if not df.empty and total_trades > 0:
        df_sorted = df.sort_values('trade_date')
        df_sorted['cum_pnl'] = df_sorted['pnl'].cumsum()
        fig = px.area(df_sorted, x='trade_date', y='cum_pnl', title="Equity Curve (Growth)")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=300, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 הגרף יופיע כאן לאחר שתזין את העסקה הראשונה.")

st.markdown("---")

# --- שורה אמצעית: לוח שנה (Calendar) וטופס הזנה ---
col_cal, col_form = st.columns([2, 1])

with col_cal:
    st.subheader("📅 Trading Calendar")
    now = datetime.now()
    curr_year, curr_month = now.year, now.month
    
    cal = calendar.monthcalendar(curr_year, curr_month)
    month_name = calendar.month_name[curr_month]
    st.write(f"**{month_name} {curr_year}**")
    
    # כותרות ימי השבוע
    days_cols = st.columns(7)
    for i, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        days_cols[i].markdown(f"<div style='text-align: center; font-size: 14px; color: #aaa;'>{day}</div>", unsafe_allow_html=True)
    
    # בניית הריבועים
    for week in cal:
        week_cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                week_cols[i].write("") # מקום ריק בתחילת/סוף חודש
            else:
                date_obj = datetime(curr_year, curr_month, day).date()
                day_trades = df[df['date_only'] == date_obj] if not df.empty else pd.DataFrame()
                
                day_pnl = day_trades['pnl'].sum() if not day_trades.empty else 0
                trade_count = len(day_trades)
                
                # צבע הריבוע
                box_class = "neutral-day"
                if trade_count > 0:
                    box_class = "win-day" if day_pnl >= 0 else "loss-day"
                
                # עיצוב הריבוע
                week_cols[i].markdown(f"""
                    <div class="calendar-day {box_class}">
                        <div style="font-size: 12px; font-weight: bold; opacity: 0.8;">{day}</div>
                        <div style="font-size: 16px; font-weight: bold;">${day_pnl:,.0f}</div>
                        <div style="font-size: 10px; opacity: 0.8;">{trade_count} Trades</div>
                    </div>
                """, unsafe_allow_html=True)

with col_form:
    st.subheader("➕ Quick Log")
    with st.form("trade_form", clear_on_submit=True):
        f_pnl = st.number_input("PNL ($)", step=10.0, format="%.2f")
        f_date = st.date_input("Trade Date", datetime.now())
        f_notes = st.text_input("Quick Notes")
        
        st.write("Confirmations:")
        c1, c2 = st.columns(2)
        f_ts = c1.checkbox("Turtle Soup")
        f_liq = c2.checkbox("Liquidity")
        
        submitted = st.form_submit_button("LOCK TRADE 🔒")
        
        if submitted:
            new_trade = {
                "pnl": float(f_pnl),
                "trade_date": str(f_date),
                "notes": f_notes,
                "liquidity_taken": f_liq,
                "stop_points": 0,
                "tp_points": 0
            }
            try:
                supabase.table("turtle_soup_journal").insert(new_trade).execute()
                st.success("Trade Recorded!")
                st.rerun() # ריענון הדף אוטומטית כדי שהקלנדר יתעדכן
            except Exception as e:
                st.error(f"❌ Error saving trade: {e}")

# --- שורה תחתונה: היסטוריית עסקאות ---
st.markdown("---")
st.subheader("📜 Recent Records")
if not df.empty and total_trades > 0:
    # הצגת טבלה מסודרת של העסקאות האחרונות מהחדש לישן
    display_df = df.sort_values('trade_date', ascending=False)[['trade_date', 'pnl', 'notes']].head(10)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.write("אין עדיין עסקאות להצגה.")

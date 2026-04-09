import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os
from supabase import create_client, Client
import plotly.express as px

# --- 1. הגדרות תצוגה ---
st.set_page_config(page_title="TurtleSoup Pro Journal", layout="wide")

# CSS לעיצוב פרימיום וקריאות מקסימלית
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    /* מטריקות - אנליזה */
    div[data-testid="stMetric"] { 
        background-color: #1e2130; 
        border: 1px solid #3e4255; 
        padding: 20px; 
        border-radius: 12px; 
    }
    div[data-testid="stMetricLabel"] > div { color: #00ffcc !important; font-weight: bold; }
    div[data-testid="stMetricValue"] > div { color: white !important; }

    /* לוח שנה */
    .calendar-day { 
        height: 110px; border-radius: 10px; padding: 10px; margin: 4px; 
        display: flex; flex-direction: column; justify-content: space-between;
        color: white !important; transition: transform 0.2s;
    }
    .calendar-day:hover { transform: scale(1.02); }
    .win-day { background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%); border: 1px solid #00ffcc; }
    .loss-day { background: linear-gradient(135deg, #b71c1c 0%, #c62828 100%); border: 1px solid #ff4b4b; }
    .neutral-day { background-color: #1e2130; border: 1px solid #3e4255; }
    
    .cal-date { font-size: 14px; font-weight: bold; opacity: 0.6; }
    .cal-pnl { font-size: 18px; font-weight: 900; text-align: center; }
    .cal-info { font-size: 10px; text-align: center; opacity: 0.8; }

    /* כפתור שמירה */
    .stButton>button { width: 100%; background-color: #00ffcc; color: black; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור ל-Supabase ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        st.error("חיבור ל-Supabase נכשל. בדוק את ה-Secrets.")
        return None

supabase = init_connection()

# --- 3. לוגיקת נתונים ---
def fetch_data():
    if not supabase: return pd.DataFrame()
    res = supabase.table("turtle_soup_journal").select("*").order("trade_date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['date_only'] = df['trade_date'].dt.date
        df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0)
    return df

df = fetch_data()

# --- 4. ממשק משתמש (UI) ---
st.title("🛡️ TurtleSoup Ultimate Journal")

# שורה 1: אנליזה מצטברת
st.subheader("📊 Performance Analytics")
col_a1, col_a2, col_a3, col_a4 = st.columns(4)

if not df.empty:
    total_pnl = df['pnl'].sum()
    win_rate = (len(df[df['pnl'] > 0]) / len(df)) * 100
    avg_tp = df['tp_points'].mean()
    avg_sl = df['stop_points'].mean()
    
    col_a1.metric("Net Profit", f"${total_pnl:,.2f}")
    col_a2.metric("Win Rate", f"{win_rate:.1f}%")
    col_a3.metric("Avg TP Points", f"{avg_tp:.1f}")
    col_a4.metric("Avg SL Points", f"{avg_sl:.1f}")

st.markdown("---")

# שורה 2: לוח שנה והזנה
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📅 Trading Calendar")
    now = datetime.now()
    curr_year, curr_month = now.year, now.month
    
    cal = calendar.monthcalendar(curr_year, curr_month)
    month_name = calendar.month_name[curr_month]
    st.write(f"### {month_name} {curr_year}")
    
    # כותרות ימים
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    header_cols = st.columns(7)
    for i, d in enumerate(day_names): header_cols[i].markdown(f"<center><b>{d}</b></center>", unsafe_allow_html=True)
    
    for week in cal:
        week_cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0: week_cols[i].write("")
            else:
                date_obj = datetime(curr_year, curr_month, day).date()
                day_data = df[df['date_only'] == date_obj] if not df.empty else pd.DataFrame()
                day_pnl = day_data['pnl'].sum() if not day_data.empty else 0
                trades_count = len(day_data)
                
                box_color = "neutral-day"
                if trades_count > 0:
                    box_color = "win-day" if day_pnl >= 0 else "loss-day"
                
                week_cols[i].markdown(f"""
                    <div class="calendar-day {box_color}">
                        <div class="cal-date">{day}</div>
                        <div class="cal-pnl">${day_pnl:,.0f}</div>
                        <div class="cal-info">{trades_count} Trades</div>
                    </div>
                """, unsafe_allow_html=True)

    # גרף Equity מתחת ללוח השנה
    if not df.empty:
        df_sorted = df.sort_values('trade_date')
        df_sorted['cum_pnl'] = df_sorted['pnl'].cumsum()
        fig = px.line(df_sorted, x='trade_date', y='cum_pnl', title="Lifetime Equity Curve", template="plotly_dark")
        fig.update_traces(line_color='#00ffcc')
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("➕ Log Trade")
    with st.form("trade_entry", clear_on_submit=True):
        f_date = st.date_input("Trade Date", datetime.now())
        f_pnl = st.number_input("PNL ($)", step=10.0)
        
        c1, c2 = st.columns(2)
        f_sl = c1.number_input("Stop Points", step=1.0)
        f_tp = c2.number_input("TP Points", step=1.0)
        
        st.write("🛡️ **Confirmations**")
        cb1, cb2 = st.columns(2)
        c_ts = cb1.checkbox("Turtle Soup")
        c_1m = cb1.checkbox("1m IFVG")
        c_3m = cb1.checkbox("3m IFVG")
        c_5m = cb1.checkbox("5m IFVG")
        c_li = cb1.checkbox("Liquidity Taken")
        
        c_pr = cb2.checkbox("Premium")
        c_di = cb2.checkbox("Discount")
        c_pb = cb2.checkbox("Entry at Pullback")
        c_ote = cb2.checkbox("OTE")
        c_05 = cb2.checkbox("0.5 Range")
        
        f_htf = st.text_input("HTF PD Array (e.g., Daily FVG)")
        f_emo = st.selectbox("Emotion", ["Neutral", "Confident", "Greedy", "Fearful", "Revenge"])
        f_notes = st.text_area("Notes & Lessons")
        
        # העלאת תמונה
        f_img = st.file_uploader("Upload Screenshot", type=['png', 'jpg', 'jpeg'])
        
        submit = st.form_submit_button("SAVE TRADE 🔒")
        
        if submit:
            # איסוף ה-Checkboxes
            confs = [k for k, v in {"Turtle Soup": c_ts, "1m IFVG": c_1m, "3m IFVG": c_3m, "5m IFVG": c_5m, 
                                    "Liquidity": c_li, "Premium": c_pr, "Discount": c_di, 
                                    "Pullback": c_pb, "OTE": c_ote, "0.5 Range": c_05}.items() if v]
            
            new_data = {
                "trade_date": str(f_date),
                "pnl": f_pnl,
                "stop_points": f_sl,
                "tp_points": f_tp,
                "confirmations": ", ".join(confs),
                "htf_pd_array": f_htf,
                "emotion": f_emo,
                "notes": f_notes,
                "image_url": "" # כאן אפשר להוסיף לוגיקת העלאה ל-S3/Supabase Storage
            }
            
            try:
                supabase.table("turtle_soup_journal").insert(new_data).execute()
                st.success("Trade Recorded!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# שורה 3: היסטוריה מפורטת
st.markdown("---")
st.subheader("📜 Recent History")
if not df.empty:
    st.dataframe(df[['trade_date', 'pnl', 'stop_points', 'tp_points', 'emotion', 'confirmations', 'notes']], 
                 use_container_width=True, hide_index=True)

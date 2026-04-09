import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px

# הגדרות חיבור
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

st.set_page_config(page_title="TurtleSoup Ultimate Hub", layout="wide")

# עיצוב מותאם אישית ללוח שנה ולכרטיסיות
st.markdown("""
    <style>
    .calendar-day {
        height: 100px;
        border-radius: 10px;
        padding: 10px;
        margin: 5px;
        text-align: center;
        color: white;
        font-weight: bold;
        border: 1px solid #3e4255;
    }
    .win-day { background-color: #1b5e20; border: 1px solid #00ffcc; }
    .loss-day { background-color: #b71c1c; border: 1px solid #ff4b4b; }
    .neutral-day { background-color: #1e2130; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4255; }
    </style>
    """, unsafe_allow_html=True)

# --- שליפת נתונים ---
def fetch_all_data():
    res = supabase.table("turtle_soup_journal").select("*").order("trade_date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['date_only'] = df['trade_date'].dt.date
    return df

df = fetch_all_data()

# --- כותרת ראשית ---
st.title("🛡️ TurtleSoup Ultimate Trading Hub")

# --- שורה ראשונה: מטריקות וגרף ---
col_stats, col_graph = st.columns([1, 2])

with col_stats:
    if not df.empty:
        total_pnl = df['pnl'].sum()
        wr = (len(df[df['pnl'] > 0]) / len(df)) * 100
        st.metric("Total Net PNL", f"${total_pnl:,.2f}")
        st.metric("Win Rate", f"{wr:.1f}%")
        st.metric("Total Trades", len(df))
    else:
        st.write("ממתין לנתונים...")

with col_graph:
    if not df.empty:
        df_sorted = df.sort_values('trade_date')
        df_sorted['cum_pnl'] = df_sorted['pnl'].cumsum()
        fig = px.area(df_sorted, x='trade_date', y='cum_pnl', title="Equity Curve", height=300)
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --- שורה שנייה: לוח שנה והזנה ---
col_cal, col_input = st.columns([2, 1])

with col_cal:
    st.subheader("📅 Trading Calendar")
    
    # חישוב ימי החודש הנוכחי
    today = datetime.now()
    curr_month = today.month
    curr_year = today.year
    
    cal = calendar.monthcalendar(curr_year, curr_month)
    month_name = calendar.month_name[curr_month]
    
    st.write(f"### {month_name} {curr_year}")
    
    # יצירת לוח השנה בריבועים
    cols = st.columns(7)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, day_name in enumerate(days):
        cols[i].write(f"**{day_name}**")

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("") # יום ריק
            else:
                date_obj = datetime(curr_year, curr_month, day).date()
                day_trades = df[df['date_only'] == date_obj] if not df.empty else pd.DataFrame()
                
                day_pnl = day_trades['pnl'].sum() if not day_trades.empty else 0
                num_trades = len(day_trades)
                
                # קביעת צבע לפי רווח/הפסד
                status_class = "neutral-day"
                if num_trades > 0:
                    status_class = "win-day" if day_pnl >= 0 else "loss-day"
                
                content = f"""
                <div class="calendar-day {status_class}">
                    <div style="font-size: 12px;">{day}</div>
                    <div style="font-size: 14px;">${day_pnl:.0f}</div>
                    <div style="font-size: 10px;">{num_trades} Trades</div>
                </div>
                """
                cols[i].markdown(content, unsafe_allow_html=True)

with col_input:
    st.subheader("➕ Quick Log")
    with st.form("quick_form", clear_on_submit=True):
        f_pnl = st.number_input("PNL ($)", step=10.0)
        f_stop = st.number_input("Stop Points", step=1.0)
        f_date = st.date_input("Date", datetime.now())
        
        st.write("Confirmations:")
        c1, c2 = st.columns(2)
        ts_check = c1.checkbox("Turtle Soup")
        ifvg_check = c1.checkbox("IFVG")
        liq_check = c2.checkbox("Liquidity")
        ote_check = c2.checkbox("OTE/0.5")
        
        f_notes = st.text_input("Notes")
        submit = st.form_submit_button("Save Trade")
        
        if submit:
            new_data = {
                "pnl": f_pnl, "stop_points": f_stop, "tp_points": 0,

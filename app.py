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

# CSS מתקדם - תיקון צבעי טקסט וריבועי קלנדר
st.markdown("""
    <style>
    /* עיצוב המטריקות (האנליזה) כך שהטקסט יהיה תמיד קריא */
    div[data-testid="stMetric"] { 
        background-color: #1e2130; 
        border: 1px solid #3e4255; 
        padding: 15px; 
        border-radius: 10px; 
    }
    div[data-testid="stMetricLabel"] > div { color: #00ffcc !important; font-size: 16px !important; font-weight: bold; }
    div[data-testid="stMetricValue"] > div { color: white !important; font-size: 28px !important; }
    
    /* עיצוב ריבועי הקלנדר */
    .calendar-day { 
        height: 100px; 
        border-radius: 8px; 
        padding: 8px; 
        margin: 3px; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        color: white !important;
    }
    .win-day { background-color: #1b5e20; border: 1px solid #00ffcc; box-shadow: 0px 0px 5px rgba(0, 255, 204, 0.2); }
    .loss-day { background-color: #b71c1c; border: 1px solid #ff4b4b; box-shadow: 0px 0px 5px rgba(255, 75, 75, 0.2); }
    .neutral-day { background-color: #1e2130; border: 1px solid #3e4255; }
    
    /* תאריך בתוך הקלנדר */
    .cal-date { font-size: 18px; font-weight: bold; align-self: flex-start; opacity: 0.9; }
    .cal-pnl { font-size: 16px; font-weight: bold; text-align: center; }
    .cal-trades { font-size: 11px; opacity: 0.7; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. חיבור מאובטח ל-Supabase
# ==========================================
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
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
# 3. משיכת נתונים
# ==========================================
def fetch_data():
    try:
        res = supabase.table("turtle_soup_journal").select("*").execute()
        df = pd.DataFrame(res.data)
        
        expected_cols = ['id', 'pnl', 'trade_date', 'notes', 'emotion']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
                
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df['date_only'] = df['trade_date'].dt.date
            df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"⚠️ שגיאה במשיכת הנתונים: {e}")
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
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=250, margin=dict(l=0, r=0, t=30, b=0))
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
        days_cols[i].markdown(f"<div style='text-align: center; font-size: 14px; color: #aaa; font-weight: bold;'>{day}</div>", unsafe_allow_html=True)
    
    # בניית הריבועים
    for week in cal:
        week_cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                week_cols[i].write("") 
            else:
                date_obj = datetime(curr_year, curr_month, day).date()
                day_trades = df[df['date_only'] == date_obj] if not df.empty else pd.DataFrame()
                
                day_pnl = day_trades['pnl'].sum() if not day_trades.empty else 0
                trade_count = len(day_trades)
                
                box_class = "neutral-day"
                if trade_count > 0:
                    box_class = "win-day" if day_pnl >= 0 else "loss-day"
                
                week_cols[i].markdown(f"""
                    <div class="calendar-day {box_class}">
                        <div class="cal-date">{day}</div>
                        <div class="cal-pnl">${day_pnl:,.0f}</div>
                        <div class="cal-trades">{trade_count} Trades</div>
                    </div>
                """, unsafe_allow_html=True)

with col_form:
    st.subheader("➕ Quick Log")
    with st.form("trade_form", clear_on_submit=True):
        c_pnl, c_date = st.columns(2)
        f_pnl = c_pnl.number_input("PNL ($)", step=10.0, format="%.2f")
        f_date = c_date.date_input("Date", datetime.now())
        
        st.write("🔍 **Confirmations**")
        conf_cols = st.columns(3)
        f_ts = conf_cols[0].checkbox("Turtle Soup")
        f_ifvg = conf_cols[0].checkbox("IFVG")
        f_liq = conf_cols[1].checkbox("Liquidity")
        f_ote = conf_cols[1].checkbox("OTE / 0.5")
        f_prem = conf_cols[2].checkbox("Premium")
        f_pull = conf_cols[2].checkbox("Pullback")
        
        f_emotion = st.selectbox("How did you feel?", ["Neutral", "Confident", "Greedy", "Fearful", "Revenge"])
        f_notes = st.text_input("Notes / Lessons")
        
        submitted = st.form_submit_button("LOCK TRADE 🔒")
        
        if submitted:
            # איסוף הסימונים לתוך טקסט כדי למנוע קריסות של עמודות חסרות במסד הנתונים
            checked_items = []
            if f_ts: checked_items.append("Turtle Soup")
            if f_ifvg: checked_items.append("IFVG")
            if f_liq: checked_items.append("Liquidity")
            if f_ote: checked_items.append("OTE/0.5")
            if f_prem: checked_items.append("Premium")
            if f_pull: checked_items.append("Pullback")
            
            conf_string = " | ".join(checked_items) if checked_items else "No confirmations selected"
            final_notes = f"[{conf_string}] {f_notes}"
            
            new_trade = {
                "pnl": float(f_pnl),
                "trade_date": str(f_date),
                "emotion": f_emotion,
                "notes": final_notes
            }
            try:
                supabase.table("turtle_soup_journal").insert(new_trade).execute()
                st.success("Trade Recorded!")
                st.rerun() 
            except Exception as e:
                st.error(f"❌ Error saving trade: {e}")

# --- שורה תחתונה: היסטוריית עסקאות ---
st.markdown("---")
st.subheader("📜 Recent Records")
if not df.empty and total_trades > 0:
    display_df = df.sort_values('trade_date', ascending=False)[['trade_date', 'pnl', 'emotion', 'notes']].head(10)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.write("אין עדיין עסקאות להצגה.")

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go

# טעינת הגדרות
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# הגדרות דף ועיצוב (Dark Mode & Professional Layout)
st.set_page_config(page_title="TurtleSoup Pro Journal", layout="wide", initial_sidebar_state="expanded")

# CSS מותאם אישית למראה מודרני
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4255; }
    .trade-card { background-color: #1e2130; padding: 20px; border-radius: 15px; border-left: 5px solid #00ffcc; margin-bottom: 15px; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #00ffcc; color: black; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- פונקציות שליפת נתונים ---
@st.cache_data(ttl=60)
def fetch_data():
    res = supabase.table("turtle_soup_journal").select("*").order("trade_date", desc=True).execute()
    return pd.DataFrame(res.data)

df = fetch_data()

# --- תפריט צד ---
st.sidebar.title("🐢 TurtleSoup Pro")
page = st.sidebar.radio("ניווט", ["🏠 דף הבית ואנליזה", "📅 לוח שנה", "➕ הזנת עסקה", "📜 היסטוריית עסקאות"])

# --- 🏠 דף הבית ואנליזה ---
if page == "🏠 דף הבית ואנליזה":
    st.title("📊 Trading Performance Overview")
    
    if df.empty:
        st.info("היומן ריק. הכנס עסקה ראשונה כדי לראות נתונים.")
    else:
        # מטריקות עליונות
        total_pnl = df['pnl'].sum()
        win_rate = (len(df[df['pnl'] > 0]) / len(df)) * 100
        profit_factor = abs(df[df['pnl'] > 0]['pnl'].sum() / df[df['pnl'] < 0]['pnl'].sum()) if not df[df['pnl'] < 0].empty else 10.0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total PNL", f"${total_pnl:,.2f}", delta=f"{df.iloc[0]['pnl']:.2f}")
        c2.metric("Win Rate", f"{win_rate:.1f}%")
        c3.metric("Profit Factor", f"{profit_factor:.2f}")
        c4.metric("Total Trades", len(df))

        st.markdown("---")
        
        col_charts_1, col_charts_2 = st.columns([2, 1])
        
        with col_charts_1:
            # גרף צבירה מעוצב
            df_sorted = df.sort_values('trade_date')
            df_sorted['cum_pnl'] = df_sorted['pnl'].cumsum()
            fig_pnl = px.area(df_sorted, x='trade_date', y='cum_pnl', title="Equity Curve", color_discrete_sequence=['#00ffcc'])
            fig_pnl.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_pnl, use_container_width=True)

        with col_charts_2:
            # התפלגות רגשות
            fig_emotions = px.pie(df, names='emotion', title="Psychology Breakdown", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_emotions, use_container_width=True)

# --- 📅 לוח שנה ---
elif page == "📅 לוח שנה":
    st.title("📅 Monthly Trading Calendar")
    
    if not df.empty:
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        # יצירת לוח שנה בסיסי באמצעות Pivot Table של PNL יומי
        df['day'] = df['trade_date'].dt.date
        daily_pnl = df.groupby('day')['pnl'].sum().reset_index()
        
        # תצוגה פשוטה אך אפקטיבית של לוח שנה
        st.write("סיכום יומי:")
        for index, row in daily_pnl.iterrows():
            color = "#00ffcc" if row['pnl'] >= 0 else "#ff4b4b"
            st.markdown(f"""
                <div style="background-color: #1e2130; padding: 10px; border-radius: 5px; border-right: 5px solid {color}; margin-bottom: 5px;">
                    <strong>{row['day']}</strong> | PNL: <span style="color: {color};">${row['pnl']:.2f}</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.write("אין נתונים להצגה בלוח השנה.")

# --- ➕ הזנת עסקה (מעוצב) ---
elif page == "➕ הזנת עסקה":
    st.title("➕ Log New Trade")
    with st.container():
        with st.form("new_trade_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                pnl = st.number_input("PNL ($)", step=10.0)
                stop = st.number_input("Stop Points", step=1.0)
                tp = st.number_input("Target Points", step=1.0)
            with c2:
                date = st.date_input("Date", datetime.now())
                emotion = st.selectbox("How did you feel?", ["Neutral", "Confident", "Greedy", "Fearful", "Revenge"])
                htf = st.text_input("HTF PD Array (e.g. Daily FVG)")

            st.write("---")
            st.write("🔍 **Confirmations**")
            conf_cols = st.columns(3)
            ts = conf_cols[0].checkbox("Turtle Soup")
            ifvg = conf_cols[0].checkbox("IFVG (1m/3m/5m)")
            liq = conf_cols[1].checkbox("Liquidity Taken")
            ote = conf_cols[1].checkbox("OTE / 0.5 Range")
            prem = conf_cols[2].checkbox("Premium/Discount")
            pull = conf_cols[2].checkbox("Pullback Entry")

            notes = st.text_area("Notes & Lessons")
            submitted = st.form_submit_button("LOCK TRADE 🔒")
            
            if submitted:
                # לוגיקת שמירה (כמו בקוד הקודם, רק וודא ששמות השדות תואמים ל-SQL)
                data = {"pnl": pnl, "trade_date": str(date), "stop_points": stop, "tp_points": tp, 
                        "emotion": emotion, "notes": notes, "is_premium": prem, "liquidity_taken": liq}
                supabase.table("turtle_soup_journal").insert(data).execute()
                st.success("Trade Recorded!")
                st.balloons()

# --- 📜 היסטוריית עסקאות ---
elif page == "📜 היסטוריית עסקאות":
    st.title("📜 Trade History & Documentation")
    
    if df.empty:
        st.write("אין היסטוריה.")
    else:
        for idx, row in df.iterrows():
            color = "#00ffcc" if row['pnl'] >= 0 else "#ff4b4b"
            with st.container():
                st.markdown(f"""
                    <div class="trade-card" style="border-left: 5px solid {color};">
                        <h4 style="margin:0;">📅 {row['trade_date']} | PNL: <span style="color:{color};">${row['pnl']}</span></h4>
                        <p style="margin:5px 0;"><strong>Emotion:</strong> {row['emotion']} | <strong>Notes:</strong> {row['notes']}</p>
                    </div>
                """, unsafe_allow_html=True)
                # כפתור לצפייה בפרטי התמונה אם קיימת
                if st.button(f"View Details #{row['id']}", key=f"btn_{row['id']}"):
                    st.json(row.to_dict()) # כאן אפשר להוסיף תצוגת תמונה

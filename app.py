import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os
from supabase import create_client

# --- 1. הגדרות ועיצוב ---
st.set_page_config(page_title="Turtle Journal", layout="wide")
st.markdown("""<style>
    div[data-testid="stMetric"] { background-color: #1e2130; border: 1px solid #3e4255; padding: 15px; border-radius: 10px; }
    div[data-testid="stMetricLabel"] > div { color: #00ffcc !important; }
    div[data-testid="stMetricValue"] > div { color: white !important; }
    .calendar-day { height: 100px; border-radius: 8px; padding: 5px; color: white; text-align: center; }
    .win { background: #1b5e20; border: 1px solid #00ffcc; }
    .loss { background: #b71c1c; border: 1px solid #ff4b4b; }
    .neutral { background: #1e2130; border: 1px solid #3e4255; }
</style>""", unsafe_allow_html=True)

# --- 2. חיבור ל-Supabase ---
# שימוש בגישה בטוחה ל-Secrets
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Missing Supabase Secrets! Check your Streamlit Cloud settings.")
    st.stop()

# --- 3. משיכת נתונים עם "חגורת בטיחות" ---
@st.cache_data(ttl=5)
def get_data():
    try:
        res = supabase.table("turtle_soup_journal").select("*").order("trade_date").execute()
        temp_df = pd.DataFrame(res.data)
        
        # אם הטבלה ריקה, ניצור DataFrame עם עמודות ריקות כדי למנוע KeyError
        if temp_df.empty:
            return pd.DataFrame(columns=['trade_date', 'pnl', 'stop_points', 'tp_points', 'confirmations', 'emotion', 'notes', 'image_url'])
        
        temp_df['trade_date'] = pd.to_datetime(temp_df['trade_date'])
        return temp_df
    except Exception:
        return pd.DataFrame(columns=['trade_date', 'pnl', 'stop_points', 'tp_points', 'confirmations', 'emotion', 'notes', 'image_url'])

df = get_data()

# --- 4. דשבורד ואנליזה ---
st.title("🐢 TurtleSoup Ultimate Journal")

# חישוב מדדים רק אם יש נתונים
if not df.empty:
    c1, c2, c3 = st.columns(3)
    total_pnl = df['pnl'].astype(float).sum()
    win_rate = (len(df[df['pnl'].astype(float) > 0]) / len(df)) * 100
    c1.metric("Total PNL", f"${total_pnl:,.2f}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Total Trades", len(df))
else:
    st.info("👋 ברוך הבא! היומן ריק. הכנס את העסקה הראשונה שלך בצד ימין.")

st.markdown("---")

# --- 5. לוח שנה וטופס ---
col_cal, col_form = st.columns([2, 1])

with col_cal:
    st.subheader("📅 Calendar")
    now = datetime.now()
    cal = calendar.monthcalendar(now.year, now.month)
    cols = st.columns(7)
    for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]): 
        cols[i].markdown(f"<center><b>{d}</b></center>", unsafe_allow_html=True)
    
    for week in cal:
        cw = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                d_obj = datetime(now.year, now.month, day).date()
                # בדיקה בטוחה אם יש עסקאות ביום הזה
                day_trades = df[df['trade_date'].dt.date == d_obj] if not df.empty else pd.DataFrame()
                d_pnl = day_trades['pnl'].astype(float).sum() if not day_trades.empty else 0
                
                style = "neutral"
                if not day_trades.empty:
                    style = "win" if d_pnl >= 0 else "loss"
                
                cw[i].markdown(f"<div class='calendar-day {style}'><b>{day}</b><br>${d_pnl:.0f}</div>", unsafe_allow_html=True)

with col_form:
    st.subheader("➕ New Trade")
    with st.form("trade_form", clear_on_submit=True):
        f_pnl = st.number_input("PNL ($)", step=1.0)
        f_date = st.date_input("Date", datetime.now())
        f_sl = st.number_input("Stop Points", step=0.1)
        f_tp = st.number_input("TP Points", step=0.1)
        
        st.write("**Confirmations:**")
        c_left, c_right = st.columns(2)
        c_ts = c_left.checkbox("Turtle Soup")
        c_1m = c_left.checkbox("1m IFVG")
        c_3m = c_left.checkbox("3m IFVG")
        c_5m = c_left.checkbox("5m IFVG")
        c_li = c_left.checkbox("Liquidity Taken")
        c_pr = c_right.checkbox("Premium")
        c_di = c_right.checkbox("Discount")
        c_pb = c_right.checkbox("Pullback")
        c_ot = c_right.checkbox("OTE")
        c_05 = c_right.checkbox("0.5 Range")
        
        f_htf = st.text_input("HTF PD Array")
        f_emo = st.selectbox("Emotion", ["Confident", "Neutral", "Fearful", "Greedy", "Revenge"])
        f_not = st.text_area("Notes")
        f_img = st.file_uploader("Screenshot", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("LOCK TRADE 🔒"):
            img_url = ""
            if f_img:
                try:
                    file_path = f"{datetime.now().strftime('%H%M%S')}_{f_img.name}"
                    supabase.storage.from_("Screenshots").upload(file_path, f_img.getvalue())
                    img_url = supabase.storage.from_("Screenshots").get_public_url(file_path)
                except:
                    st.warning("התמונה לא עלתה, אבל העסקה תישמר.")
            
            # איסוף אישורים
            checks = {"TS":c_ts,"1m":c_1m,"3m":c_3m,"5m":c_5m,"Liq":c_li,"Prem":c_pr,"Disc":c_di,"PB":c_pb,"OTE":c_ot,"0.5":c_05}
            confs = ", ".join([k for k, v in checks.items() if v])
            
            try:
                supabase.table("turtle_soup_journal").insert({
                    "trade_date": str(f_date), "pnl": f_pnl, "stop_points": f_sl, "tp_points": f_tp,
                    "confirmations": confs, "htf_pd_array": f_htf, "emotion": f_emo, "notes": f_not, "image_url": img_url
                }).execute()
                st.success("Saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving: {e}")

# --- 6. היסטוריה ---
if not df.empty:
    st.markdown("---")
    st.subheader("📜 History")
    for _, r in df.sort_values("trade_date", ascending=False).head(10).iterrows():
        with st.expander(f"Trade {r['trade_date'].date()} | PNL: ${r['pnl']}"):
            st.write(f"**Emotion:** {r['emotion']} | **Confirmations:** {r['confirmations']}")
            st.write(f"**HTF:** {r['htf_pd_array']} | **Notes:** {r['notes']}")
            if r['image_url']: st.image(r['image_url'], use_container_width=True)

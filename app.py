import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os
from supabase import create_client

# 1. הגדרות ועיצוב
st.set_page_config(page_title="Turtle Journal", layout="wide")
st.markdown("""<style>
    div[data-testid="stMetric"] { background-color: #1e2130; border: 1px solid #3e4255; padding: 15px; border-radius: 10px; }
    .calendar-day { height: 100px; border-radius: 8px; padding: 5px; color: white; text-align: center; }
    .win { background: #1b5e20; border: 1px solid #00ffcc; }
    .loss { background: #b71c1c; border: 1px solid #ff4b4b; }
    .neutral { background: #1e2130; border: 1px solid #3e4255; }
</style>""", unsafe_allow_html=True)

# 2. חיבור ל-Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 3. משיכת נתונים
@st.cache_data(ttl=10)
def get_data():
    res = supabase.table("turtle_soup_journal").select("*").order("trade_date").execute()
    return pd.DataFrame(res.data)

df = get_data()

# 4. דשבורד ואנליזה
st.title("🐢 TurtleSoup Ultimate Journal")
if not df.empty:
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    c1, c2, c3 = st.columns(3)
    c1.metric("Total PNL", f"${df['pnl'].sum():,.2f}")
    c2.metric("Win Rate", f"{(len(df[df['pnl']>0])/len(df)*100):.1f}%")
    c3.metric("Total Trades", len(df))

st.markdown("---")

# 5. לוח שנה וטופס
col_cal, col_form = st.columns([2, 1])

with col_cal:
    st.subheader("📅 Calendar")
    now = datetime.now()
    cal = calendar.monthcalendar(now.year, now.month)
    cols = st.columns(7)
    for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]): cols[i].write(f"**{d}**")
    
    for week in cal:
        cw = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                d_obj = datetime(now.year, now.month, day).date()
                d_pnl = df[df['trade_date'].dt.date == d_obj]['pnl'].sum() if not df.empty else 0
                d_trades = len(df[df['trade_date'].dt.date == d_obj]) if not df.empty else 0
                style = "win" if d_trades > 0 and d_pnl >= 0 else "loss" if d_trades > 0 else "neutral"
                cw[i].markdown(f"<div class='calendar-day {style}'><b>{day}</b><br>${d_pnl:.0f}</div>", unsafe_allow_html=True)

with col_form:
    st.subheader("➕ New Trade")
    with st.form("f", clear_on_submit=True):
        f_pnl = st.number_input("PNL ($)", step=1.0)
        f_date = st.date_input("Date", datetime.now())
        f_sl = st.number_input("Stop Points")
        f_tp = st.number_input("TP Points")
        
        st.write("Confirmations:")
        c1, c2 = st.columns(2)
        c_ts = c1.checkbox("Turtle Soup")
        c_1m = c1.checkbox("1m IFVG")
        c_3m = c1.checkbox("3m IFVG")
        c_5m = c1.checkbox("5m IFVG")
        c_li = c1.checkbox("Liquidity Taken")
        c_pr = c2.checkbox("Premium")
        c_di = c2.checkbox("Discount")
        c_pb = c2.checkbox("Pullback")
        c_ot = c2.checkbox("OTE")
        c_05 = c2.checkbox("0.5 Range")
        
        f_htf = st.text_input("HTF PD Array")
        f_emo = st.selectbox("Emotion", ["Confident", "Neutral", "Fearful", "Greedy"])
        f_not = st.text_area("Notes")
        f_img = st.file_uploader("Screenshot", type=['png', 'jpg'])
        
        if st.form_submit_button("SAVE"):
            img_url = ""
            if f_img:
                path = f"{datetime.now().strftime('%H%M%S')}_{f_img.name}"
                supabase.storage.from_("Screenshots").upload(path, f_img.getvalue())
                img_url = supabase.storage.from_("Screenshots").get_public_url(path)
            
            confs = [k for k, v in {"TS":c_ts,"1m":c_1m,"3m":c_3m,"5m":c_5m,"Liq":c_li,"Prem":c_pr,"Disc":c_di,"PB":c_pb,"OTE":c_ot,"0.5":c_05}.items() if v]
            
            supabase.table("turtle_soup_journal").insert({
                "trade_date": str(f_date), "pnl": f_pnl, "stop_points": f_sl, "tp_points": f_tp,
                "confirmations": ", ".join(confs), "htf_pd_array": f_htf, "emotion": f_emo, "notes": f_not, "image_url": img_url
            }).execute()
            st.success("Saved!")
            st.rerun()

# 6. היסטוריה
st.markdown("---")
if not df.empty:
    for _, r in df.sort_values("trade_date", ascending=False).head(5).iterrows():
        with st.expander(f"Trade {r['trade_date'].date()} | PNL: ${r['pnl']}"):
            st.write(f"**Confirmations:** {r['confirmations']} | **Emotion:** {r['emotion']}")
            if r['image_url']: st.image(r['image_url'])

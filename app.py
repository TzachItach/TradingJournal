import streamlit as st
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px

# טעינת משתני סביבה מהקובץ .env
load_dotenv()

# הגדרות Supabase מה-.env
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Turtle Soup Trading Journal", layout="wide")

# --- כותרת ותפריט ---
st.title("🛡️ Turtle Soup אינטראקטיבי")

menu = ["הזנת עסקה חדשה", "דשבורד אנליזה", "צפייה בעסקאות"]
choice = st.sidebar.selectbox("תפריט ניווט", menu)

# --- פונקציות עזר ---

def upload_screenshot(trade_id, file):
    """מעלה קובץ ל-Supabase Storage ומחזיר את ה-Public URL"""
    bucket_name = "screenshots"
    file_extension = os.path.splitext(file.name)[1]
    file_name = f"trade_{trade_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_extension}"
    
    # העלאה
    res = supabase.storage.from_(bucket_name).upload(file_name, file)
    
    # קבלת ה-Public URL
    if res.status_code == 200:
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        return public_url
    else:
        st.error("שגיאה בהעלאת התמונה")
        return None

# --- דף הזנת עסקה חדשה ---
if choice == "הזנת עסקה חדשה":
    st.subheader("📝 הזנת עסקה חדשה (Turtle Soup)")

    with st.form("trade_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            trade_date = st.date_input("תאריך עסקה", datetime.now())
            trade_time = st.time_input("שעת עסקה", datetime.now())
            combined_date = datetime.combine(trade_date, trade_time)
            
        with col2:
            pnl = st.number_input("PNL ($)", format="%.2f")
            stop_points = st.number_input("כמות נקודות סטופ", format="%.2f")
            
        with col3:
            tp_points = st.number_input("כמות נקודות רווח", format="%.2f")

        st.markdown("---")
        st.write("📋 **אישורים לעסקה:**")
        
        # ארגון ה-Checkboxes בצורה נקייה
        c1, c2, c3, c4 = st.columns(4)
        ts = c1.checkbox("Turtle Soup")
        ifvg_1m = c2.checkbox("1m IFVG")
        ifvg_3m = c3.checkbox("3M IFVG")
        ifvg_5m = c4.checkbox("5M IFVG")
        premium = c1.checkbox("Premium")
        discount = c2.checkbox("Discount")
        pullback = c3.checkbox("Entry at Pullback")
        ote_range = c4.checkbox("OTE 0.5 Of range")
        liquidity = c1.checkbox("Liquidity Taken?")

        st.markdown("---")
        st.write("💬 **פרטים נוספים:**")
        htf_text = st.text_area("HTF PD array (הכנס גאפים וטווחי זמן)")
        emotion = st.selectbox("רגש במהלך העסקה", ["Neutral", "Confident", "Greedy", "Fearful", "Excited", "Anxious"])
        notes = st.text_area("הערות")

        # העלאת צילום מסך
        uploaded_file = st.file_uploader("העלה צילום מסך (TradingView/אחר)", type=['png', 'jpg', 'jpeg'])

        # כפתור שמירה
        submitted = st.form_submit_submit("שמור עסקה")

    # לוגיקה לשמירה ב-Supabase
    if submitted:
        # 1. יצירת העסקה בטבלה הראשית
        new_trade = {
            "trade_date": combined_date.isoformat(),
            "pnl": pnl,
            "stop_points": stop_points,
            "tp_points": tp_points,
            "is_premium": premium,
            "is_discount": discount,
            "entry_at_pullback": pullback,
            "ote_05_range": ote_range,
            "liquidity_taken": liquidity,
            "emotion": emotion,
            "notes": notes
        }
        
        try:
            res = supabase.table("turtle_soup_journal").insert(new_trade).execute()
            trade_id = res.data[0]['id']
            
            # 2. העלאת התמונה (אם יש) וקישור בטבלה הריקות
            if uploaded_file is not None:
                public_url = upload_screenshot(trade_id, uploaded_file)
                if public_url:
                    supabase.table("trade_screenshots").insert({"trade_id": trade_id, "screenshot_url": public_url}).execute()
            
            # 3. שמירת ה-Checkboxes של האישורים (לצורך אנליזה)
            confirmations_to_insert = []
            if ts: confirmations_to_insert.append({"trade_id": trade_id, "conf_name": "Turtle Soup"})
            if ifvg_1m: confirmations_to_insert.append({"trade_id": trade_id, "conf_name": "1m IFVG"})
            if ifvg_3m: confirmations_to_insert.append({"trade_id": trade_id, "conf_name": "3m IFVG"})
            if ifvg_5m: confirmations_to_insert.append({"trade_id": trade_id, "conf_name": "5m IFVG"})
            # הוסיפו את שאר ה-Checkboxes כאן אם אתם רוצים לנתח אותם באופן ספציפי

            if confirmations_to_insert:
                 supabase.table("trade_confirmations").insert(confirmations_to_insert).execute()
            
            st.success("✅ העסקה נשמרה בהצלחה!")
            st.balloons()
            
        except Exception as e:
            st.error(f"שגיאה בשמירת העסקה: {e}")

# --- דף דשבורד אנליזה ---
elif choice == "דשבורד אנליזה":
    st.subheader("📊 דשבורד אנליזה")

    # משיכת כל הנתונים
    trades_res = supabase.table("turtle_soup_journal").select("*").execute()
    trades_data = trades_res.data

    if not trades_data:
        st.info("אין עסקאות רשומות עדיין. הזן עסקה כדי לראות אנליזה.")
    else:
        df = pd.DataFrame(trades_data)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # משיכת האישורים (נצטרך לחישובים מורכבים)
        confirm_res = supabase.table("trade_confirmations").select("*").execute()
        confirm_df = pd.DataFrame(confirm_res.data)

        # 1. מטריקות מפתח (מצטברות)
        total_trades = len(df)
        total_pnl = df['pnl'].sum()
        winning_trades = len(df[df['pnl'] > 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        avg_rr = df.apply(lambda row: row['tp_points'] / row['stop_points'] if row['stop_points'] != 0 else 0, axis=1).mean()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("סך עסקאות", total_trades)
        m2.metric("סך PNL ($)", f"${total_pnl:,.2f}", f"${df.iloc[-1]['pnl']:,.2f}")
        m3.metric("Win Rate (%)", f"{win_rate:.1f}%")
        m4.metric("ממוצע R:R", f"{avg_rr:.2f}:1")

        st.markdown("---")
        # 2. סיכום חודשי
        st.write("📆 **אנליזה לפי חודש:**")
        df['month'] = df['trade_date'].dt.to_period('M')
        monthly_summary = df.groupby('month')['pnl'].sum().reset_index()
        monthly_summary['month'] = monthly_summary['month'].astype(str) # המרה לטקסט לצורך תצוגה
        
        st.dataframe(monthly_summary, use_container_width=True)
        
        # 3. גרף צבירה (PNL לאורך זמן)
        st.write("📉 **עקומת רווח/הפסד (מצטברת):**")
        df['cumulative_pnl'] = df['pnl'].cumsum()
        fig = px.line(df, x='trade_date', y='cumulative_pnl', title="Cumulative PNL")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        # 4. אנליזת אישורים (turtle_soup strategy)
        st.write("🛠️ **אנליזת אישורי אסטרטגיה:**")
        
        # חישוב Win Rate לכל אישור (נצטרך ל-merge)
        merged_df = pd.merge(confirm_df, df, left_on='trade_id', right_on='id', how='left')
        
        # יצירת טבלת win_rate לכל סוג אישור
        confirmation_analysis = []
        unique_confirmations = confirm_df['conf_name'].unique()
        
        for conf in unique_confirmations:
            conf_trades = merged_df[merged_df['conf_name'] == conf]
            c_trades = len(conf_trades)
            w_trades = len(conf_trades[conf_trades['pnl'] > 0])
            w_rate = (w_trades / c_trades) * 100 if c_trades > 0 else 0
            
            confirmation_analysis.append({"אישור": conf, "סך עסקאות": c_trades, "Win Rate (%)": f"{w_rate:.1f}%"})
        
        conf_analysis_df = pd.DataFrame(confirmation_analysis)
        st.dataframe(conf_analysis_df, use_container_width=True)

# --- דף צפייה בעסקאות ---
elif choice == "צפייה בעסקאות":
    st.subheader("🕵️‍♀️ צפייה בכל העסקאות")
    
    # משיכת נתונים עם תמונות
    trades_res = supabase.table("turtle_soup_journal").select("*").execute()
    trades_data = trades_res.data
    
    if not trades_data:
        st.info("אין עסקאות רשומות.")
    else:
        df = pd.DataFrame(trades_data)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # הצגת הטבלה כולה
        st.dataframe(df.sort_values(by='trade_date', ascending=False), use_container_width=True)
        
        # צפייה בפרטים + תמונות לעסקה ספציפית
        st.markdown("---")
        st.write("🔍 **צפייה בפרטי עסקה וצילום מסך:**")
        trade_ids = df['id'].sort_values(ascending=False).tolist()
        selected_trade_id = st.selectbox("בחר מזהה עסקה", trade_ids)
        
        if selected_trade_id:
            trade_details = df[df['id'] == selected_trade_id].iloc[0]
            st.write(f"**תאריך:** {trade_details['trade_date'].strftime('%Y-%m-%d %H:%M')}")
            st.write(f"**PNL:** ${trade_details['pnl']:.2f}")
            st.write(f"**הערות:** {trade_details['notes']}")
            
            # משיכת התמונה
            screenshot_res = supabase.table("trade_screenshots").select("screenshot_url").eq("trade_id", selected_trade_id).execute()
            
            if screenshot_res.data:
                image_url = screenshot_res.data[0]['screenshot_url']
                st.image(image_url, caption=f"Trade {selected_trade_id} Screenshot", use_container_width=True)
            else:
                st.info("לא צורף צילום מסך לעסקה זו.")
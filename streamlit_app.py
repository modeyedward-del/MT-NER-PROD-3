import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="MT-NER Dashboard", layout="wide")

st.title("📊 MT-NER Dashboard")
st.write("Connecting to Google Sheets...")

# Connect to Google Sheets using Streamlit Secrets
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    
    # CHANGE THIS TO YOUR EXACT SHEET NAME
    sheet = client.open("MT-NER") 
    
    st.success(f"✅ Connected to Google Sheet: {sheet.title}")

    # Load all worksheets
    worksheets = sheet.worksheets()
    tabs = st.tabs([ws.title for ws in worksheets])
    
    for i, ws in enumerate(worksheets):
        with tabs[i]:
            st.subheader(f"Tab: {ws.title}")
            data = ws.get_all_records()
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"❌ Connection Failed: {e}")
    st.info("Check 1: Is the sheet shared with mt-ner-bot@inec-plc-board.iam.gserviceaccount.com?")
    st.info("Check 2: Is the sheet name 'MT-NER' correct?")
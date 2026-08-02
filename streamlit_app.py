import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="MT-NER Dashboard", layout="wide")

@st.cache_resource
def connect_gsheets():
    SCOPE = ["https://www.googleapis.com/auth/spreadsheets", 
             "https://www.googleapis.com/auth/drive"]
    
    creds_dict = dict(st.secrets)
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
    client = gspread.authorize(creds)
    
    sheet = client.open("MT-NER") 
    tabs = [ws.title for ws in sheet.worksheets()]
    return sheet, tabs

@st.cache_data(ttl=300)
def load_sheet_data(sheet, tab_name):
    worksheet = sheet.worksheet(tab_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

st.title("MT-NER Production Dashboard")

try:
    sheet, tabs = connect_gsheets()
    st.success(f"Connected to Google Sheet: {sheet.title}")
    
    tab_selected = st.selectbox("Select Sheet Tab", tabs)
    
    if tab_selected:
        df = load_sheet_data(sheet, tab_selected)
        st.dataframe(df, use_container_width=True)
        st.write(f"Total Rows: {len(df)}")

except Exception as e:
    st.error(f"Connection Error: {e}")
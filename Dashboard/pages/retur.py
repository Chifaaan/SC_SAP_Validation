import streamlit as st
import pandas as pd
import numpy as np

# --- Helper Functions ---

def load_dataframe(uploaded_file):
    """Loads an uploaded file into a pandas DataFrame."""
    try:
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
    return None

def map_columns(df, required_cols_map, file_type):
    """
    Checks for required columns. If they don't exist, it provides a mapping interface.
    If the file is completely wrong, it shows an error.
    """
    original_cols = set(df.columns)
    required_keys = set(required_cols_map.keys())
    missing_keys = required_keys - original_cols
    
    if len(missing_keys) == len(required_keys):
        st.error(
            f"Error: The Column doesn't match. Not a single required column "
            f"was found in the uploaded {file_type} file. Please ensure it's the right document.",
            icon="🚨"
        )
        return None

    if not missing_keys:
        return df

    st.write("---")
    st.subheader(f"2. Map Columns for {file_type} File")
    st.write("One or more required columns were not found. Please map them from your file.")
    
    mappings = {}
    all_mapped = True

    for key in required_keys:
        if key in original_cols:
            mappings[key] = key
        else:
            friendly_name = required_cols_map[key]
            selected_col = st.selectbox(
                f"Which column represents '{friendly_name}'?",
                options=list(original_cols),
                index=None,
                placeholder="Select a column...",
                key=f"map_{file_type}_{key}"
            )
            if selected_col:
                mappings[selected_col] = key
            else:
                all_mapped = False
    
    if not all_mapped:
        st.warning("Please map all required columns to proceed.")
        return None
    
    return df.rename(columns=mappings)

# --- Page Configuration and Authentication ---
st.set_page_config(page_title="Document Validation", layout="wide")

if not st.session_state.get('logged_in'):
    st.error("Access denied. Please log in first.")
    st.page_link("pages/login.py", label="Go to Login Page", icon="🔒")
    st.stop()

# --- Main Page UI ---
role = st.session_state.get('role')
st.title(f"📄 Document Validation Portal")
st.markdown(f"Welcome, **{role}**!")

with st.sidebar:
    st.header("Controls")
    if st.button("Logout"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.session_state.logged_in = False
        st.page_link("pages/login.py", label="Go to Login", icon="🔒")

# --- Load Validation File Automatically ---
try:
    val_df_raw = pd.read_csv("./im_purchases_and_return.csv")
    VAL_FILE_LOADED = True
except FileNotFoundError:
    st.error("Validation file not found. Please make sure `im_purchases_and_return.csv` is in the root directory.")
    VAL_FILE_LOADED = False
    st.stop()

# --- File Upload and Processing Section ---
st.header("Upload Your Document")
data_file = None

if role == "Supply Chain":
    data_file = st.file_uploader("Upload your Supply Chain (SC) file", type=['csv', 'xlsx'], key="sc_uploader")
elif role == "Accountant":
    data_file = st.file_uploader("Upload your Accountant (SAP) file", type=['csv', 'xlsx'], key="sap_uploader")

if data_file and VAL_FILE_LOADED:
    data_df = load_dataframe(data_file)
    if data_df is None:
        st.stop()

    val_required_cols = {"kode_outlet": "Outlet Code", "document_id": "Document ID", "no_transaksi": "Transaction Number", "tanggal": "Date", "dpp": "DPP Value"}
    val_df = val_df_raw
    val_df['dpp'] = pd.to_numeric(val_df['dpp'], errors='coerce').fillna(0)

    result_df = None
    # --- Role-Specific Logic ---
    if role == "Supply Chain":
        sc_required_cols = {"kode_outlet": "Outlet Code", "no_penerimaan": "Receipt Number", "tgl_penerimaan": "Receipt Date", "jml_neto": "Net Amount (jml_neto)"}
        sc_df = map_columns(data_df, sc_required_cols, "SC")

        if sc_df is not None:
            with st.spinner("Validating SC file..."):
                sc_df['jml_neto'] = pd.to_numeric(sc_df['jml_neto'], errors='coerce').fillna(0)
                sc_df['tgl_penerimaan'] = pd.to_datetime(sc_df['tgl_penerimaan'], errors='coerce')
                
                sc_agg_df = sc_df.groupby('no_penerimaan').agg(
                    jml_neto=('jml_neto', 'sum'),
                    kode_outlet=('kode_outlet', 'first'),
                    tgl_penerimaan=('tgl_penerimaan', 'first')
                ).reset_index()
                
                val_agg_df = val_df.groupby('no_transaksi')['dpp'].sum().reset_index()
                
                merged_df = pd.merge(sc_agg_df, val_agg_df, left_on='no_penerimaan', right_on='no_transaksi', how='left')
                merged_df = merged_df.drop(columns=['no_transaksi'])
                
                merged_df['dpp'] = merged_df['dpp'].fillna(0)
                merged_df['difference'] = merged_df['jml_neto'] - merged_df['dpp']
                merged_df['status'] = np.where(abs(merged_df['difference']) > 0.01, 'Discrepancy', 'Matched')
                
                result_df = merged_df.rename(columns={
                    'no_penerimaan': 'transaction_code', 'kode_outlet': 'outlet_code',
                    'tgl_penerimaan': 'date', 'jml_neto': 'target_col_value', 'dpp': 'validation_total'
                })

    elif role == "Accountant":
        sap_required_cols = {"profit_center": "Profit Center (Outlet)", "doc_id": "Document ID", "posting_date": "Posting Date", "kredit": "Credit Amount"}
        sap_df = map_columns(data_df, sap_required_cols, "SAP")

        if sap_df is not None:
            with st.spinner("Validating SAP file..."):
                val_agg_df = val_df.groupby('document_id')['dpp'].sum().reset_index()
                sap_df['kredit'] = pd.to_numeric(sap_df['kredit'], errors='coerce').fillna(0)
                sap_df['posting_date'] = pd.to_datetime(sap_df['posting_date'], errors='coerce')

                merged_df = pd.merge(sap_df, val_agg_df, left_on='doc_id', right_on='document_id', how='left')
                merged_df = merged_df.drop(columns=['document_id'])
                merged_df['dpp'] = merged_df['dpp'].fillna(0)
                merged_df['difference'] = merged_df['kredit'] - merged_df['dpp']
                merged_df['status'] = np.where(abs(merged_df['difference']) > 0.01, 'Discrepancy', 'Matched')
                
                result_df = merged_df.rename(columns={
                    'doc_id': 'document_id', 'profit_center': 'outlet_code',
                    'posting_date': 'date', 'kredit': 'target_col_value', 'dpp': 'validation_total'
                })
    
    # --- Store results in session state and provide link to dashboard ---
    if result_df is not None:
        st.session_state['role'] = role
        st.session_state['result_df'] = result_df
        st.session_state['val_df'] = val_df
        # Save the correct source dataframe
        if role == "Supply Chain":
            st.session_state['sc_df'] = sc_df # <-- Add this line
            st.session_state['sap_df'] = None # <-- Add this line
        elif role == "Accountant":
            st.session_state['sap_df'] = sap_df # <-- Add this line
            st.session_state['sc_df'] = None # <-- Add this line
        st.success("Validation complete! The results are ready.")
        st.page_link("pages/dashboard.py", label="Go to Dashboard", icon="📊")
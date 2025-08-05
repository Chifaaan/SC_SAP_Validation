import streamlit as st
import pandas as pd
import numpy as np

# --- Helper Functions ---
def load_dataframe(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')): return pd.read_excel(uploaded_file)
    except Exception as e: st.error(f"Error reading file: {e}")
    return None

def map_columns(df, required_cols_map, file_type):
    original_cols, required_keys = set(df.columns), set(required_cols_map.keys())
    missing_keys = required_keys - original_cols
    if len(missing_keys) == len(required_keys):
        st.error(f"Error: Kolom dalam dokumen anda tidak sesuai! Pastikan dokumen yang anda kirim sesuai dengan role Anda!", icon="🚨")
        return None
    if not missing_keys: return df
    st.write("---"); st.subheader(f"Map Columns for {file_type} File")
    mappings, all_mapped = {}, True
    for key in required_keys:
        if key in original_cols: mappings[key] = key
        else:
            friendly_name = required_cols_map[key]
            selected_col = st.selectbox(f"Which column represents '{friendly_name}'?", list(original_cols), index=None, placeholder="Select...", key=f"map_{file_type}_{key}")
            if selected_col: mappings[selected_col] = key
            else: all_mapped = False
    if not all_mapped:
        st.warning("Please map all required columns."); return None
    return df.rename(columns=mappings)

# --- Page Configuration and Authentication ---
st.set_page_config(page_title="Document Validation", layout="wide")
if not st.session_state.get('logged_in'):
    st.switch_page("pages/login.py")
    st.stop()
role = st.session_state.get('role')
user = st.session_state.get('user')
st.title(f"📄 Document Validation Portal")
st.markdown(f"Welcome, **{user}**!")
st.markdown(f"Anda terdaftar sebagai **{role}**")

with st.sidebar:
    st.header("Controls")
    if st.button("Logout"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.switch_page("pages/login.py")
        st.stop()

# --- Load Validation File ---
try:
    val_df_raw = pd.read_csv("./im_purchases_and_return.csv")
    VAL_FILE_LOADED = True
except FileNotFoundError:
    st.error("Validation file not found: `im_purchases_and_return.csv` must be in the root directory."); st.stop()

# --- File Upload Section ---
st.header("Upload Your Document")
data_file = None
if role == "Supply Chain": data_file = st.file_uploader("Upload your Supply Chain (SC) file", type=['csv', 'xlsx'])
elif role == "Accountant": data_file = st.file_uploader("Upload your Accountant (SAP) file", type=['csv', 'xlsx'])

if data_file and VAL_FILE_LOADED:
    data_df = load_dataframe(data_file)
    if data_df is None: st.stop()

    # --- THIS IS THE NEW CORE LOGIC ---
    val_required_cols = {"kode_outlet": "Outlet", "document_id": "Doc ID", "no_transaksi": "Trans Num", "dpp": "DPP", "total": "Total"}
    val_df = map_columns(val_df_raw.copy(), val_required_cols, "VAL")
    if val_df is None: st.stop()
        
    val_df['dpp'] = pd.to_numeric(val_df['dpp'], errors='coerce').fillna(0)
    val_df['total'] = pd.to_numeric(val_df['total'], errors='coerce').fillna(0)

    result_df = None
    sc_df_mapped, sap_df_mapped = None, None

    with st.spinner("Validating file..."):
        if role == "Supply Chain":
            sc_required = {"kode_outlet": "Outlet Code", "no_penerimaan": "Receipt Number", "tgl_penerimaan": "Receipt Date", "jml_neto": "Net Amount"}
            sc_df_mapped = map_columns(data_df, sc_required, "SC")
            if sc_df_mapped is not None:
                sc_df_mapped['jml_neto'] = pd.to_numeric(sc_df_mapped['jml_neto'], errors='coerce').fillna(0)
                sc_df_mapped['tgl_penerimaan'] = pd.to_datetime(sc_df_mapped['tgl_penerimaan'], errors='coerce')
                source_agg = sc_df_mapped.groupby('no_penerimaan').agg(
                    target_col_value=('jml_neto', 'sum'),
                    outlet_code=('kode_outlet', 'first'),
                    date=('tgl_penerimaan', 'first')
                ).reset_index().rename(columns={'no_penerimaan': 'transaction_code'})
                id_col, val_id_col = 'transaction_code', 'no_transaksi'
                
        elif role == "Accountant":
            sap_required = {"profit_center": "Profit Center", "doc_id": "Document ID", "posting_date": "Posting Date", "kredit": "Credit Amount"}
            sap_df_mapped = map_columns(data_df, sap_required, "SAP")
            if sap_df_mapped is not None:
                sap_df_mapped['kredit'] = pd.to_numeric(sap_df_mapped['kredit'], errors='coerce').fillna(0)
                sap_df_mapped['posting_date'] = pd.to_datetime(sap_df_mapped['posting_date'], errors='coerce')
                source_agg = sap_df_mapped.rename(columns={
                    'doc_id': 'document_id', 'profit_center': 'outlet_code',
                    'posting_date': 'date', 'kredit': 'target_col_value'
                })
                source_agg['target_col_value'] = abs(source_agg['target_col_value'])
                id_col, val_id_col = 'document_id', 'document_id'

        if 'source_agg' in locals():
            val_agg_dpp = val_df.groupby(val_id_col)['dpp'].sum().reset_index()
            val_agg_total = val_df.groupby(val_id_col)['total'].sum().reset_index()
            
            merged = pd.merge(source_agg, val_agg_dpp, left_on=id_col, right_on=val_id_col, how='left')
            merged['dpp'] = merged['dpp'].fillna(0)
            initial_diff = merged['target_col_value'] - merged['dpp']
            merged['status'] = np.where(abs(initial_diff) > 0.01, 'Discrepancy', 'Matched')
            
            merged = pd.merge(merged, val_agg_total, left_on=id_col, right_on=val_id_col, how='left', suffixes=('', '_y'))
            if val_id_col+'_y' in merged.columns: merged = merged.drop(columns=[val_id_col+'_y'])
            merged['dpp'] = merged['dpp'].fillna(0)
            
            merged['difference'] = np.where(
                merged['status'] == 'Discrepancy',
                merged['target_col_value'] - merged['dpp'],
                initial_diff
            )
            
            result_df = merged.rename(columns={'dpp': 'validation_total'})
            final_cols = [id_col, 'outlet_code', 'date', 'target_col_value', 'validation_total', 'difference', 'status']
            result_df = result_df[final_cols]
            
    if result_df is not None:
        st.session_state['result_df'] = result_df
        st.session_state['val_df'] = val_df_raw
        st.session_state['role'] = role
        st.session_state['sc_df'] = sc_df_mapped
        st.session_state['sap_df'] = sap_df_mapped
        st.success("Validation complete! The results are ready.")
        st.page_link("pages/dashboard.py", label="Go to Dashboard", icon="📊")

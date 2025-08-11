import streamlit as st
import pandas as pd
import numpy as np
import time
import os
from minio import Minio
from io import BytesIO
from dotenv import load_dotenv
import uuid



# -- Set Connection to MinIO --
load_dotenv()
minio_client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)

# --- Page Configuration and Authentication ---
st.set_page_config(page_title="Document Validation", layout="centered", initial_sidebar_state="expanded")

# --- Sidebar Navigation ---
with st.sidebar:
    st.image("kf.png")
    st.divider()
    st.header("Navigation") 
    if st.button("Lihat Log Proses", use_container_width=True, type="secondary", icon=":material/history:"):
        st.session_state.data_sent = True
        st.switch_page("pages/process.py")
    st.header("Controls")
    if st.button("Logout", use_container_width=True, type="primary"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.switch_page("pages/login.py")
        st.stop()
# --- Helper Functions ---
def load_dataframe(uploaded_file):
    try:
        # Baca file sesuai ekstensi
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
    
    return None

def map_columns(df, required_cols_map, file_type):
    original_cols, required_keys = set(df.columns), set(required_cols_map.keys())
    missing_keys = required_keys - original_cols
    if len(missing_keys) == len(required_keys):
        st.error(f"Error: Kolom dalam dokumen anda tidak sesuai! Pastikan dokumen yang anda kirim sesuai dengan role Anda!", icon="🚨")
        return None
    if not missing_keys: return df
    st.write("---"); st.subheader(f"Terdapat kolom yang tidak sesuai pada file {file_type}")
    st.write("Silahkan pilih kolom yang sesuai untuk melanjutkan proses validasi.")
    mappings, all_mapped = {}, True
    for key in required_keys:
        if key in original_cols: mappings[key] = key
        else:
            friendly_name = required_cols_map[key]
            selected_col = st.selectbox(f"Pilihlah kolom yang mewakilkan :red-background['{friendly_name}']?", list(original_cols), index=None, placeholder="Select...", key=f"map_{file_type}_{key}")
            if selected_col: mappings[selected_col] = key
            else: all_mapped = False
    if not all_mapped:
        st.warning("Tolong lengkapi seluruh kolom."); return None
    return df.rename(columns=mappings)



if not st.session_state.get('logged_in'):
    st.switch_page("pages/login.py")
    st.stop()

# --- Set login time once only ---
if 'login_time' not in st.session_state:
    st.session_state['login_time'] = pd.Timestamp.now()

login_time = st.session_state['login_time']


role = st.session_state.get('role')
user = st.session_state.get('user')
st.session_state.data_sent = False
st.title(f"📄 Document Validation Portal")

col1, col2 = st.columns(2)
with col1:
    st.subheader("User Information")
    with st.container(border=True, height=147):
        st.markdown(f'''Nama User: :green[ **{user}**]''')
        st.markdown(f''':blue-background[Role User: **{role}**]''')
        st.markdown(f"Waktu login: {login_time.strftime('%Y-%m-%d %H:%M:%S')}")

with col2:
    st.subheader("Document Types")
    if role == "Supply Chain":
        with st.container(border=True):
            st.markdown("Dokumen yang dapat anda validasi:")
            st.markdown("- **Dokumen Reguler Pembelian**")
            st.markdown("- **Dokumen Retur Pembelian**")
    elif role == "Accountant":
        with st.container(border=True):
            st.markdown("Dokumen yang dapat anda validasi:")
            st.markdown("- **Dokumen Reguler Pembelian**")
            st.markdown("- **Dokumen Retur Pembelian**")
    
    elif role == "Admin":
        with st.container(border=True):
            st.markdown("Dokumen yang dapat anda validasi:")
            st.markdown("- **Dokumen Reguler Pembelian**")
            st.markdown("- **Dokumen Retur Pembelian**")

# --- Load Validation File ---
try:
    val_df_raw = pd.read_csv("./im_purchases_and_return.csv")
    VAL_FILE_LOADED = True
except FileNotFoundError:
    st.error("Validation file not found: `im_purchases_and_return.csv` must be in the root directory."); st.stop()

# --- File Upload Section ---
radio_cols = st.columns(2)
with radio_cols[0]:
    file_type = st.radio("Select Document Type", ["Reguler", "Retur"], key="file_type_selector", horizontal=True)
st.header("Upload Your Document")
data_file = None
if role == "Supply Chain": 
    st.markdown("**Note:** Pastikan kolom berikut tersedia: `kode_outlet`, `no_penerimaan`, `tgl_penerimaan`, dan `jml_neto`.")
    data_file = st.file_uploader("Upload your Supply Chain (SC) file", type=['csv', 'xlsx'])

elif role == "Accountant": 
    st.markdown("**Note:** Pastikan kolom berikut tersedia: `profit_center`, `doc_id`, `posting_date`, dan `kredit`.")
    data_file = st.file_uploader("Upload your Accountant (SAP) file", type=['csv', 'xlsx'])

elif role == "Admin":
    with radio_cols[1]:
        doc_role = st.radio("Pilih jenis dokumen yang akan divalidasi:", ["Supply Chain", "Accountant"], horizontal=True)
    
    if doc_role == "Supply Chain":
        st.markdown("**Note:** Pastikan kolom berikut tersedia: `kode_outlet`, `no_penerimaan`, `tgl_penerimaan`, dan `jml_neto`.")
        data_file = st.file_uploader("Upload Supply Chain (SC) file", type=['csv', 'xlsx'])
        role_to_process = "Supply Chain"
    
    elif doc_role == "Accountant":
        st.markdown("**Note:** Pastikan kolom berikut tersedia: `profit_center`, `doc_id`, `posting_date`, dan `kredit`.")
        data_file = st.file_uploader("Upload Accountant (SAP) file", type=['csv', 'xlsx'])
        role_to_process = "Accountant"
else:
    role_to_process = role

if data_file and VAL_FILE_LOADED:
    data_df = load_dataframe(data_file)
    # Simpan nama file ke dalam session_state
    if data_df is None: st.stop()
    st.session_state['uploaded_filename'] = data_file.name

    # --- CORE LOGIC ---
    val_required_cols = {"kode_outlet": "Outlet", "document_id": "Doc ID", "no_transaksi": "Trans Num", "dpp": "DPP", "total": "Total"}
    val_df = map_columns(val_df_raw.copy(), val_required_cols, "VAL")
    if val_df is None: st.stop()
        
    val_df['dpp'] = pd.to_numeric(val_df['dpp'], errors='coerce').fillna(0)
    val_df['total'] = pd.to_numeric(val_df['total'], errors='coerce').fillna(0)

    result_df = None
    sc_df_mapped, sap_df_mapped = None, None

    with st.spinner("Validating Column..."):
        time.sleep(0.5)
        if role == "Supply Chain":
            st.markdown("File yang diupload:")
            st.dataframe(data_df.head())
            sc_required = {"kode_outlet": "Outlet Code", "no_penerimaan": "Nomor Penerimaan", "tgl_penerimaan": "Tanggal Penerimaan", "jml_neto": "Jumlah Neto"}
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
            st.markdown("File yang diupload:")
            st.dataframe(data_df.head())
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
        
        elif role_to_process == "Supply Chain":
            st.markdown("File yang diupload:")
            st.dataframe(data_df.head())
            sc_required = {"kode_outlet": "Outlet Code", "no_penerimaan": "Nomor Penerimaan", "tgl_penerimaan": "Tanggal Penerimaan", "jml_neto": "Jumlah Neto"}
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

        elif role_to_process == "Accountant":
            st.markdown("File yang diupload:")
            st.dataframe(data_df.head())
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
    
        if role == "Admin":
            st.session_state['role_to_process'] = role_to_process
        else:
            st.session_state['role'] = role
        
        st.session_state['sc_df'] = sc_df_mapped
        st.session_state['sap_df'] = sap_df_mapped
        st.session_state['file_type'] = file_type
        
        st.success("Kolom sudah sesuai! Hasil sudah siap.")
        if st.button("View Results", use_container_width=True, type="primary"):
            # --- Insert Result into MinIO ---
            unique_id = str(uuid.uuid4())
            minio_path = f"{unique_id}.csv"
            minio_client.put_object(
                os.getenv("BUCKET_NAME"),
                minio_path,
                BytesIO(result_df.to_csv(index=False).encode('utf-8')),
                len(result_df.to_csv(index=False).encode('utf-8')),
                content_type="application/csv"
            )
            st.session_state['minio_path'] = minio_path
            st.switch_page("pages/dashboard.py")

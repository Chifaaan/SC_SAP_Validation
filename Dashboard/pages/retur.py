import streamlit as st
import pandas as pd
import time

# --- Page Config and Authentication/Gatekeeping ---
st.set_page_config(page_title="Validasi Retur", layout="wide", page_icon="🔄")

# Redirect if not logged in or if no process is selected
if not st.session_state.get('authenticated', False):
    st.warning("Akses ditolak. Silakan login terlebih dahulu.")
    st.switch_page("pages/login.py")
if not st.session_state.get('current_process_id'):
    st.warning("Tidak ada proses yang dipilih. Silakan pilih proses dari halaman utama.")
    st.switch_page("pages/process.py")

# --- Load Validation Data ---
@st.cache_data
def load_validation_data(filepath):
    try:
        df = pd.read_csv(filepath)
        df['document_id'] = df['document_id'].astype(str)
        df['no_transaksi'] = df['no_transaksi'].astype(str)
        return df
    except Exception as e:
        st.error(f"Gagal memuat file validasi 'im_purchases_and_return.csv': {e}")
        return None

val_df = load_validation_data("./im_purchases_and_return.csv")

# --- Sidebar ---
with st.sidebar:
    st.info(f"Login sebagai:\n**{st.session_state.get('name', 'N/A')}**\n({st.session_state.get('role', 'N/A')})")
    st.divider()
    st.page_link("process.py", label="⬅️ Kembali ke Daftar Proses")

# --- Main Page ---
st.title(f"🔄 Validasi Dokumen Retur")
st.info(f"ID Proses Aktif: **{st.session_state.get('current_process_id')}**")
st.markdown("---")

role = st.session_state.get('role')
uploaded_df = None
file_type = ""

# --- Role-Based File Upload ---
if role == "Supply Chain":
    st.header("Langkah 1: Upload File Supply Chain (SC)")
    file_type = "SC"
    sc_file = st.file_uploader("Upload file retur dari SC", type=["csv", "xlsx"])
    if sc_file:
        uploaded_df = pd.read_csv(sc_file, dtype=str) if sc_file.name.endswith('.csv') else pd.read_excel(sc_file, dtype=str)

elif role == "Akuntansi":
    st.header("Langkah 1: Upload File SAP")
    file_type = "SAP"
    sap_file = st.file_uploader("Upload file retur dari SAP", type=["csv", "xlsx"])
    if sap_file:
        uploaded_df = pd.read_csv(sap_file, dtype=str) if sap_file.name.endswith('.csv') else pd.read_excel(sap_file, dtype=str)

else:
    st.error("Role tidak dikenali. Tidak dapat melanjutkan.")


# --- Processing Logic ---
if uploaded_df is not None and val_df is not None:
    st.header("Langkah 2: Pratinjau dan Proses")
    st.dataframe(uploaded_df.head())

    if st.button(f"🚀 Proses Validasi File {file_type}", type="primary", use_container_width=True):
        with st.spinner("Memproses validasi..."):
            validated_df = None
            try:
                if role == "Supply Chain":
                    # Merge SC data with validation data
                    merged_df = pd.merge(
                        uploaded_df,
                        val_df[['no_transaksi', 'dpp', 'tanggal']],
                        left_on='no_penerimaan',
                        right_on='no_transaksi',
                        how='left',
                        suffixes=('_sc', '_val')
                    )
                    # Rename for consistency
                    validated_df = merged_df.rename(columns={
                        'kode_outlet': 'outlet',
                        'tgl_penerimaan': 'tanggal',
                        'jml_neto': 'nilai_upload',
                        'dpp': 'nilai_referensi'
                    })
                    # Use the date from the uploaded file as the primary date
                    validated_df['tanggal'] = pd.to_datetime(validated_df['tanggal_sc'])


                elif role == "Akuntansi":
                    # Merge SAP data with validation data
                    merged_df = pd.merge(
                        uploaded_df,
                        val_df[['document_id', 'dpp', 'tanggal']],
                        left_on='doc_id',
                        right_on='document_id',
                        how='left',
                        suffixes=('_sap', '_val')
                    )
                    # Rename for consistency
                    validated_df = merged_df.rename(columns={
                        'profit_center': 'outlet',
                        'posting_date': 'tanggal',
                        'kredit': 'nilai_upload',
                        'dpp': 'nilai_referensi'
                    })
                    validated_df['tanggal'] = pd.to_datetime(validated_df['tanggal_sap'])

                # --- Common Validation Steps ---
                # Convert values to numeric, coercing errors to NaN
                validated_df['nilai_upload'] = pd.to_numeric(validated_df['nilai_upload'], errors='coerce')
                validated_df['nilai_referensi'] = pd.to_numeric(validated_df['nilai_referensi'], errors='coerce')
                
                # Fill NaNs from merge/conversion with 0
                validated_df.fillna({'nilai_upload': 0, 'nilai_referensi': 0}, inplace=True)
                
                # Calculate difference and status
                validated_df['selisih'] = validated_df['nilai_upload'] - validated_df['nilai_referensi']
                validated_df['status'] = validated_df['selisih'].apply(lambda x: "VALID" if abs(x) < 1 else "TIDAK VALID")
                
                # Handle cases where the reference value was not found (missing)
                validated_df.loc[validated_df['nilai_referensi'] == 0, 'status'] = 'REFERENSI TIDAK DITEMUKAN'

                st.session_state['validated_df'] = validated_df
                st.success("Validasi selesai!")
                time.sleep(1)
                st.switch_page("pages/dashboard.py")

            except KeyError as e:
                st.error(f"Kolom kunci tidak ditemukan: {e}. Pastikan file yang di-upload memiliki kolom yang benar.")
            except Exception as e:
                st.error(f"Terjadi kesalahan saat validasi: {e}")
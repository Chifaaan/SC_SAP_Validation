import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

st.set_page_config(
    page_title="Retur Validation",
    page_icon=":material/bar_chart_4_bars:",
    layout="wide"
)

col1, col2 = st.columns(2)
with col1:
    sc_file = st.file_uploader("Upload SC Retur File", type=["csv", "xlsx"])
    if sc_file is not None:
        if sc_file.name.endswith('.csv'):
            sc_df = pd.read_csv(sc_file)
        else:
            sc_df = pd.read_excel(sc_file)

        st.write("SC Retur Data:")
        st.dataframe(sc_df.head())

        st.write("Pilih kolom untuk validasi:")
        #Select box untuk memilih variabel date dan target
        available_targets = [col for col in sc_df.columns]
        sc_outlet = True if 'kode_outlet' in sc_df.columns else None
        st.write("Ketersediaan kolom kode outlet:", sc_outlet)
        default_date_index = available_targets.index('tgl_penerimaan') if 'tgl_penerimaan' in available_targets else None
        sc_date = st.selectbox("Pilih kolom tanggal", options=available_targets, index=default_date_index)
        sc_tar = st.selectbox("Pilih kolom Indikator Validasi", options=available_targets)

    
with col2:
    sap_file = st.file_uploader("Upload SAP Retur File", type=["csv", "xlsx"])
    if sap_file is not None:
        if sap_file.name.endswith('.csv'):
            sap_df = pd.read_csv(sap_file)
        else:
            sap_df = pd.read_excel(sap_file)

        st.write("SAP Retur Data:")
        st.dataframe(sap_df.head())

        st.write("Pilih kolom untuk validasi:")
        #Select box untuk memilih variabel date dan target
        available_targets = [col for col in sap_df.columns]
        sap_outlet = True if 'profit_center' in sap_df.columns else None
        st.write("Ketersediaan kolom kode outlet:", sap_outlet)
        default_date_index = available_targets.index('posting_date') if 'posting_date' in available_targets else None
        sap_date = st.selectbox("Pilih kolom tanggal", options=available_targets, index=default_date_index)
        sap_tar = st.selectbox("Pilih kolom Indikator Validasi", options=available_targets)

if st.button("Proses Validasi dan Lanjut ke Dashboard"):
    if sc_file is not None and sap_file is not None:
        try:
            # Grouping Dataframes
            sap_df[sap_date] = pd.to_datetime(sap_df[sap_date])
            sc_df[sc_date] = pd.to_datetime(sc_df[sc_date])

            #Grouping SC
            sc_grouped = sc_df.groupby(['kode_outlet', sc_date])[sc_tar].sum().reset_index()
            sc_grouped.columns = ['outlet', 'tanggal', sc_tar]

            # Grouping SAP
            sap_grouped = sap_df.groupby(['profit_center', sap_date])[sap_tar].sum().reset_index()
            sap_grouped.columns = ['outlet', 'tanggal', sap_tar]

            # Validasi
            validasi = pd.merge(sap_grouped, sc_grouped, on=["outlet", "tanggal"], how="outer")
            validasi["selisih"] = validasi[sap_tar] - validasi[sc_tar]


            # Status final dengan 3 kategori
            def classify_status(x):
                if pd.isna(x):
                    return "MISSING"
                elif abs(x) < 1:
                    return "VALID"
                else:
                    return "TIDAK VALID"

            validasi["status"] = validasi["selisih"].apply(classify_status)
            

            # Simpan ke session_state
            st.session_state['sc_tar'] = sc_tar
            st.session_state['sap_tar'] = sap_tar
            st.session_state['sc_grouped'] = sc_grouped
            st.session_state['sap_grouped'] = sap_grouped
            
            # Filter kategori selisih
            def kategori_selisih(x):
                if pd.isna(x):
                    return "MISSING"
                elif x == 0:
                    return "VALID"
                elif 1 <= abs(x) <= 9_999:
                    return "Kecil (1–9.999)"
                elif abs(x) <= 999_999:
                    return "Sedang (10rb–999rb)"
                else:
                    return "Besar (≥1jt)"
            validasi["kategori_selisih"] = validasi["selisih"].apply(kategori_selisih)
            st.session_state['validasi'] = validasi

            # Large Language Model (LLM) Analysis Setup
            load_dotenv()
            os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.1,
            )

            validasi = st.session_state['validasi']

            summary_stats = {
                "total_data": len(validasi),
                "valid": (validasi['status'] == 'VALID').sum(),
                "tidak_valid": (validasi['status'] == 'TIDAK VALID').sum(),
                "missing": (validasi['status'] == 'MISSING').sum(),
                "selisih_terbesar": validasi['selisih'].abs().max(),
                "tanggal_selisih_maks": validasi.loc[validasi['selisih'].abs().idxmax(), 'tanggal']
            }

            kategori_selisih_count = validasi['kategori_selisih'].value_counts().to_dict()

            summary_text = f"""
            Total data: {summary_stats['total_data']}
            VALID: {summary_stats['valid']}
            TIDAK VALID: {summary_stats['tidak_valid']}
            MISSING: {summary_stats['missing']}
            Selisih terbesar: {summary_stats['selisih_terbesar']}

            Distribusi Selisih:
            {kategori_selisih_count}

            Tanggal selisih terbesar: {summary_stats['tanggal_selisih_maks']}
            """

            prompt_template = PromptTemplate.from_template(
                "Buatkan analisis data validasi retur dari data berikut:\n\n{summary}\n\n"
                "Analisis harus mencakup insight, anomali, dan saran untuk perbaikan data.\n"
                "Anggaplah bahwa data yang terjadi pembulatan oleh sistem adalah valid.\n"
                "Berikan penjelasan alasan alasan yang mungkin terjadi pada distribusi selisih.\n"
                "Distribusi selisih data kecil kemungkinan disebabkan oleh pembulatan oleh sistem, tolong sertakan keterangan ini dalam analisis."
            )

            chain = LLMChain(llm=llm, prompt=prompt_template)
            result = chain.run(summary=summary_text)

            # Simpan ke session_state agar bisa diakses dari halaman lain
            st.session_state['llm_analysis'] = result

            #Validation Percetange count
            total = summary_stats["total_data"]
            valid = summary_stats["valid"]
            valid_percent = (valid / total) * 100 if total > 0 else 0
            st.session_state['valid_percent'] = valid_percent

            # Case kalau data valid
            st.success("Data berhasil diproses. Menuju halaman dashboard...")
            st.switch_page("pages/dashboard.py")

        except Exception as e:
            st.error(f"Terjadi kesalahan saat memproses: {e}")
    else:
        st.warning("Silakan upload kedua file sebelum melanjutkan.")


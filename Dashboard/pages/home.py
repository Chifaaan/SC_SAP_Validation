import streamlit as st
st.set_page_config(
    page_title="Home",
    page_icon=":material/home:",
    layout="wide"
)

# Title & Header
st.title("Kimia Farma SC and SAP Validation System")
st.markdown("## Selamat datang di Aplikasi Validasi Data Kimia Farma SC dan SAP")
st.markdown("""
Aplikasi ini dirancang khusus untuk mendukung proses **validasi data** antara sistem **Supply Chain (SC)** Kimia Farma dan sistem **SAP** perusahaan.  
Dengan fokus pada **integritas dan konsistensi data**, platform ini membantu memastikan bahwa informasi yang tercatat di kedua sistem utama berjalan **selaras dan bebas dari kesalahan**.
""")

# Divider
st.markdown("---")

col1, col2 = st.columns(2)
# Tujuan Utama
with col1:
    st.subheader("🔍 Tujuan Utama")
    st.markdown("""
    - Menjamin kesesuaian antara data operasional (SC) dan data finansial (SAP).
    - Meminimalisir potensi human error dalam pencatatan dan pelaporan.
    - Mempercepat proses audit dan rekonsiliasi antar departemen.
    """)

with col2:
    # Fitur Unggulan
    st.subheader("⚙️ Fitur Unggulan")
    st.markdown("""
    - **Validasi Otomatis**  
    Sistem secara otomatis mencocokkan data dari SC dan SAP berdasarkan parameter tertentu (Outlet, Tanggal, Nilai Transaksi, dsb).

    - **Visualisasi Dashboard**  
    Tampilkan hasil validasi secara visual dengan grafik dan tabel yang mudah dipahami.

    - **Deteksi Mismatch**  
    Temukan perbedaan data secara real-time dan dapatkan insight langsung mengenai sumber ketidaksesuaian.
    """)

with col1:
    # Target Pengguna
    st.subheader("🏢 Untuk Siapa Aplikasi Ini?")
    st.markdown("""
    Aplikasi ini dirancang bagi:
    - Tim Supply Chain  
    - Tim Keuangan / Akuntansi  
    - Auditor Internal  
    - Tim IT dan Integrasi Sistem
    """)


# CTA
st.markdown("---")
st.page_link(page="pages/retur.py", label="Retur Validation", icon=":material/info:")
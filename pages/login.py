# login.py

import streamlit as st
import time

# Atur konfigurasi halaman sebagai perintah pertama
st.set_page_config(
    page_title="Login - Validasi Retur",
    page_icon="🔒",
    layout="centered"
)

def check_login(username, password):
    """Fungsi untuk memeriksa kredensial login."""
    # Kredensial di-embed langsung di dalam kode
    # PENTING: Untuk aplikasi produksi, gunakan metode yang lebih aman seperti
    # database atau st.secrets untuk menyimpan kredensial.
    VALID_CREDENTIALS = {
        "sc_user": {
            "password": "user123",
            "role": "Supply Chain",
            "name": "user_sc"
        },
        "acc_user": {
            "password": "user123",
            "role": "Akuntansi",
            "name": "user_acc"
        }
    }
    
    user_data = VALID_CREDENTIALS.get(username)
    if user_data and user_data["password"] == password:
        return True, user_data["role"], user_data["name"]
    return False, None, None

# Inisialisasi session state jika belum ada
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'name' not in st.session_state:
    st.session_state['name'] = None

# Tampilkan form login jika pengguna belum terotentikasi

st.title("Login Aplikasi Validasi Retur")
st.write("Silakan masukkan kredensial Anda.")

username = st.text_input("Username", key="login_username")
password = st.text_input("Password", type="password", key="login_password")

if st.button("Login", key="login_button"):
    is_valid, role, name = check_login(username, password)
    if is_valid:
        # Jika login berhasil, simpan status dan data pengguna di session state
        st.session_state['authenticated'] = True
        st.session_state['role'] = role
        st.session_state['name'] = name
        
        # Tampilkan pesan sukses dan alihkan halaman
        st.success(f"Login berhasil! Selamat datang, {name}.")
        time.sleep(1) # Beri jeda sejenak agar pengguna bisa membaca pesan
        st.switch_page("pages/retur.py")
    else:
        st.error("Username atau password salah. Silakan coba lagi.")

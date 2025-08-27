import streamlit as st
import pandas as pd
import plotly.express as px
import mysql.connector
from streamlit_option_menu import option_menu
from PIL import Image

# ======================
# FUNGSI KONEKSI MYSQL
# ======================
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",        # ganti sesuai MySQL kamu
        password="baru123", # ganti passwordmu
        database="monitoring_aset"
    )

# ======================
# LOGIN FUNCTION
# ======================
def login(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nama, role FROM users WHERE username=%s AND password=%s", (username, password))
    user = cur.fetchone()
    conn.close()
    return user

# ======================
# KONFIGURASI APLIKASI
# ======================
st.set_page_config(page_title="Dashboard Monitoring Aset", layout="wide")

# ======================
# SESSION LOGIN
# ======================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    # ---- HALAMAN LOGIN ----
    st.title("🔐 Login Dashboard Aset")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login(u, p)
        if user:
            st.session_state.user = {"nama": user[0], "role": user[1]}
            st.experimental_rerun()
        else:
            st.error("❌ Username / Password salah")

else:
    # ---- HEADER ----
    st.title("Dashboard Monitoring Aset - Perhutani Divre Jateng")

    # ---- SIDEBAR ----
    with st.sidebar:
        # Tampilkan logo
        logo = Image.open("logo.png")   # pastikan file logo.png ada di folder project
        st.image(logo, width=120)

        # Info user
        st.markdown(f"👤 Login as: **{st.session_state.user['nama']}**")

        # Menu
        selected = option_menu(
            "Menu Utama",
            ["📋 Master Data", "⚠️ Monitoring", "🔒 Logout"],
            icons=["table", "bar-chart", "box-arrow-right"],
            menu_icon="cast",
            default_index=0,
        )

    # ======================
    # MASTER DATA
    # ======================
    if selected == "📋 Master Data":
        st.subheader("📋 Upload & Simpan Data Aset")

        file = st.file_uploader("Upload File Excel", type=["xlsx"])
        if file:
            # Baca Excel
            df = pd.read_excel(file, skiprows=1)

            # Mapping kolom sesuai DB
            mapping = {
                "Nama Aset*": "nama_aset",
                "Nomor Aset*": "nomor_aset",
                "Tanggal Perolehan*": "tahun",
                "Nilai Perolehan*": "nilai",
                "Kondisi Aset*": "kondisi",
                "Alamat": "alamat",
                "Jenis Aset": "jenis_aset",
                "KPH": "kph",
                "Sub KPH": "sub_kph",
                "Luas": "luas"
            }
            df.rename(columns=mapping, inplace=True)

            # Bersihkan data
            df["tahun"] = pd.to_datetime(df["tahun"], errors="coerce").dt.year
            df["nilai"] = (
                df["nilai"].astype(str).str.replace(r"[^0-9]", "", regex=True)
            )
            df["nilai"] = pd.to_numeric(df["nilai"], errors="coerce").fillna(0)
            if "luas" in df.columns:
                df["luas"] = pd.to_numeric(df["luas"], errors="coerce").fillna(0)

            st.dataframe(df.head())

            if st.button("💾 Simpan ke Database"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM assets")  # hapus data lama
                for _, row in df.iterrows():
                    cur.execute("""
                        INSERT INTO assets (nama_aset, nomor_aset, tahun, nilai, kondisi, alamat, jenis_aset, kph, sub_kph, luas)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        row.get("nama_aset", ""),
                        row.get("nomor_aset", ""),
                        int(row["tahun"]) if not pd.isna(row["tahun"]) else None,
                        row.get("nilai", 0),
                        row.get("kondisi", ""),
                        row.get("alamat", ""),
                        row.get("jenis_aset", ""),
                        row.get("kph", ""),
                        row.get("sub_kph", ""),
                        row.get("luas", 0)
                    ))
                conn.commit()
                conn.close()
                st.success("✅ Data berhasil disimpan ke database!")

    # ======================
    # MONITORING
    # ======================
    elif selected == "⚠️ Monitoring":
        st.subheader("⚠️ Monitoring Aset")

        conn = get_connection()
        df = pd.read_sql("SELECT * FROM assets", conn)
        conn.close()

        if not df.empty:
            # Filter KPH
            kph = st.selectbox("Pilih KPH", ["Semua"] + sorted(df["kph"].dropna().unique().tolist()))
            if kph != "Semua":
                df = df[df["kph"] == kph]

            # Filter Jenis Aset
            jenis = st.multiselect("Jenis Aset", df["jenis_aset"].dropna().unique())
            if jenis:
                df = df[df["jenis_aset"].isin(jenis)]

            # Statistik
            col1, col2, col3 = st.columns(3)
            col1.metric("Jumlah Aset", len(df))
            col2.metric("Total Nilai", f"Rp {df['nilai'].sum():,.0f}")
            col3.metric("Data Tidak Lengkap", df.isnull().sum().sum())

            if not df.empty:
                aset_max = df.loc[df["nilai"].idxmax()]
                aset_min = df.loc[df["nilai"].idxmin()]
                st.write(f"💰 Nilai Tertinggi: {aset_max['nama_aset']} (Rp {aset_max['nilai']:,.0f})")
                st.write(f"💸 Nilai Terendah: {aset_min['nama_aset']} (Rp {aset_min['nilai']:,.0f})")

            # Grafik kondisi
            fig = px.histogram(df, x="kondisi", y="nilai", color="jenis_aset", title="Nilai Aset per Kondisi & Jenis", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

            # Pie chart jenis aset
            fig2 = px.pie(df, names="jenis_aset", values="nilai", title="Distribusi Nilai per Jenis Aset")
            st.plotly_chart(fig2, use_container_width=True)

            # Export
            st.download_button(
                "⬇️ Download Hasil Monitoring",
                df.to_csv(index=False).encode("utf-8"),
                "monitoring_aset.csv",
                "text/csv"
            )
        else:
            st.warning("⚠️ Belum ada data aset di database. Upload dulu di menu Master Data.")

    # ======================
    # LOGOUT
    # ======================
    elif selected == "🔒 Logout":
        st.session_state.user = None
        st.experimental_rerun()

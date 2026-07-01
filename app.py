# ============================================================
# app.py — Backend utama aplikasi pencatat keuangan
# Versi multi-user dengan sistem login
# ============================================================

from flask import Flask, render_template, request, redirect, url_for, session
# session : untuk menyimpan info user yang sedang login
# (seperti "ingatan" sementara siapa yang sedang pakai aplikasi)

import json
import os
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash
# generate_password_hash : mengubah password asli menjadi kode terenkripsi
# check_password_hash    : membandingkan password yang diketik dengan yang terenkripsi

# ============================================================
# Inisialisasi Flask
# ============================================================
app = Flask(__name__)

app.secret_key = "dompetku_secret_2024"
# secret_key dibutuhkan Flask untuk mengamankan session
# Boleh diganti dengan teks apapun, tapi jangan dibagikan ke orang lain

DATA_FILE = "data.json"

# ============================================================
# Struktur data.json untuk multi-user:
# {
#   "users": {
#     "budi": {
#       "password": "hash...",
#       "penyimpanan": {"Cash": 500000},
#       "transaksi": [...]
#     }
#   }
# }
# ============================================================

def load_data():
    # Jika file belum ada, buat struktur awal
    if not os.path.exists(DATA_FILE):
        data_awal = {"users": {}}
        save_data(data_awal)
        return data_awal
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user_data():
    # Ambil data milik user yang sedang login
    data = load_data()
    username = session.get("username")
    if not username or username not in data["users"]:
        return None
    return data["users"][username]

def save_user_data(user_data):
    # Simpan data milik user yang sedang login
    data = load_data()
    username = session.get("username")
    data["users"][username] = user_data
    save_data(data)

# ============================================================
# ROUTE: Halaman Login & Daftar
# ============================================================
@app.route("/", methods=["GET", "POST"])
def login():
    # Jika sudah login, langsung ke dashboard
    if "username" in session:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        data     = load_data()

        if username in data["users"]:
            # Cek password
            if check_password_hash(data["users"][username]["password"], password):
                session["username"] = username
                return redirect(url_for("dashboard"))
            else:
                error = "Password salah. Coba lagi."
        else:
            error = "Akun tidak ditemukan. Silakan daftar terlebih dahulu."

    return render_template("login.html", mode="login", error=error)

@app.route("/daftar", methods=["GET", "POST"])
def daftar():
    # Jika sudah login, langsung ke dashboard
    if "username" in session:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        username  = request.form["username"].strip().lower()
        password  = request.form["password"]
        password2 = request.form["password2"]
        data      = load_data()

        # Validasi
        if len(username) < 3:
            error = "Username minimal 3 karakter."
        elif username in data["users"]:
            error = "Username sudah dipakai. Pilih yang lain."
        elif len(password) < 6:
            error = "Password minimal 6 karakter."
        elif password != password2:
            error = "Password tidak cocok. Periksa kembali."
        else:
            # Buat akun baru
            data["users"][username] = {
                "password"    : generate_password_hash(password),
                "penyimpanan" : {},
                "transaksi"   : []
            }
            save_data(data)
            session["username"] = username
            return redirect(url_for("dashboard"))

    return render_template("login.html", mode="daftar", error=error)

@app.route("/logout")
def logout():
    session.pop("username", None)
    # Hapus info login dari session
    return redirect(url_for("login"))

# ============================================================
# ROUTE: Dashboard (Halaman Utama setelah login)
# ============================================================
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    user   = get_user_data()
    bulan_ini = datetime.now().strftime("%Y-%m")
    total_saldo = sum(user["penyimpanan"].values())

    return render_template("index.html",
                           username=session["username"],
                           penyimpanan=user["penyimpanan"],
                           transaksi=user["transaksi"],
                           total_saldo=total_saldo,
                           bulan_ini=bulan_ini)

# ============================================================
# ROUTE: Penyimpanan
# ============================================================
@app.route("/penyimpanan")
def penyimpanan():
    if "username" not in session:
        return redirect(url_for("login"))
    user = get_user_data()
    return render_template("penyimpanan.html",
                           username=session["username"],
                           penyimpanan=user["penyimpanan"])

@app.route("/penyimpanan/tambah", methods=["POST"])
def tambah_penyimpanan():
    if "username" not in session:
        return redirect(url_for("login"))
    nama = request.form["nama"].strip()
    user = get_user_data()
    if nama and nama not in user["penyimpanan"]:
        user["penyimpanan"][nama] = 0
        save_user_data(user)
    return redirect(url_for("penyimpanan"))

@app.route("/penyimpanan/hapus/<nama>")
def hapus_penyimpanan(nama):
    if "username" not in session:
        return redirect(url_for("login"))
    user = get_user_data()
    if nama in user["penyimpanan"]:
        del user["penyimpanan"][nama]
        save_user_data(user)
    return redirect(url_for("penyimpanan"))

# ============================================================
# ROUTE: Transaksi
# ============================================================
@app.route("/transaksi")
def transaksi():
    if "username" not in session:
        return redirect(url_for("login"))
    user = get_user_data()
    return render_template("transaksi.html",
                           username=session["username"],
                           penyimpanan=user["penyimpanan"])

@app.route("/transaksi/tambah", methods=["POST"])
def tambah_transaksi():
    if "username" not in session:
        return redirect(url_for("login"))

    jenis      = request.form["jenis"]
    nominal    = int(request.form["nominal"])
    dari       = request.form.get("dari", "")
    tujuan     = request.form.get("tujuan", "")
    keterangan = request.form.get("keterangan", "")
    tanggal    = datetime.now().strftime("%Y-%m-%d")
    user       = get_user_data()

    if jenis == "pemasukan":
        user["penyimpanan"][tujuan] += nominal
    elif jenis == "pengeluaran":
        user["penyimpanan"][dari] -= nominal
    elif jenis == "pindah":
        user["penyimpanan"][dari]   -= nominal
        user["penyimpanan"][tujuan] += nominal

    user["transaksi"].append({
        "jenis"     : jenis,
        "nominal"   : nominal,
        "dari"      : dari,
        "tujuan"    : tujuan,
        "keterangan": keterangan,
        "tanggal"   : tanggal
    })

    save_user_data(user)
    return redirect(url_for("transaksi"))

# ============================================================
# ROUTE: Laporan
# ============================================================
@app.route("/laporan")
def laporan():
    if "username" not in session:
        return redirect(url_for("login"))
    user = get_user_data()
    return render_template("laporan.html",
                           username=session["username"],
                           penyimpanan=user["penyimpanan"],
                           transaksi=user["transaksi"])

# ============================================================
# Jalankan aplikasi
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
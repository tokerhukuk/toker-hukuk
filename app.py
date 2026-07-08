import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import bcrypt

# ====================== STREAMLIT SAYFA AYARLARI ======================
st.set_page_config(
    page_title="TOKER HUKUK BÜROSU",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "TOKER HUKUK BÜROSU Otomasyon Sistemi"
    }
)

# Sağ üstteki butonları (Share, Deploy vb.) gizle
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    .css-1v3fvcr {display:none;}  /* Ekstra menü öğeleri */
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ====================== OTURUM YÖNETİMİ ======================
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now()

def update_activity():
    st.session_state.last_activity = datetime.now()

def check_inactivity_timeout():
    if st.session_state.get('logged_in') and st.session_state.get('last_activity'):
        if datetime.now() - st.session_state.last_activity > timedelta(minutes=5):
            st.session_state.logged_in = False
            st.error("⚠️ 5 dakika işlem yapılmadığı için oturum kapatıldı.")
            st.rerun()

# ====================== VERİTABANI ======================
def get_db_connection():
    return sqlite3.connect('hukuk_otomasyon.db')

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, 
                password TEXT, 
                role TEXT DEFAULT 'user',
                created_at TEXT)''')
    
    c.execute("PRAGMA table_info(users)")
    if 'created_at' not in [col[1] for col in c.fetchall()]:
        c.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
    
    c.execute("SELECT COUNT(*) FROM users WHERE username=?", ("admin",))
    if c.fetchone()[0] == 0:
        hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
        c.execute("INSERT INTO users (username, password, role, created_at) VALUES (?,?,?,?)",
                 ("admin", hashed, "admin", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    # Diğer tablolar
    c.execute('''CREATE TABLE IF NOT EXISTS musteri (
                id INTEGER PRIMARY KEY, foy_no TEXT, ad_soyad TEXT NOT NULL,
                tc_no TEXT UNIQUE, telefon TEXT, email TEXT, adres TEXT,
                kayit_tarihi TEXT DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS dava (
                id INTEGER PRIMARY KEY, foy_no TEXT, dosya_no TEXT UNIQUE,
                musteri_id INTEGER, dava_turu TEXT, konu TEXT, acilis_tarihi TEXT,
                durum TEXT, mahkeme TEXT, aktarim_bilgisi TEXT,
                FOREIGN KEY (musteri_id) REFERENCES musteri(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS durusma (
                id INTEGER PRIMARY KEY, dava_id INTEGER, tur TEXT DEFAULT 'Duruşma',
                tarih TEXT, saat TEXT, aciklama TEXT,
                FOREIGN KEY (dava_id) REFERENCES dava(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS gorev (
                id INTEGER PRIMARY KEY, baslik TEXT, aciklama TEXT, son_tarih TEXT,
                oncelik TEXT, durum TEXT DEFAULT 'Bekliyor', atanan_kullanici TEXT, dava_id INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS belgeler (
                id INTEGER PRIMARY KEY, belge_adi TEXT NOT NULL, dosya_yolu TEXT NOT NULL,
                belge_turu TEXT, aciklama TEXT, dava_id INTEGER, yukleme_tarihi TEXT,
                FOREIGN KEY (dava_id) REFERENCES dava(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cari_hesap (
                id INTEGER PRIMARY KEY, musteri_id INTEGER, dava_id INTEGER,
                islem_tarihi TEXT, islem_turu TEXT, gider_turu TEXT, harc_turu TEXT,
                adet INTEGER DEFAULT 1, tutar REAL, aciklama TEXT,
                bakiye REAL DEFAULT 0,
                FOREIGN KEY (musteri_id) REFERENCES musteri(id),
                FOREIGN KEY (dava_id) REFERENCES dava(id))''')
    
    conn.commit()
    conn.close()

# ====================== KULLANICI FONKSİYONLARI ======================
def login_user(username, password):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT password, role FROM users WHERE username=?", (username,))
        result = c.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0]):
            return True, result[1]
    return False, None

def change_password(username, old_password, new_password):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        result = c.fetchone()
        if result and bcrypt.checkpw(old_password.encode('utf-8'), result[0]):
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            c.execute("UPDATE users SET password=? WHERE username=?", (hashed, username))
            conn.commit()
            return True
    return False

def get_all_users():
    with get_db_connection() as conn:
        return pd.read_sql_query("SELECT username, role, COALESCE(created_at, '---') as created_at FROM users ORDER BY username", conn)

def delete_user(username):
    if username == "admin":
        return False
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
    return True

# ====================== UYGULAMA ======================
init_db()
init_session_state()
check_inactivity_timeout()

if not st.session_state.logged_in:
    st.set_page_config(page_title="TOKER HUKUK - Giriş", layout="centered", page_icon="⚖️")
    
    st.title("⚖️ TOKER HUKUK")
    st.subheader("Büro Otomasyon Sistemi")
    
    with st.form("login_form"):
        st.markdown("### 🔑 Giriş Yap")
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        
        submitted = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
        
        if submitted:
            success, role = login_user(username, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = role
                st.session_state.last_activity = datetime.now()
                st.success("Hoş geldiniz!")
                st.rerun()
            else:
                st.error("❌ Kullanıcı adı veya şifre hatalı!")
    
    st.stop()

update_activity()

# ====================== ANA UYGULAMA ======================
st.set_page_config(page_title="TOKER HUKUK", layout="wide", page_icon="⚖️")

with st.sidebar:
    st.success(f"👤 {st.session_state.username} ({st.session_state.role})")
    st.divider()
    menu = st.selectbox("📌 Menü", [
        "Ana Sayfa", "Müvekkil Yönetimi", "Dava/Dosya Yönetimi", 
        "Duruşma Takvimi", "Görevler", "Belgeler", "Raporlar", 
        "Hesaplar", "Yedekleme", "Ayarlar", "🔧 Kullanıcı Yönetimi"
    ])
    st.divider()
    if st.button("🚪 Çıkış Yap"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.title("⚖️ TOKER HUKUK BÜROSU")

# ====================== KULLANICI YÖNETİMİ ======================
if menu == "🔧 Kullanıcı Yönetimi":
    if st.session_state.role != "admin":
        st.error("Bu sayfaya sadece admin erişebilir!")
        st.stop()
    
    st.header("👥 Kullanıcı Yönetimi")
    tab1, tab2, tab3 = st.tabs(["Tüm Kullanıcılar", "Yeni Kullanıcı Ekle", "Şifre Değiştir"])
    
    with tab1:
        users_df = get_all_users()
        st.dataframe(users_df, use_container_width=True, hide_index=True)
        
        to_delete = st.selectbox("Silinecek Kullanıcı", users_df['username'].tolist())
        if st.button("🗑️ Sil", type="secondary"):
            if delete_user(to_delete):
                st.success(f"{to_delete} silindi.")
                st.rerun()
            else:
                st.error("Admin hesabı silinemez!")
    
    with tab2:
        with st.form("new_user"):
            nu = st.text_input("Kullanıcı Adı")
            np = st.text_input("Şifre", type="password")
            nr = st.selectbox("Rol", ["user", "admin"])
            if st.form_submit_button("Ekle"):
                try:
                    hashed = bcrypt.hashpw(np.encode('utf-8'), bcrypt.gensalt())
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("""INSERT INTO users (username, password, role, created_at)
                                    VALUES (?, ?, ?, ?)""",
                                (nu, hashed, nr, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                    st.success("Kullanıcı eklendi!")
                    st.rerun()
                except:
                    st.error("Kullanıcı adı zaten var!")
    
    with tab3:
        st.subheader("Şifre Değiştir")
        with st.form("change_pass"):
            old = st.text_input("Mevcut Şifre", type="password")
            newp = st.text_input("Yeni Şifre", type="password")
            if st.form_submit_button("Güncelle"):
                if change_password(st.session_state.username, old, newp):
                    st.success("Şifre değiştirildi!")
                else:
                    st.error("Mevcut şifre yanlış!")
# ====================== ANA SAYFA ======================
if menu == "Ana Sayfa":
    st.header("🏠 Ana Sayfa")
    
    # ====================== İSTATİSTİKLER ======================
    with get_db_connection() as conn:
        toplam_muvekkil = pd.read_sql_query("SELECT COUNT(*) as sayi FROM musteri", conn).iloc[0]['sayi']
        aktif_dava = pd.read_sql_query(
            "SELECT COUNT(*) as sayi FROM dava WHERE durum IN ('Açık', 'İstinaf', 'Temyiz')", 
            conn).iloc[0]['sayi']
        yaklasan_durusma = pd.read_sql_query(
            "SELECT COUNT(*) as sayi FROM durusma WHERE tarih >= date('now')", 
            conn).iloc[0]['sayi']
        bekleyen_gorev = pd.read_sql_query(
            "SELECT COUNT(*) as sayi FROM gorev WHERE durum = 'Bekliyor'", 
            conn).iloc[0]['sayi']

    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        st.metric("Toplam Müvekkil", f"{toplam_muvekkil}", "👥")
    with col2: 
        st.metric("Aktif Dava", f"{aktif_dava}", "⚖️")
    with col3: 
        st.metric("Yaklaşan Duruşma", f"{yaklasan_durusma}", "📅")
    with col4: 
        st.metric("Bekleyen Görev", f"{bekleyen_gorev}", "📌")
    
    st.divider()
    st.subheader("📅 Duruşma ve Görev Takvimi")

    # ====================== TAKVİM ======================
    try:
        from streamlit_calendar import calendar
    except ImportError:
        st.error("streamlit-calendar kütüphanesi yüklü değil. Komut: `pip install streamlit-calendar`")
        st.stop()

    # Takvim anahtarı
    if "calendar_key" not in st.session_state:
        st.session_state.calendar_key = f"cal_{int(datetime.now().timestamp())}"

    calendar_options = {
        "initialView": "dayGridMonth",
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek,timeGridDay"},
        "height": "700px", 
        "dayMaxEvents": 6, 
        "locale": "tr"
    }

    # Verileri çek
    with get_db_connection() as conn:
        durusmalar = pd.read_sql_query("""
            SELECT dur.id, d.mahkeme, d.dosya_no, m.ad_soyad as musteri, 
                   dur.tarih as start, dur.saat, dur.aciklama, dur.tur
            FROM durusma dur
            LEFT JOIN dava d ON dur.dava_id = d.id
            LEFT JOIN musteri m ON d.musteri_id = m.id
        """, conn)

        gorevler = pd.read_sql_query("""
            SELECT g.id, g.baslik, g.son_tarih as start, g.oncelik, g.aciklama, g.durum,
                   d.mahkeme, d.dosya_no
            FROM gorev g 
            LEFT JOIN dava d ON g.dava_id = d.id
        """, conn)

    # Olayları hazırla
    all_events = []

    for _, row in durusmalar.iterrows():
        all_events.append({
            "id": f"dur_{row['id']}",
            "title": f"{row.get('tur', 'Duruşma')} - {row.get('mahkeme','')} - {row.get('dosya_no','')}",
            "start": row['start'],
            "color": "#FFEB3B",
            "extendedProps": {**row.to_dict(), "type": "durusma"}
        })

    for _, row in gorevler.iterrows():
        all_events.append({
            "id": f"gorev_{row['id']}",
            "title": f"📌 {row['baslik']}",
            "start": row['start'],
            "color": "#FF5252",
            "extendedProps": {**row.to_dict(), "type": "gorev"}
        })

    # Takvimi göster
    selected = calendar(events=all_events, options=calendar_options, key=st.session_state.calendar_key)

    # Etkinlik tıklama
    if selected and "eventClick" in selected:
        event = selected["eventClick"]["event"]
        props = event.get("extendedProps", {})

        @st.dialog("📅 Etkinlik Detayı")
        def show_detail():
            if props.get("type") == "durusma":
                st.subheader(props.get("tur", "DURUŞMA").upper())
                st.write(f"**Mahkeme:** {props.get('mahkeme', '')}")
                st.write(f"**Dosya No:** {props.get('dosya_no', '')}")
                st.write(f"**Tarih:** {event.get('start', '')}")
                st.write(f"**Saat:** {props.get('saat', 'Belirtilmemiş')}")
                st.write(f"**Müvekkil:** {props.get('musteri', '')}")
                st.write(f"**Açıklama:** {props.get('aciklama', 'Açıklama yok')}")
            else:
                st.subheader("GÖREV")
                st.write(f"**Görev:** {event.get('title', '').replace('📌 ', '')}")
                st.write(f"**İlgili Mahkeme:** {props.get('mahkeme', 'Bağlı dava yok')}")
                st.write(f"**Dosya No:** {props.get('dosya_no', 'Bağlı dava yok')}")
                st.write(f"**Tarih:** {event.get('start', '')}")
                st.write(f"**Öncelik:** {props.get('oncelik', 'Belirtilmemiş')}")
                st.write(f"**Durum:** {props.get('durum', 'Bekliyor')}")
                st.write(f"**Açıklama:** {props.get('aciklama', 'Açıklama yok')}")
        
        show_detail()

    st.divider()

# ====================== MÜVEKKİL YÖNETİMİ ======================
elif menu == "Müvekkil Yönetimi":
    st.header("👤 Müvekkil Yönetimi")
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Müvekkil Ekle", "📋 Müvekkil Listesi", "✏️ Düzenle / Sil"])
    
    # ====================== TAB 1: YENİ MÜVEKKİL EKLE ======================
    with tab1:
        st.subheader("Yeni Müvekkil Ekle")
        with st.form("yeni_musteri_form", clear_on_submit=True):
            foy_no = st.text_input("FÖY NO *")
            ad = st.text_input("AD SOYAD *")
            tc = st.text_input("TC KİMLİK NO *")
            telefon = st.text_input("TELEFON NUMARASI *")
            email = st.text_input("E-POSTA ADRESİ")
            adres = st.text_input("ADRES")
            
            submitted = st.form_submit_button("💾 MÜVEKKİLİ KAYDET", type="primary")
            
            if submitted:
                if not foy_no or not ad or not tc or not telefon:
                    st.error("❌ FÖY NO, AD SOYAD, TC ve TELEFON zorunludur!")
                else:
                    try:
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute("""INSERT INTO musteri (foy_no, ad_soyad, tc_no, telefon, email, adres) 
                                        VALUES (?, ?, ?, ?, ?, ?)""",
                                     (foy_no.strip(), ad.strip(), tc.strip(), telefon.strip(), 
                                      email.strip() if email else None, adres.strip() if adres else None))
                            conn.commit()
                        st.success("✅ MÜVEKKİL BAŞARIYLA KAYDEDİLDİ!")
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Bu TC Kimlik No daha önce kaydedilmiş!")

    # ====================== TAB 2: MÜVEKKİL LİSTESİ ======================
    with tab2:
        st.subheader("TÜM MÜVEKKİLLER")
        arama = st.text_input("🔍 MÜVEKKİL ARA", "")
        
        query = "SELECT foy_no, ad_soyad, tc_no, telefon, email, adres FROM musteri"
        if arama:
            query += f" WHERE ad_soyad LIKE ? OR tc_no LIKE ? OR telefon LIKE ? OR foy_no LIKE ?"
            params = (f"%{arama}%", f"%{arama}%", f"%{arama}%", f"%{arama}%")
        else:
            params = None

        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            df_display = df.rename(columns={
                "foy_no": "Föy No", "ad_soyad": "Ad Soyad", "tc_no": "T.C. No",
                "telefon": "Telefon No", "email": "E-mail", "adres": "Adres"
            })
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            st.caption(f"**Toplam Müvekkil:** {len(df)}")
        else:
            st.info("Henüz müvekkil bulunmuyor.")

    # ====================== TAB 3: DÜZENLE / SİL ======================
    with tab3:
        st.subheader("MÜVEKKİL DÜZENLE VEYA SİL")
        
        with get_db_connection() as conn:
            df_list = pd.read_sql_query("SELECT id, foy_no, ad_soyad FROM musteri ORDER BY ad_soyad", conn)
        
        if not df_list.empty:
            secilen_musteri = st.selectbox("Seçin", options=df_list['id'],
                format_func=lambda x: f"{df_list[df_list['id'] == x]['foy_no'].values[0] or ''} - {df_list[df_list['id'] == x]['ad_soyad'].values[0]}")
            
            with get_db_connection() as conn:
                secili = pd.read_sql_query("SELECT * FROM musteri WHERE id = ?", conn, params=(secilen_musteri,)).iloc[0]
            
            with st.form("duzenle_form"):
                yeni_foy_no = st.text_input("Föy No", value=secili.get('foy_no', ''))
                yeni_ad = st.text_input("AD SOYAD", value=secili['ad_soyad'])
                yeni_tc = st.text_input("TC KİMLİK NO", value=secili['tc_no'])
                yeni_tel = st.text_input("TELEFON", value=secili['telefon'])
                yeni_email = st.text_input("E-POSTA", value=secili.get('email', ''))
                yeni_adres = st.text_area("ADRES", value=secili.get('adres', ''))
                
                guncelle = st.form_submit_button("💾 GÜNCELLE", type="primary")
                sil = st.form_submit_button("🗑️ SİL", type="secondary")
                
                if guncelle:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("""UPDATE musteri SET foy_no=?, ad_soyad=?, tc_no=?, telefon=?, email=?, adres=? WHERE id=?""",
                                 (yeni_foy_no, yeni_ad, yeni_tc, yeni_tel, yeni_email, yeni_adres, secilen_musteri))
                        conn.commit()
                    st.success("✅ GÜNCELLENDİ!")
                    st.rerun()
                
                if sil and st.checkbox("Silmek istediğinize emin misiniz?"):
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("DELETE FROM musteri WHERE id=?", (secilen_musteri,))
                        conn.commit()
                    st.success("🗑️ SİLİNDİ!")
                    st.rerun()
        else:
            st.info("Henüz kayıtlı müvekkil yok.")

# ====================== DAVA/DOSYA YÖNETİMİ ======================
elif menu == "Dava/Dosya Yönetimi":
    st.header("⚖️ Dava ve Dosya Yönetimi")
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Dava Ekle", "📋 Dava Listesi", "✏️ Düzenle / Sil"])
    
    # ====================== TAB 1: YENİ DAVA EKLE ======================
    with tab1:
        st.subheader("Yeni Dava Ekle")
        
        with get_db_connection() as conn:
            musteriler = pd.read_sql_query("SELECT id, ad_soyad FROM musteri ORDER BY ad_soyad", conn)
        
        with st.form("yeni_dava_form", clear_on_submit=True):
            foy_no = st.text_input("Föy No *")
            mahkeme = st.text_input("MAHKEME ADI *")
            dosya_no = st.text_input("DOSYA NO *")
            
            musteri_sec = st.selectbox("MÜVEKKİL", 
                options=musteriler['id'] if not musteriler.empty else [],
                format_func=lambda x: musteriler[musteriler['id'] == x]['ad_soyad'].values[0] if not musteriler.empty else "")
            
            dava_turu = st.selectbox("DAVA TÜRÜ", ["Hukuk", "Ceza", "İcra", "Aile", "İdare", "Ticaret"])
            durum = st.selectbox("DURUM", ["Açık", "Kapalı", "İstinaf", "Temyiz", "Dosyaya aktarıldı"])
            
            submitted = st.form_submit_button("💾 DAVAYI KAYDET", type="primary")
            
            if submitted:
                if not foy_no or not dosya_no or not musteri_sec or not mahkeme:
                    st.error("❌ FÖY NO, DOSYA NO, MAHKEME ve MÜVEKKİL zorunludur!")
                else:
                    try:
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute("""INSERT INTO dava (foy_no, dosya_no, musteri_id, dava_turu, durum, mahkeme) 
                                        VALUES (?, ?, ?, ?, ?, ?)""",
                                     (foy_no.strip(), dosya_no.strip(), musteri_sec, dava_turu, durum, mahkeme.strip()))
                            conn.commit()
                        st.success("✅ DAVA BAŞARIYLA KAYDEDİLDİ!")
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Bu dosya numarası daha önce kullanılmış!")

    # ====================== TAB 2: DAVA LİSTESİ ======================
    with tab2:
        st.subheader("Tüm Davalar")
        arama = st.text_input("🔍 Dava Ara", "")
        
        query = """SELECT d.foy_no, d.dosya_no, d.mahkeme, m.ad_soyad as musteri, 
                          d.dava_turu, d.durum, d.aktarim_bilgisi
                   FROM dava d LEFT JOIN musteri m ON d.musteri_id = m.id"""
        
        if arama:
            query += " WHERE d.foy_no LIKE ? OR d.dosya_no LIKE ? OR d.mahkeme LIKE ? OR m.ad_soyad LIKE ?"
            params = (f"%{arama}%", f"%{arama}%", f"%{arama}%", f"%{arama}%")
        else:
            params = None

        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            df_display = df.rename(columns={
                "foy_no": "Föy No", "dosya_no": "DOSYA NO", "mahkeme": "MAHKEME ADI",
                "musteri": "MÜVEKKİL", "dava_turu": "DAVA TÜRÜ", "durum": "DURUM"
            })
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Henüz dava kaydı bulunmuyor.")

    # ====================== TAB 3: DÜZENLE / SİL ======================
    with tab3:
        st.subheader("Dava Düzenle veya Sil")
        
        with get_db_connection() as conn:
            df_list = pd.read_sql_query("""SELECT d.id, d.foy_no, d.mahkeme, d.dosya_no, m.ad_soyad as musteri
                                           FROM dava d LEFT JOIN musteri m ON d.musteri_id = m.id 
                                           ORDER BY d.mahkeme""", conn)
        
        if not df_list.empty:
            secilen_dava = st.selectbox("Seçin", options=df_list['id'],
                format_func=lambda x: f"{df_list[df_list['id'] == x]['mahkeme'].values[0]} - {df_list[df_list['id'] == x]['dosya_no'].values[0]}")
            
            with get_db_connection() as conn:
                secili = pd.read_sql_query("SELECT * FROM dava WHERE id = ?", conn, params=(secilen_dava,)).iloc[0]
            
            with st.form("duzenle_dava_form"):
                yeni_foy_no = st.text_input("Föy No", value=secili.get('foy_no', ''))
                yeni_dosya_no = st.text_input("DOSYA NO", value=secili['dosya_no'])
                yeni_mahkeme = st.text_input("MAHKEME", value=secili['mahkeme'])
                yeni_durum = st.selectbox("DURUM", ["Açık", "Kapalı", "İstinaf", "Temyiz", "Dosyaya aktarıldı"], 
                                        index=["Açık", "Kapalı", "İstinaf", "Temyiz", "Dosyaya aktarıldı"].index(secili['durum']))
                
                guncelle = st.form_submit_button("💾 GÜNCELLE", type="primary")
                sil = st.form_submit_button("🗑️ SİL", type="secondary")
                
                if guncelle:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("""UPDATE dava SET foy_no=?, dosya_no=?, mahkeme=?, durum=? WHERE id=?""",
                                 (yeni_foy_no, yeni_dosya_no, yeni_mahkeme, yeni_durum, secilen_dava))
                        conn.commit()
                    st.success("✅ GÜNCELLENDİ!")
                    st.rerun()
                
                if sil and st.checkbox("Silmek istediğinize emin misiniz?"):
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("DELETE FROM dava WHERE id=?", (secilen_dava,))
                        conn.commit()
                    st.success("🗑️ SİLİNDİ!")
                    st.rerun()
        else:
            st.info("Henüz kayıtlı dava yok.")

# ====================== DURUŞMA TAKVİMİ ======================
elif menu == "Duruşma Takvimi":
    st.header("⏰ Duruşma / Keşif Takvimi")
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Ekle", "📋 Yaklaşanlar", "✏️ Düzenle / Sil"])
    
    # ====================== TAB 1: YENİ DURUŞMA EKLE ======================
    with tab1:
        st.subheader("Yeni Duruşma/Keşif Ekle")
        
        with get_db_connection() as conn:
            davalar = pd.read_sql_query("""
                SELECT d.id, d.dosya_no, d.mahkeme, m.ad_soyad 
                FROM dava d 
                LEFT JOIN musteri m ON d.musteri_id = m.id 
                ORDER BY d.mahkeme
            """, conn)
        
        with st.form("yeni_durusma"):
            dava_sec = st.selectbox("Dava / Dosya", 
                options=davalar['id'] if not davalar.empty else [],
                format_func=lambda x: f"{davalar[davalar['id']==x]['mahkeme'].values[0]} - {davalar[davalar['id']==x]['dosya_no'].values[0]}")
            
            tur = st.selectbox("Tür", ["Duruşma", "Keşif"])
            tarih = st.date_input("Tarih")
            saat = st.time_input("Saat")
            aciklama = st.text_area("Açıklama")
            
            if st.form_submit_button("💾 Kaydet", type="primary"):
                if not dava_sec:
                    st.error("Lütfen bir dava seçin!")
                else:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("""INSERT INTO durusma (dava_id, tur, tarih, saat, aciklama) 
                                    VALUES (?, ?, ?, ?, ?)""",
                                 (dava_sec, tur, str(tarih), str(saat), aciklama))
                        conn.commit()
                    st.success(f"✅ {tur} başarıyla eklendi!")
                    st.rerun()

    # ====================== TAB 2: YAKLAŞAN DURUŞMALAR (MAHKEME EKLENDİ) ======================
    with tab2:
        st.subheader("Yaklaşan Duruşma ve Keşifler")
        
        with get_db_connection() as conn:
            yaklasan = pd.read_sql_query("""
                SELECT 
                    d.mahkeme as "Mahkeme",
                    d.dosya_no as "Dosya No", 
                    m.ad_soyad as "Müvekkil", 
                    dur.tur as "Tür", 
                    dur.tarih as "Tarih", 
                    dur.saat as "Saat", 
                    dur.aciklama as "Açıklama"
                FROM durusma dur 
                LEFT JOIN dava d ON dur.dava_id = d.id
                LEFT JOIN musteri m ON d.musteri_id = m.id
                WHERE dur.tarih >= date('now') 
                ORDER BY dur.tarih ASC, dur.saat ASC
            """, conn)
        
        if not yaklasan.empty:
            st.dataframe(yaklasan, use_container_width=True, hide_index=True)
            
            # Özet bilgi
            st.caption(f"**Toplam Yaklaşan Duruşma/Keşif:** {len(yaklasan)}")
        else:
            st.info("📅 Yaklaşan herhangi bir duruşma veya keşif bulunmuyor.")

    # ====================== TAB 3: DÜZENLE / SİL ======================
    with tab3:
        st.subheader("Duruşma/Keşif Düzenle veya Sil")
        
        with get_db_connection() as conn:
            df_list = pd.read_sql_query("""
                SELECT 
                    dur.id, 
                    d.mahkeme, 
                    d.dosya_no, 
                    m.ad_soyad as musteri, 
                    dur.tur, 
                    dur.tarih,
                    dur.saat
                FROM durusma dur 
                LEFT JOIN dava d ON dur.dava_id = d.id
                LEFT JOIN musteri m ON d.musteri_id = m.id 
                ORDER BY dur.tarih DESC
            """, conn)
        
        if not df_list.empty:
            secilen = st.selectbox("Seçin", options=df_list['id'],
                format_func=lambda x: f"{df_list[df_list['id'] == x]['tur'].values[0]} - "
                                     f"{df_list[df_list['id'] == x]['mahkeme'].values[0]} - "
                                     f"{df_list[df_list['id'] == x]['dosya_no'].values[0]}")
            
            with get_db_connection() as conn:
                secili = pd.read_sql_query("SELECT * FROM durusma WHERE id = ?", conn, params=(secilen,)).iloc[0]
            
            with st.form("duzenle_durusma"):
                yeni_tur = st.selectbox("Tür", ["Duruşma", "Keşif"], 
                                      index=["Duruşma", "Keşif"].index(secili['tur']))
                yeni_tarih = st.date_input("Tarih", value=datetime.strptime(secili['tarih'], "%Y-%m-%d").date())
                yeni_saat = st.time_input("Saat", value=datetime.strptime(secili['saat'], "%H:%M:%S").time())
                yeni_aciklama = st.text_area("Açıklama", value=secili.get('aciklama', ''))
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 GÜNCELLE", type="primary"):
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute("UPDATE durusma SET tur=?, tarih=?, saat=?, aciklama=? WHERE id=?",
                                     (yeni_tur, str(yeni_tarih), str(yeni_saat), yeni_aciklama, secilen))
                            conn.commit()
                        st.success("✅ Güncellendi!")
                        st.rerun()
                with col2:
                    if st.form_submit_button("🗑️ SİL", type="secondary"):
                        if st.checkbox("Silmek istediğinize emin misiniz?"):
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                c.execute("DELETE FROM durusma WHERE id=?", (secilen,))
                                conn.commit()
                            st.success("🗑️ Silindi!")
                            st.rerun()
        else:
            st.info("Henüz duruşma kaydı bulunmuyor.")

# ====================== GÖREVLER ======================
elif menu == "Görevler":
    st.header("📌 Görevler")
    
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Görev Ekle", "📋 Görev Listesi", "✏️ Düzenle / Sil"])
    
    # ====================== TAB 1: YENİ GÖREV EKLE ======================
    with tab1:
        st.subheader("Yeni Görev Ekle")
        
        with st.form("yeni_gorev_form", clear_on_submit=True):
            gorev_basligi = st.text_input("Görev Başlığı *")
            gorev_aciklama = st.text_area("Görev Açıklaması")
            son_tarih = st.date_input("Son Tarih")
            oncelik = st.selectbox("Öncelik", ["Yüksek", "Orta", "Düşük"])
            
            with get_db_connection() as conn:
                kullanicilar = pd.read_sql_query("SELECT DISTINCT username FROM users UNION SELECT 'Genel' as username", conn)
            
            atanan_kullanici = st.selectbox("Görev Atanan Kullanıcı", options=kullanicilar['username'])
            
            with get_db_connection() as conn:
                davalar = pd.read_sql_query("""
                    SELECT d.id, d.mahkeme, d.dosya_no, m.ad_soyad 
                    FROM dava d 
                    LEFT JOIN musteri m ON d.musteri_id = m.id 
                    ORDER BY d.dosya_no
                """, conn)
            
            secilen_dava = st.selectbox(
                "İlgili Dava / Dosya (Opsiyonel)",
                options=[None] + list(davalar['id']) if not davalar.empty else [None],
                format_func=lambda x: "Genel Görev" if x is None else 
                    f"{davalar[davalar['id']==x]['mahkeme'].values[0]} - {davalar[davalar['id']==x]['dosya_no'].values[0]}"
            )
            
            if st.form_submit_button("✅ Görevi Ekle", type="primary"):
                if not gorev_basligi:
                    st.error("Görev başlığı zorunludur!")
                else:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("""INSERT INTO gorev 
                                    (baslik, aciklama, son_tarih, oncelik, durum, atanan_kullanici, dava_id) 
                                    VALUES (?, ?, ?, ?, 'Bekliyor', ?, ?)""",
                                 (gorev_basligi.strip(), gorev_aciklama.strip(), 
                                  str(son_tarih), oncelik, atanan_kullanici, secilen_dava))
                        conn.commit()
                    st.success("✅ Görev başarıyla eklendi!")
                    st.rerun()

    # ====================== TAB 2: GÖREV LİSTESİ ======================
    with tab2:
        st.subheader("Tüm Görevler")
        
        with get_db_connection() as conn:
            gorevler = pd.read_sql_query("""
                SELECT g.id, g.baslik, g.son_tarih, g.oncelik, g.durum, 
                       g.atanan_kullanici, d.dosya_no, d.mahkeme
                FROM gorev g 
                LEFT JOIN dava d ON g.dava_id = d.id 
                ORDER BY g.son_tarih
            """, conn)
        
        if not gorevler.empty:
            df_display = gorevler.rename(columns={
                "baslik": "Görev Başlığı",
                "son_tarih": "Son Tarih",
                "oncelik": "Öncelik",
                "durum": "Durum",
                "atanan_kullanici": "Atanan Kişi",
                "dosya_no": "Dosya No",
                "mahkeme": "Mahkeme"
            })
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Henüz görev eklenmemiş.")

    # ====================== TAB 3: DÜZENLE / SİL ======================
    with tab3:
        st.subheader("Görev Düzenle veya Sil")
        
        with get_db_connection() as conn:
            df_list = pd.read_sql_query("SELECT id, baslik FROM gorev ORDER BY son_tarih", conn)
        
        if not df_list.empty:
            secilen_gorev = st.selectbox("Görev Seçin", options=df_list['id'],
                format_func=lambda x: df_list[df_list['id'] == x]['baslik'].values[0])
            
            with get_db_connection() as conn:
                secili = pd.read_sql_query("SELECT * FROM gorev WHERE id = ?", conn, params=(secilen_gorev,)).iloc[0]
            
            with st.form("duzenle_gorev_form"):
                yeni_baslik = st.text_input("Görev Başlığı", value=secili['baslik'])
                yeni_aciklama = st.text_area("Açıklama", value=secili.get('aciklama', ''))
                yeni_son_tarih = st.date_input("Son Tarih", value=datetime.strptime(secili['son_tarih'], "%Y-%m-%d").date())
                
                col1, col2 = st.columns(2)
                with col1:
                    yeni_oncelik = st.selectbox("Öncelik", ["Yüksek", "Orta", "Düşük"], 
                                              index=["Yüksek", "Orta", "Düşük"].index(secili['oncelik']))
                with col2:
                    yeni_durum = st.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal"], 
                                            index=["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal"].index(secili['durum']))
                
                with get_db_connection() as conn:
                    kullanicilar = pd.read_sql_query("SELECT DISTINCT username FROM users UNION SELECT 'Genel' as username", conn)
                
                mevcut_atanan = secili.get('atanan_kullanici', 'Genel')
                index = list(kullanicilar['username']).index(mevcut_atanan) if mevcut_atanan in list(kullanicilar['username']) else 0
                yeni_atanan = st.selectbox("Atanan Kullanıcı", options=kullanicilar['username'], index=index)
                
                with get_db_connection() as conn:
                    davalar = pd.read_sql_query("""
                        SELECT d.id, d.mahkeme, d.dosya_no 
                        FROM dava d ORDER BY d.dosya_no
                    """, conn)
                
                mevcut_dava = secili.get('dava_id')
                secilen_dava = st.selectbox(
                    "İlgili Dava (Opsiyonel)",
                    options=[None] + list(davalar['id']) if not davalar.empty else [None],
                    index=0 if mevcut_dava is None else ([None] + list(davalar['id'])).index(mevcut_dava) if mevcut_dava in [None] + list(davalar['id']) else 0,
                    format_func=lambda x: "Genel Görev" if x is None else 
                        f"{davalar[davalar['id']==x]['mahkeme'].values[0]} - {davalar[davalar['id']==x]['dosya_no'].values[0]}"
                )
                
                col_guncelle, col_sil = st.columns(2)
                with col_guncelle:
                    if st.form_submit_button("💾 GÜNCELLE", type="primary"):
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute("""UPDATE gorev SET baslik=?, aciklama=?, son_tarih=?, oncelik=?, 
                                        durum=?, atanan_kullanici=?, dava_id=? WHERE id=?""",
                                     (yeni_baslik, yeni_aciklama, str(yeni_son_tarih), yeni_oncelik, 
                                      yeni_durum, yeni_atanan, secilen_dava, secilen_gorev))
                            conn.commit()
                        st.success("✅ Görev güncellendi!")
                        st.rerun()
                
                with col_sil:
                    if st.form_submit_button("🗑️ SİL", type="secondary"):
                        if st.checkbox("Silmek istediğinize emin misiniz?"):
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                c.execute("DELETE FROM gorev WHERE id=?", (secilen_gorev,))
                                conn.commit()
                            st.success("🗑️ Görev silindi!")
                            st.rerun()
        else:
            st.info("Henüz görev bulunmuyor.")
    
# ====================== BELGELER ======================
elif menu == "Belgeler":
    st.header("📁 Belgeler & Döküman Yönetimi")
    
    tab1, tab2 = st.tabs(["📤 Belge Yükle", "📋 Belgelerim"])
    
    # ====================== TAB 1: BELGE YÜKLE ======================
    with tab1:
        st.subheader("Yeni Belge Yükle")
        uploaded_file = st.file_uploader("Dosya Seç (PDF, Word, Resim, vb.)", 
                                       type=['pdf', 'docx', 'doc', 'jpg', 'png', 'jpeg', 'txt'])
        
        if uploaded_file:
            with st.form("belge_yukle_form"):
                belge_adi = st.text_input("Belge Adı *", value=uploaded_file.name)
                
                with get_db_connection() as conn:
                    davalar = pd.read_sql_query("""
                        SELECT d.id, d.dosya_no, d.mahkeme, m.ad_soyad 
                        FROM dava d 
                        LEFT JOIN musteri m ON d.musteri_id = m.id 
                        ORDER BY d.dosya_no
                    """, conn)
                
                ilgili_dava = st.selectbox(
                    "İlgili Dava / Dosya *",
                    options=davalar['id'] if not davalar.empty else [],
                    format_func=lambda x: f"{davalar[davalar['id']==x]['dosya_no'].values[0]} - {davalar[davalar['id']==x]['mahkeme'].values[0]}"
                )
                
                belge_turu = st.selectbox("Belge Türü", 
                                        ["Dava Dilekçesi", "Mahkeme Kararı", "İcra Takip", 
                                         "Sözleşme", "Vekaletname", "Diğer"])
                aciklama = st.text_area("Açıklama / Not")
                
                submitted = st.form_submit_button("📤 Belgeyi Yükle", type="primary")
                
                if submitted:
                    if not belge_adi or not ilgili_dava:
                        st.error("Belge adı ve ilgili dava zorunludur!")
                    else:
                        try:
                            # Klasör oluşturma
                            secilen_dava_bilgi = davalar[davalar['id'] == ilgili_dava].iloc[0]
                            klasor_adi = f"{secilen_dava_bilgi['mahkeme']} - {secilen_dava_bilgi['dosya_no']} - {secilen_dava_bilgi['ad_soyad']}"
                            klasor_adi = klasor_adi.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_")
                            
                            klasor_yolu = f"belgeler/{klasor_adi}"
                            os.makedirs(klasor_yolu, exist_ok=True)
                            
                            dosya_yolu = f"{klasor_yolu}/{uploaded_file.name}"
                            
                            # Dosyayı kaydet
                            with open(dosya_yolu, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            
                            # Veritabanına kaydet
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                c.execute("""INSERT INTO belgeler 
                                            (belge_adi, dosya_yolu, belge_turu, aciklama, dava_id, yukleme_tarihi)
                                            VALUES (?, ?, ?, ?, ?, ?)""",
                                         (belge_adi, dosya_yolu, belge_turu, aciklama, 
                                          ilgili_dava, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                conn.commit()
                            
                            st.success(f"✅ '{belge_adi}' başarıyla yüklendi!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Belge yüklenirken hata oluştu: {e}")

    # ====================== TAB 2: YÜKLENEN BELGELER ======================
    with tab2:
        st.subheader("📋 Yüklenen Belgeler")
        
        with get_db_connection() as conn:
            belgeler = pd.read_sql_query("""
                SELECT 
                    b.id, b.belge_adi, b.belge_turu, b.aciklama, b.yukleme_tarihi, b.dosya_yolu,
                    d.dosya_no, d.mahkeme, m.ad_soyad as musteri
                FROM belgeler b
                LEFT JOIN dava d ON b.dava_id = d.id
                LEFT JOIN musteri m ON d.musteri_id = m.id
                ORDER BY b.yukleme_tarihi DESC
            """, conn)
        
        if not belgeler.empty:
            for dosya_no in belgeler['dosya_no'].unique():
                dava_belgeleri = belgeler[belgeler['dosya_no'] == dosya_no]
                mahkeme = dava_belgeleri['mahkeme'].iloc[0]
                musteri = dava_belgeleri['musteri'].iloc[0]
                
                with st.expander(f"📁 {mahkeme} - {dosya_no} - {musteri} ({len(dava_belgeleri)} belge)", expanded=False):
                    for idx, row in dava_belgeleri.iterrows():
                        col1, col2, col3 = st.columns([5, 2, 2])
                        
                        with col1:
                            st.write(f"**{row['belge_adi']}**")
                            st.caption(f"{row['belge_turu']} • {row['yukleme_tarihi']}")
                        
                        with col2:
                            if st.button("👁️ Önizle", key=f"preview_{row['id']}_{idx}"):
                                # Önizleme dialogu (basit hali)
                                st.info("Önizleme özelliği geliştirme aşamasında...")
                                if os.path.exists(row['dosya_yolu']):
                                    st.download_button("📥 İndir", open(row['dosya_yolu'], "rb"), row['belge_adi'])
                        
                        with col3:
                            if st.button("🗑️ Sil", key=f"delete_{row['id']}_{idx}", type="secondary"):
                                try:
                                    if os.path.exists(row['dosya_yolu']):
                                        os.remove(row['dosya_yolu'])
                                    with get_db_connection() as conn:
                                        c = conn.cursor()
                                        c.execute("DELETE FROM belgeler WHERE id=?", (row['id'],))
                                        conn.commit()
                                    st.success("Belge silindi!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Silme hatası: {e}")
        else:
            st.info("Henüz belge yüklenmemiş.")

# ====================== RAPORLAR ======================
elif menu == "Raporlar":
    st.header("📊 Raporlar ve İstatistikler")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Dava Durum Dağılımı", 
        "📅 Aylık Duruşma Trendi", 
        "⚖️ Mahkeme Bazlı Performans", 
        "👤 Müvekkil Bazlı Rapor"
    ])
    
    with get_db_connection() as conn:
        
        # TAB 1: Dava Durum Dağılımı
        with tab1:
            st.subheader("Dava Durum Dağılımı")
            durum_df = pd.read_sql_query("""
                SELECT durum, COUNT(*) as sayi 
                FROM dava 
                GROUP BY durum 
                ORDER BY sayi DESC
            """, conn)
            
            if not durum_df.empty:
                fig = px.bar(durum_df, x="durum", y="sayi", color="durum",
                             title="Davalara Göre Durum Dağılımı",
                             labels={"sayi": "Dava Sayısı", "durum": "Durum"})
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(durum_df, use_container_width=True, hide_index=True)
            else:
                st.info("Henüz dava kaydı bulunmuyor.")

        # TAB 2: Aylık Duruşma Trendi
        with tab2:
            st.subheader("Aylık Duruşma Trendi")
            durusma_df = pd.read_sql_query("""
                SELECT strftime('%Y-%m', tarih) as ay, COUNT(*) as durusma_sayisi
                FROM durusma
                GROUP BY ay
                ORDER BY ay
            """, conn)
            
            if not durusma_df.empty:
                fig = px.line(durusma_df, x="ay", y="durusma_sayisi", markers=True,
                              title="Aylık Duruşma Sayısı Trendi",
                              labels={"ay": "Ay", "durusma_sayisi": "Duruşma Sayısı"})
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(durusma_df, use_container_width=True, hide_index=True)
            else:
                st.info("Henüz duruşma kaydı bulunmuyor.")

        # TAB 3: Mahkeme Bazlı Performans
        with tab3:
            st.subheader("Mahkeme Bazlı Dava Performansı")
            mahkeme_df = pd.read_sql_query("""
                SELECT mahkeme, 
                       COUNT(*) as dava_sayisi,
                       SUM(CASE WHEN durum IN ('Açık', 'İstinaf', 'Temyiz') THEN 1 ELSE 0 END) as aktif_dava
                FROM dava 
                GROUP BY mahkeme 
                ORDER BY dava_sayisi DESC
            """, conn)
            
            if not mahkeme_df.empty:
                fig = px.bar(mahkeme_df, x="mahkeme", y="dava_sayisi", color="aktif_dava",
                             title="Mahkemelere Göre Dava Sayısı",
                             labels={"dava_sayisi": "Toplam Dava", "mahkeme": "Mahkeme"})
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(mahkeme_df, use_container_width=True, hide_index=True)
            else:
                st.info("Henüz mahkeme bazlı veri yok.")

        # TAB 4: Müvekkil Bazlı Rapor
        with tab4:
            st.subheader("Müvekkil Bazlı Rapor")
            musteri_df = pd.read_sql_query("""
                SELECT m.ad_soyad as musteri, 
                       COUNT(d.id) as dava_sayisi,
                       SUM(CASE WHEN d.durum IN ('Açık', 'İstinaf', 'Temyiz') THEN 1 ELSE 0 END) as aktif_dava
                FROM musteri m
                LEFT JOIN dava d ON m.id = d.musteri_id
                GROUP BY m.id, m.ad_soyad
                HAVING dava_sayisi > 0
                ORDER BY dava_sayisi DESC
                LIMIT 15
            """, conn)
            
            if not musteri_df.empty:
                fig = px.bar(musteri_df, x="musteri", y="dava_sayisi", color="aktif_dava",
                             title="En Çok Dava Olan Müvekkiller (İlk 15)",
                             labels={"dava_sayisi": "Dava Sayısı", "musteri": "Müvekkil"})
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(musteri_df, use_container_width=True, hide_index=True)
            else:
                st.info("Henüz müvekkil bazlı veri yok.")

# ====================== CARİ HESAP ======================
elif menu == "Hesaplar":
    st.header("💰 Cari Hesap Takibi")
    
    tab1, tab2, tab3 = st.tabs(["➕ Hareket Ekle", "📋 Cari Ekstre", "✏️ Düzenle / Sil"])

    # ====================== TAB 1: HAREKET EKLE ======================
    with tab1:
        st.subheader("Yeni Hareket Ekle")
        
        with get_db_connection() as conn:
            musteriler = pd.read_sql_query("SELECT id, ad_soyad FROM musteri ORDER BY ad_soyad", conn)
        
        col1, col2 = st.columns([2, 3])
        with col1:
            musteri_sec = st.selectbox("Müvekkil *", 
                options=musteriler['id'] if not musteriler.empty else [],
                format_func=lambda x: musteriler[musteriler['id'] == x]['ad_soyad'].values[0])

        with col2:
            if musteri_sec:
                with get_db_connection() as conn:
                    davalar = pd.read_sql_query(
                        "SELECT id, dosya_no, mahkeme FROM dava WHERE musteri_id = ? ORDER BY dosya_no", 
                        conn, params=(musteri_sec,))
            else:
                davalar = pd.DataFrame()
            
            dava_sec = st.selectbox("Dava / Dosya (Opsiyonel)",
                options=[None] + list(davalar['id']) if not davalar.empty else [None],
                format_func=lambda x: "Genel (Dava Seçilmedi)" if x is None else 
                    f"{davalar[davalar['id']==x]['mahkeme'].values[0]} - {davalar[davalar['id']==x]['dosya_no'].values[0]}")

        col_tarih, col_tur = st.columns(2)
        with col_tarih:
            islem_tarihi = st.date_input("İşlem Tarihi", value=datetime.now().date())
        with col_tur:
            islem_turu = st.radio("İşlem Türü *", ["Borç", "Alacak"], horizontal=True)

        if islem_turu == "Borç":
            gider_turu = st.selectbox("Gider Türü *", ["Harç", "Masraf", "Tahsilat", "Pul"])
            if gider_turu == "Harç":
                alt_tur = st.selectbox("Harç Türü", HARC_LISTESI)
            elif gider_turu == "Masraf":
                alt_tur = st.selectbox("Masraf Türü", MASRAF_LISTESI)
            elif gider_turu == "Tahsilat":
                alt_tur = st.selectbox("Tahsilat Türü", TAHSILAT_BORC_LISTESI)
            else:
                alt_tur = st.selectbox("Pul Türü", PUL_LISTESI)
        else:
            gider_turu = "Tahsilat"
            alt_tur = st.selectbox("Gelir Türü", GELIR_TURLERI)

        with st.form("cari_hareket_form", clear_on_submit=True):
            col_adet, col_tutar = st.columns([1, 2])
            with col_adet:
                adet = st.number_input("Adet", min_value=1, value=1, step=1)
            with col_tutar:
                tutar = st.number_input("Tutar (₺) *", min_value=0.0, step=10.0, format="%.2f")
            
            aciklama = st.text_area("Açıklama / Not", height=80)

            if st.form_submit_button("➕ HAREKETİ KAYDET", type="primary", use_container_width=True):
                if not musteri_sec or tutar <= 0:
                    st.error("❌ Müvekkil ve Tutar zorunludur!")
                else:
                    try:
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute("""INSERT INTO cari_hesap 
                                (musteri_id, dava_id, islem_tarihi, islem_turu, gider_turu, harc_turu, adet, tutar, aciklama)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (musteri_sec, dava_sec, str(islem_tarihi), islem_turu, 
                                 gider_turu, alt_tur, adet, tutar, aciklama))
                            conn.commit()
                        st.success("✅ Hareket başarıyla kaydedildi!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")

    # ====================== TAB 2: CARİ EKSTRE ======================
    with tab2:
        st.subheader("Cari Ekstre")
        
        with get_db_connection() as conn:
            musteriler = pd.read_sql_query("SELECT id, ad_soyad FROM musteri ORDER BY ad_soyad", conn)
        
        secilen_musteri = st.selectbox("Müvekkil Seçin", 
            options=musteriler['id'] if not musteriler.empty else [],
            format_func=lambda x: musteriler[musteriler['id'] == x]['ad_soyad'].values[0])

        if secilen_musteri:
            gorunum = st.radio("Görünüm", ["Müvekkil Bazlı", "Dava Bazlı"], horizontal=True)

            if gorunum == "Dava Bazlı":
                with get_db_connection() as conn:
                    davalar = pd.read_sql_query(
                        "SELECT id, dosya_no, mahkeme FROM dava WHERE musteri_id = ?", 
                        conn, params=(secilen_musteri,))
                if not davalar.empty:
                    secilen_dava = st.selectbox("Dava Seçin", options=davalar['id'],
                        format_func=lambda x: f"{davalar[davalar['id']==x]['mahkeme'].values[0]} - {davalar[davalar['id']==x]['dosya_no'].values[0]}")
                    query = "SELECT * FROM cari_hesap WHERE musteri_id = ? AND dava_id = ? ORDER BY islem_tarihi"
                    params = (secilen_musteri, secilen_dava)
                else:
                    st.info("Bu müvekkile ait dava yok.")
                    query = None
            else:
                query = "SELECT * FROM cari_hesap WHERE musteri_id = ? ORDER BY islem_tarihi"
                params = (secilen_musteri,)

            if query:
                with get_db_connection() as conn:
                    df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    df['Bakiye'] = df.apply(
                        lambda row: row['tutar'] if row['islem_turu'] == 'Alacak' else -row['tutar'], axis=1
                    ).cumsum()
                    
                    df_display = df.rename(columns={
                        "islem_tarihi": "Tarih", "islem_turu": "İşlem Türü",
                        "gider_turu": "Gider Türü", "harc_turu": "Detay",
                        "tutar": "Tutar"
                    })
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    
                    toplam_bakiye = df['Bakiye'].iloc[-1]
                    st.metric("Güncel Bakiye", f"₺ {toplam_bakiye:,.2f}", 
                             delta="Alacak" if toplam_bakiye >= 0 else "Borç")
                else:
                    st.info("Bu müvekkile ait hareket bulunmuyor.")

    # ====================== TAB 3: DÜZENLE / SİL ======================
    with tab3:
        st.subheader("Hareket Düzenle veya Sil")
        
        with get_db_connection() as conn:
            musteriler = pd.read_sql_query("SELECT id, ad_soyad FROM musteri ORDER BY ad_soyad", conn)
        
        secilen_musteri = st.selectbox("Müvekkil Seçin", 
            options=musteriler['id'] if not musteriler.empty else [],
            format_func=lambda x: musteriler[musteriler['id'] == x]['ad_soyad'].values[0],
            key="duzenle_musteri_key")

        if secilen_musteri:
            with get_db_connection() as conn:
                hareketler = pd.read_sql_query("""
                    SELECT id, islem_tarihi, islem_turu, tutar, aciklama 
                    FROM cari_hesap 
                    WHERE musteri_id = ? 
                    ORDER BY islem_tarihi DESC
                """, conn, params=(secilen_musteri,))
            
            if not hareketler.empty:
                secilen_hareket = st.selectbox("Hareket Seçin", options=hareketler['id'],
                    format_func=lambda x: f"{hareketler[hareketler['id']==x]['islem_tarihi'].values[0]} | "
                                         f"{hareketler[hareketler['id']==x]['islem_turu'].values[0]} | "
                                         f"₺{hareketler[hareketler['id']==x]['tutar'].values[0]}")

                secili = hareketler[hareketler['id'] == secilen_hareket].iloc[0]

                with st.form("duzenle_hareket_form"):
                    yeni_tarih = st.date_input("Tarih", value=datetime.strptime(secili['islem_tarihi'], "%Y-%m-%d").date())
                    yeni_tur = st.selectbox("İşlem Türü", ["Borç", "Alacak"], 
                                          index=0 if secili['islem_turu'] == "Borç" else 1)
                    yeni_tutar = st.number_input("Tutar", value=float(secili['tutar']))
                    yeni_aciklama = st.text_area("Açıklama", value=secili.get('aciklama', ''))

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Güncelle", type="primary"):
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                c.execute("UPDATE cari_hesap SET islem_tarihi=?, islem_turu=?, tutar=?, aciklama=? WHERE id=?",
                                         (str(yeni_tarih), yeni_tur, yeni_tutar, yeni_aciklama, secilen_hareket))
                                conn.commit()
                            st.success("✅ Güncellendi!")
                            st.rerun()
                    with col2:
                        if st.form_submit_button("🗑️ Sil", type="secondary"):
                            if st.checkbox("Silmek istediğinize emin misiniz?"):
                                with get_db_connection() as conn:
                                    c = conn.cursor()
                                    c.execute("DELETE FROM cari_hesap WHERE id=?", (secilen_hareket,))
                                    conn.commit()
                                st.success("🗑️ Silindi!")
                                st.rerun()
            else:
                st.info("Bu müvekkile ait hareket bulunmuyor.")

# ====================== YEDEKLEME ======================
elif menu == "Yedekleme":
    st.header("💾 Veritabanı Yedekleme ve Geri Yükleme")
    
    import shutil
    import os
    from datetime import datetime

    BACKUP_DIR = "backups"
    os.makedirs(BACKUP_DIR, exist_ok=True)

    tab1, tab2, tab3 = st.tabs(["📦 Yeni Yedek Al", "📋 Yedek Listesi", "⚠️ Geri Yükleme"])

    # ====================== TAB 1: YENİ YEDEK AL ======================
    with tab1:
        st.subheader("Manuel Yedek Alma")
        aciklama = st.text_input("Yedek Açıklaması (Opsiyonel)", 
                                placeholder="Örn: Haftalık tam yedek - 06.07.2026")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📦 Şimdi Yedek Al", type="primary", use_container_width=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"hukuk_otomasyon_{timestamp}.db"
                backup_path = os.path.join(BACKUP_DIR, backup_name)

                try:
                    shutil.copy("hukuk_otomasyon.db", backup_path)
                    
                    if aciklama.strip():
                        with open(backup_path + ".txt", "w", encoding="utf-8") as f:
                            f.write(aciklama.strip())
                    
                    st.success(f"✅ Yedek başarıyla alındı: `{backup_name}`")
                except Exception as e:
                    st.error(f"Hata oluştu: {e}")

        with col2:
            st.info("💡 Yedekler 'backups' klasörüne kaydedilir.")

    # ====================== TAB 2: YEDEK LİSTESİ ======================
    with tab2:
        st.subheader("Mevcut Yedekler")
        
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")],
            reverse=True
        )

        if backups:
            for backup_file in backups:
                backup_path = os.path.join(BACKUP_DIR, backup_file)
                size_mb = os.path.getsize(backup_path) / (1024 * 1024)
                mod_time = datetime.fromtimestamp(os.path.getmtime(backup_path)).strftime("%d.%m.%Y %H:%M")

                desc = ""
                desc_file = backup_path + ".txt"
                if os.path.exists(desc_file):
                    with open(desc_file, "r", encoding="utf-8") as f:
                        desc = f.read().strip()

                with st.expander(f"📁 {backup_file} • {size_mb:.2f} MB • {mod_time}", expanded=False):
                    if desc:
                        st.caption(f"**Açıklama:** {desc}")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📥 İndir", key=f"dl_{backup_file}", use_container_width=True):
                            with open(backup_path, "rb") as f:
                                st.download_button("Dosyayı İndir", f, backup_file, key=f"download_{backup_file}")

                    with col2:
                        if st.button("🔄 Geri Yükle", key=f"restore_{backup_file}", use_container_width=True):
                            if st.checkbox("Geri yüklemek istediğinize emin misiniz? (Mevcut veri silinecek)"):
                                try:
                                    shutil.copy(backup_path, "hukuk_otomasyon.db")
                                    st.success(f"✅ `{backup_file}` yedeğinden geri yüklendi!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Hata: {e}")

                    with col3:
                        if st.button("🗑️ Sil", key=f"del_{backup_file}", use_container_width=True):
                            if st.checkbox("Silmek istediğinize emin misiniz?"):
                                try:
                                    os.remove(backup_path)
                                    if os.path.exists(desc_file):
                                        os.remove(desc_file)
                                    st.success("Yedek silindi.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Hata: {e}")
        else:
            st.info("Henüz yedek bulunmuyor.")

    # ====================== TAB 3: Geri Yükleme ======================
    with tab3:
        st.subheader("⚠️ Geri Yükleme")
        st.warning("Bu işlem mevcut veritabanını tamamen siler ve seçilen yedeği yükler.")
        
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")],
            reverse=True
        )
        
        if backups:
            secilen_yedek = st.selectbox("Yüklenecek Yedeği Seçin", backups)
            if st.button("🚨 Seçili Yedeği Geri Yükle", type="primary"):
                if st.checkbox("Bu işlem mevcut tüm verileri silecek. Emin misiniz?"):
                    try:
                        shutil.copy(os.path.join(BACKUP_DIR, secilen_yedek), "hukuk_otomasyon.db")
                        st.success("✅ Veritabanı başarıyla geri yüklendi!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Geri yükleme hatası: {e}")
        else:
            st.info("Yüklenecek yedek bulunmuyor.")

# ====================== AYARLAR ======================
elif menu == "Ayarlar":
    st.header("⚙️ Ayarlar")
    
    tab1, tab2, tab3 = st.tabs([
        "🏢 Firma Bilgileri", 
        "🎨 Tema", 
        "ℹ️ Uygulama Bilgileri"
    ])
    
    # ====================== TAB 1: FİRMA BİLGİLERİ ======================
    with tab1:
        st.subheader("🏢 Firma Bilgileri")
        
        if "firma_adi" not in st.session_state:
            st.session_state.firma_adi = "TOKER HUKUK BÜROSU"
        
        firma_adi = st.text_input("Firma Adı", value=st.session_state.firma_adi)
        
        uploaded_logo = st.file_uploader("Firma Logosu Yükle (PNG/JPG)", type=["png", "jpg", "jpeg"])
        if uploaded_logo:
            st.session_state.firma_logo = uploaded_logo
            st.image(uploaded_logo, width=200)
        
        if st.button("💾 Firma Bilgilerini Kaydet", type="primary"):
            st.session_state.firma_adi = firma_adi
            st.success("Firma bilgileri kaydedildi!")

    # ====================== TAB 2: TEMA ======================
    with tab2:
        st.subheader("🎨 Tema Ayarları")
        
        tema = st.radio("Tema Seçimi", ["Açık Tema", "Koyu Tema"], horizontal=True)
        
        if st.button("🎨 Temayı Uygula"):
            if tema == "Koyu Tema":
                st.markdown("""
                    <style>
                    .stApp { background-color: #0e1117; color: white; }
                    </style>
                """, unsafe_allow_html=True)
                st.success("Koyu tema uygulandı!")
            else:
                st.success("Açık tema uygulandı!")

    # ====================== TAB 3: UYGULAMA BİLGİLERİ ======================
    with tab3:
        st.subheader("ℹ️ Uygulama Bilgileri")
        st.markdown("""
        **TOKER HUKUK BÜROSU Otomasyon Sistemi**  
        
        - **Versiyon:** 1.2 (Güncellenmiş)
        - **Geliştirici:** Recep
        - **Teknoloji:** Python + Streamlit + SQLite
        - **Özellikler:** Müvekkil, Dava, Duruşma, Görev, Belge, Cari Hesap Yönetimi
        
        **Not:** Bu sistem yerel kullanım için geliştirilmiştir.
        """)
        
        st.divider()
        
        if st.button("🚪 Çıkış Yap", type="secondary"):
            st.session_state.user = None
            st.rerun()
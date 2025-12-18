# app.py
# -*- coding: utf-8 -*-
"""
Saxophobia – registrácia účastníkov + plánovanie lekcií (MVP)
"""
def hide_streamlit_menu():
    hide_menu_style = """
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stActionButton {visibility: hidden;}
        </style>
    """
    st.markdown(hide_menu_style, unsafe_allow_html=True)


from urllib.parse import quote
import html
import requests
import smtplib, ssl
from email.message import EmailMessage
import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple

# -----------------------------
# Jazykové texty
# -----------------------------
TEXTS = {
    "SK": {
        # --- Navigácia ---
        "nav_application": "Prihláška",
        "nav_organizer": "Organizátor",
        "nav_admin": "Admin",
        "nav_feedback": "Feedback",
        "nav_label": "Navigácia",
        "lang_label": "Jazyk",

        # --- Prihláška ---
        "application_header": "Prihláška – Saxophobia",
        "application_fill": "Vyplňte prosím údaje. * (povinné)",
        "name": "Meno a priezvisko *",
        "email": "E-mail *",
        "phone": "Telefón",
        "age": "Vek",
        "course": "Kurz (Účasť: A=aktívna, P=pasívna, O=len hra v orchestri)",
        "instrument": "Nástroj",
        "school": "Škola",
        "submit": "Odoslať prihlášku",
        "success": "Ďakujeme, prihláška bola odoslaná.",

        # --- Feedback formulár ---
        "feedback_header": "Feedback – Saxophobia",
        "feedback_intro": "Ďakujeme, že nám pomáhate zlepšovať Saxophobiu.",
        "feedback_liked": "Čo sa vám na Saxophobii páčilo?",
        "feedback_improve": "Čo by sme mali zlepšiť?",
        "feedback_lectors": "Ktorých lektorov by ste privítali nabudúce?",
        "feedback_workshops": "Workshopy",
        "feedback_topics": "Aký obsah workshopov by ste chceli nabudúce?",
        "feedback_other": "Akýkoľvek iný komentár:",
        "feedback_name_optional": "Vaše meno (nepovinné):",
        "feedback_submit": "Odoslať feedback",
        "feedback_success": "Ďakujeme za spätnú väzbu!",

        # --- Feedback admin ---
        "feedback_admin_tab": "Admin – otázky & export",
        "feedback_fill_tab": "Vyplniť dotazník",
        "feedback_year": "Rok",
        "feedback_questions_title": "Otázky k workshopom",
        "feedback_add_default_q": "Doplniť predvolené otázky",
        "feedback_save_questions": "Uložiť otázky",
        "feedback_export": "Export odpovedí",
    },

    "EN": {
        # --- Navigation ---
        "nav_application": "Application",
        "nav_organizer": "Organizer",
        "nav_admin": "Admin",
        "nav_feedback": "Feedback",
        "nav_label": "Navigation",
        "lang_label": "Language",

        # --- Application ---
        "application_header": "Application – Saxophobia",
        "application_fill": "Please fill in the required information. * (required)",
        "name": "Full name *",
        "email": "E-mail *",
        "phone": "Phone",
        "age": "Age",
        "course": "Course (Participation: A=active, P=passive, O=only playing in the orchestra)",
        "instrument": "Instrument",
        "school": "School",
        "submit": "Submit application",
        "success": "Thank you, your application has been sent.",

        # --- Feedback form ---
        "feedback_header": "Feedback – Saxophobia",
        "feedback_intro": "Thank you for helping us improve Saxophobia.",
        "feedback_liked": "What did you like about Saxophobia?",
        "feedback_improve": "What should we improve?",
        "feedback_lectors": "Which lecturers would you welcome next time?",
        "feedback_workshops": "Workshops",
        "feedback_topics": "What workshop topics would you like next time?",
        "feedback_other": "Any other comment:",
        "feedback_name_optional": "Your name (optional):",
        "feedback_submit": "Submit feedback",
        "feedback_success": "Thank you for your feedback!",

        # --- Feedback admin ---
        "feedback_admin_tab": "Admin – questions & export",
        "feedback_fill_tab": "Fill out the form",
        "feedback_year": "Year",
        "feedback_questions_title": "Workshop questions",
        "feedback_add_default_q": "Add default questions",
        "feedback_save_questions": "Save questions",
        "feedback_export": "Export responses",
    }
}


# -----------------------------
# Konštanty & defaulty
# -----------------------------
DEFAULT_LECTORS = [
    "Rall",
    "Zoelen",
    "Trompenaars",
    "Fančovič",
    "Padilla",
    "Brutti",
    "Portejoie",
]


ENSEMBLE_TYPES = ["jednotlivec/individual", "duo", "trio", "kvarteto", "kvinteto", "iné/other"]
ROOM_TYPES = ["jednokapsule/single capsule", "dvojkapsule/double capsule", "trojlôžková/triple", "iné/other"]
COURSES = ["A", "P", "O"]
INSTRUMENTS = ["sopran sax", "alt sax", "tenor sax", "baryton sax", "bas sax", "kontrabas sax"]

DB_PATH = "saxophobia.db"

# -----------------------------
# UBYTOVACÍ INVENTÁR (kódy a kapacity)
# -----------------------------
# JK = jednokapsule, DK = dvojkapsule
ROOM_INVENTORY = [
    {"code": "JK10-1", "label": "Jednokapsule (10) #1", "capacity": 10},
    {"code": "JK10-2", "label": "Jednokapsule (10) #2", "capacity": 10},
    {"code": "JK4-1",  "label": "Jednokapsule (4) #1",  "capacity": 4},
    {"code": "JK4-2",  "label": "Jednokapsule (4) #2",  "capacity": 4},
    {"code": "JK4-3",  "label": "Jednokapsule (4) #3",  "capacity": 4},
    {"code": "DK8-1",  "label": "Dvojkapsule (8) #1",   "capacity": 8},
    {"code": "DK6-1",  "label": "Dvojkapsule (6) #1",   "capacity": 6},
]
ROOM_CAPACITY_BY_CODE = {r["code"]: r["capacity"] for r in ROOM_INVENTORY}
ROOM_LABEL_BY_CODE = {r["code"]: r["label"] for r in ROOM_INVENTORY}
ROOM_CODES = [r["code"] for r in ROOM_INVENTORY]


# --- Event dates (centrálne defaulty) ---
EVENT_START = date(2026, 1, 29)
EVENT_END   = date(2026, 2, 1)

# --- Feedback (aktuálny rok – podľa eventu) ---
FEEDBACK_YEAR_DEFAULT = EVENT_START.year  # napr. 2026
FEEDBACK_DEFAULT_QUESTIONS = [
    "Was Jan Provazník's workshop useful to you?",
    "Was Jana Dekánková's workshop useful to you?",
]


# -----------------------------
# DB helpery a migrácie
# -----------------------------

def ensure_feedback_tables(conn: sqlite3.Connection):
    cur = conn.cursor()
    # Workshop otázky (po rokoch – aby sa dali meniť)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            question TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1
        )
    """)
    # Odpovede respondentov
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            year INTEGER NOT NULL,
            liked TEXT,
            improve TEXT,
            lectors_next TEXT,
            workshop_answers TEXT,      -- JSON: {question_id: "Yes/No/I didn't attend"}
            workshop_topics TEXT,       -- free text: "What workshop content..."
            other_comment TEXT,
            name_optional TEXT
        )
    """)
    conn.commit()

def seed_feedback_questions_if_empty(conn: sqlite3.Connection, year: int):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM feedback_questions WHERE year=?", (year,))
    if (cur.fetchone()[0] or 0) == 0:
        cur.executemany(
            "INSERT INTO feedback_questions(year, question, enabled) VALUES(?,?,1)",
            [(year, q) for q in FEEDBACK_DEFAULT_QUESTIONS]
        )
        conn.commit()

def load_feedback_questions(conn: sqlite3.Connection, year: int) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT id, question, enabled FROM feedback_questions WHERE year=? ORDER BY id",
        conn, params=(year,)
    )

def save_feedback_questions(conn: sqlite3.Connection, year: int, edited_df: pd.DataFrame):
    cur = conn.cursor()
    # delete removed
    original = load_feedback_questions(conn, year)
    orig_ids = set(original["id"].dropna().astype(int)) if not original.empty else set()
    new_ids  = set(edited_df.get("id", pd.Series([], dtype=int)).dropna().astype(int)) if not edited_df.empty else set()
    for del_id in (orig_ids - new_ids):
        cur.execute("DELETE FROM feedback_questions WHERE id=?", (int(del_id),))

    # upsert others + add new
    for _, r in edited_df.iterrows():
        q = (r.get("question") or "").strip()
        if not q:
            continue
        en = int(1 if r.get("enabled", 1) else 0)
        rid = r.get("id")
        if pd.isna(rid) or rid is None:
            cur.execute("INSERT INTO feedback_questions(year, question, enabled) VALUES(?,?,?)", (year, q, en))
        else:
            cur.execute("UPDATE feedback_questions SET question=?, enabled=? WHERE id=?", (q, en, int(rid)))
    conn.commit()

def save_feedback_response(conn: sqlite3.Connection, payload: dict):
    conn.execute("""
        INSERT INTO feedback_responses
        (created_at, year, liked, improve, lectors_next, workshop_answers, workshop_topics, other_comment, name_optional)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        int(payload["year"]),
        payload.get("liked"),
        payload.get("improve"),
        payload.get("lectors_next"),
        to_json(payload.get("workshop_answers") or {}),
        payload.get("workshop_topics"),
        payload.get("other_comment"),
        payload.get("name_optional"),
    ))
    conn.commit()

def page_feedback():
    # Jazykové texty
    lang = st.session_state.get("lang", "SK")
    txt = TEXTS.get(lang, TEXTS["SK"])

    st.header(txt["feedback_header"])
    conn = get_conn()
    ensure_feedback_tables(conn)

    # Rok dotazníka
    year = st.number_input(
        txt["feedback_year"],
        min_value=2020,
        max_value=2100,
        value=FEEDBACK_YEAR_DEFAULT,
        step=1,
    )
    seed_feedback_questions_if_empty(conn, year)

    tab_fill, tab_admin = st.tabs([txt["feedback_fill_tab"], txt["feedback_admin_tab"]])

    # ---------- VEREJNÝ FORMULÁR ----------
    with tab_fill:
        st.subheader(f"{txt['feedback_header']} {year}")
        st.caption(txt["feedback_intro"])

        liked = st.text_area(txt["feedback_liked"])
        improve = st.text_area(txt["feedback_improve"])
        lectors_next = st.text_area(txt["feedback_lectors"])

        q_df = load_feedback_questions(conn, year)
        answers = {}

        if q_df.empty:
            msg = (
                "Pre tento rok zatiaľ nie sú nastavené žiadne workshopové otázky."
                if lang == "SK"
                else "There are no workshop questions set for this year yet."
            )
            st.info(msg)
        else:
            st.markdown(f"### {txt['feedback_workshops']}")
            for _, row in q_df.iterrows():
                if int(row["enabled"]) != 1:
                    continue
                qid = str(int(row["id"]))
                options = (
                    ["Áno", "Nie", "Nezúčastnil som sa"]
                    if lang == "SK"
                    else ["Yes", "No", "I didn't attend"]
                )
                answers[qid] = st.radio(
                    row["question"],
                    options=options,
                    horizontal=True,
                    key=f"ws_{qid}",
                )

        workshop_topics = st.text_area(txt["feedback_topics"])
        other_comment = st.text_area(txt["feedback_other"])
        name_optional = st.text_input(txt["feedback_name_optional"])

        if st.button(txt["feedback_submit"]):
            payload = {
                "year": year,
                "liked": liked.strip() or None,
                "improve": improve.strip() or None,
                "lectors_next": lectors_next.strip() or None,
                "workshop_answers": answers,
                "workshop_topics": workshop_topics.strip() or None,
                "other_comment": other_comment.strip() or None,
                "name_optional": name_optional.strip() or None,
            }
            save_feedback_response(conn, payload)
            st.success(txt["feedback_success"])

    # ---------- ADMIN – OTÁZKY & EXPORT ----------
    with tab_admin:
        if not login("admin"):
            st.stop()

        st.markdown(f"### {txt['feedback_questions_title']}")

        q_df = load_feedback_questions(conn, year)
        edited = st.data_editor(
            q_df,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "question": st.column_config.TextColumn("Question"),
                "enabled": st.column_config.CheckboxColumn("Enabled"),
            },
        )

        col_q_save, col_q_seed = st.columns([1, 1])
        with col_q_save:
            if st.button(txt["feedback_save_questions"]):
                save_feedback_questions(
                    conn,
                    year,
                    edited if isinstance(edited, pd.DataFrame) else q_df,
                )
                msg = "Otázky uložené." if lang == "SK" else "Questions saved."
                st.success(msg)

        with col_q_seed:
            if st.button(txt["feedback_add_default_q"]):
                seed_feedback_questions_if_empty(conn, year)
                msg = (
                    "Predvolené otázky doplnené."
                    if lang == "SK"
                    else "Default questions added (if missing)."
                )
                st.success(msg)

        st.markdown(f"### {txt['feedback_export']}")
        resp = pd.read_sql_query(
            "SELECT * FROM feedback_responses WHERE year=? ORDER BY created_at DESC",
            conn,
            params=(year,),
        )

        if not resp.empty:
            # rozbaliť JSON odpovede na stĺpce podľa otázok
            qmap_df = load_feedback_questions(conn, year)
            qmap = {int(r["id"]): r["question"] for _, r in qmap_df.iterrows()}

            def _answers_to_cols(js):
                d = from_json(js) or {}
                out = {}
                for qid, qtext in qmap.items():
                    out[qtext] = d.get(str(qid))
                return pd.Series(out)

            ws_cols = resp["workshop_answers"].apply(_answers_to_cols)
            export_df = pd.concat(
                [resp.drop(columns=["workshop_answers"]), ws_cols],
                axis=1,
            )

            st.dataframe(export_df, use_container_width=True)
            xlsx = to_excel_bytes(export_df)

            filename = f"feedback_{year}.xlsx"
            st.download_button(
                txt["feedback_export"],
                data=xlsx,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            msg = "Zatiaľ bez odpovedí pre tento rok." if lang == "SK" else "No responses for this year yet."
            st.info(msg)


def _gmail_ready_message():
    try:
        g = st.secrets["gmail"]
        user = g.get("user")
        ok_pw = bool(g.get("app_password"))
    except Exception:
        user, ok_pw = None, False
    if user and ok_pw:
        st.success(f"Gmail SMTP je pripravený (odosielateľ: {user}).")
    else:
        st.error("Gmail SMTP nie je načítaný zo secrets. Skontroluj .streamlit/secrets.toml a reštartuj appku.")


def _wrap_html_from_text(body: str) -> str:
    """
    Urobí jednoduché HTML s pevným fontom a zachovaním riadkovania.
    white-space: pre-wrap -> zachová \n, viac medzier aj zalamovanie.
    """
    safe = html.escape(body or "")
    return f"""<!doctype html>
<html>
  <body>
    <div style="font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.5; color: #000; white-space: pre-wrap;">
      {safe}
    </div>
  </body>
</html>"""


# --- EMAIL TEMPLATES (DB) ---
def ensure_email_templates_table(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY,
            name TEXT,
            subject TEXT,
            body TEXT
        )
    """)
    # inicializuj 1..3, ak chýbajú
    for i, (nm, sj, bd) in {
        1: ("Template 1", "Saxophobia – dôležité informácie pre účastníkov",
            "Ahojte,\n\nposielame súhrn organizačných informácií k Saxophobii.\n- Registrácia: ...\n- Ubytovanie: ...\n- Platby: ...\n\nTešíme sa na vás!\nSaxophobia tím"),
        2: ("Template 2 (platby)", "Saxophobia – informácia k platbe",
            "Dobrý deň,\n\nprosíme o úhradu účastníckeho poplatku do DD.MM.YYYY na účet ...\nVariabilný symbol: ...\n\nĎakujeme.\nS pozdravom\nSaxophobia tím"),
        3: ("Template 3", "Saxophobia – harmonogram",
            "Ahojte,\n\nprikladáme harmonogram a organizačné pokyny.\n\nS pozdravom\nSaxophobia tím"),
    }.items():
        cur.execute("INSERT OR IGNORE INTO email_templates (id,name,subject,body) VALUES (?,?,?,?)", (i,nm,sj,bd))
    conn.commit()

def load_email_templates(conn: sqlite3.Connection) -> Dict[int, Dict[str,str]]:
    rows = conn.execute("SELECT id, name, subject, body FROM email_templates ORDER BY id").fetchall()
    return {int(r["id"]): {"name": r["name"] or f"Template {r['id']}", "subject": r["subject"] or "", "body": r["body"] or ""} for r in rows}

def save_email_template(conn: sqlite3.Connection, tid: int, name: str, subject: str, body: str):
    conn.execute("UPDATE email_templates SET name=?, subject=?, body=? WHERE id=?", (name, subject, body, int(tid)))
    conn.commit()


@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn



def ensure_price_columns(conn: sqlite3.Connection):
    cur = conn.cursor()
    def add(coldef: str):
        try:
            cur.execute(f"ALTER TABLE registrations ADD COLUMN {coldef}")
        except Exception:
            pass
    add("price_accommodation REAL")
    add("price_breakfasts REAL")
    add("price_lunches REAL")
    add("price_citytax REAL")
    add("price_course REAL")
    add("price_total REAL")
    try:
        cur.execute("SELECT room_type FROM registrations LIMIT 1")
    except Exception:
        add("room_type TEXT")
    conn.commit()


def ensure_room_code_column(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(registrations)")
    cols = [row[1] for row in cur.fetchall()]
    if "room_code" not in cols:
        try:
            cur.execute("ALTER TABLE registrations ADD COLUMN room_code TEXT")
            conn.commit()
        except Exception:
            pass


def ensure_piece_columns(conn: sqlite3.Connection):
    """Repertoár: pridá stĺpce pre part (Skladba 1–5). Tituly skladieb sú globálne inde."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(registrations)")
    cols = {row[1] for row in cur.fetchall()}
    for c in [f"piece{i}_part" for i in range(1,6)]:
        if c not in cols:
            try:
                cur.execute(f"ALTER TABLE registrations ADD COLUMN {c} TEXT")
            except Exception:
                pass
    conn.commit()


def ensure_repertoire_titles_table(conn: sqlite3.Connection):
    """Globálne názvy skladieb (hlavičky stĺpcov)."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS repertoire_titles (
            id INTEGER PRIMARY KEY CHECK (id=1),
            title1 TEXT, title2 TEXT, title3 TEXT, title4 TEXT, title5 TEXT
        )
    """)
    cur.execute("SELECT COUNT(*) FROM repertoire_titles WHERE id=1")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO repertoire_titles (id, title1, title2, title3, title4, title5) VALUES (1, ?, ?, ?, ?, ?)",
            ("Skladba 1", "Skladba 2", "Skladba 3", "Skladba 4", "Skladba 5"),
        )
    conn.commit()


def get_repertoire_titles(conn: sqlite3.Connection):
    ensure_repertoire_titles_table(conn)
    row = conn.execute("SELECT title1, title2, title3, title4, title5 FROM repertoire_titles WHERE id=1").fetchone()
    if row:
        return list(row)
    return ["Skladba 1","Skladba 2","Skladba 3","Skladba 4","Skladba 5"]


def save_repertoire_titles(conn: sqlite3.Connection, titles):
    ensure_repertoire_titles_table(conn)
    conn.execute(
        "UPDATE repertoire_titles SET title1=?, title2=?, title3=?, title4=?, title5=? WHERE id=1",
        (titles[0], titles[1], titles[2], titles[3], titles[4]),
    )
    conn.commit()


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    ensure_email_templates_table(conn)

    # Registrácie účastníkov
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            name TEXT,
            email TEXT,
            phone TEXT,
            age INTEGER,
            course TEXT,
            instrument TEXT,
            school TEXT,
            year_of_study TEXT,
            people_count INTEGER,
            ensemble_type TEXT,
            member_names TEXT,
            lesson_count INTEGER,
            preferred_lectors TEXT, -- JSON list
            wants_accommodation INTEGER,
            arrival_date TEXT,
            departure_date TEXT,
            room_type TEXT,
            breakfasts INTEGER,
            lunches INTEGER,
            notes TEXT
        )
        """
    )

    # Lektori
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS lectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
        """
    )

    # Časové sloty
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT,           -- ISO dátum
            start TEXT,         -- HH:MM
            end TEXT,           -- HH:MM
            teacher TEXT,       -- meno lektora; pre špeciálny program prázdne
            label TEXT,         -- popis
            is_blocked INTEGER  -- 1 = blokované (špeciálny program), 0 = voľné na výučbu
        )
        """
    )

    # Priradenia
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_id INTEGER,
            registration_id INTEGER,
            FOREIGN KEY(slot_id) REFERENCES slots(id),
            FOREIGN KEY(registration_id) REFERENCES registrations(id)
        )
        """
    )
    conn.commit()

    # Migrácie
    ensure_price_columns(conn)
    ensure_room_code_column(conn)
    ensure_piece_columns(conn)
    ensure_repertoire_titles_table(conn)
    ensure_feedback_tables(conn)

    # Seed lektorov len ak je tabuľka prázdna (prvé spustenie)
    cur.execute("SELECT COUNT(*) FROM lectors")
    if (cur.fetchone()[0] or 0) == 0:
        cur.executemany(
            "INSERT INTO lectors(name) VALUES(?)",
            [(lec,) for lec in DEFAULT_LECTORS]
        )

    conn.commit()

# -----------------------------
# Autentifikácia (jednoduchá)
# -----------------------------

def get_secret(path: str, default: Optional[str] = None) -> Optional[str]:
    try:
        ref = st.secrets
        for key in path.split("."):
            ref = ref[key]
        return ref
    except Exception:
        return default
# =========================
# PLATOBNÉ ÚDAJE (QR SEPA)
# =========================
PAYEE_NAME = "Saxophobia"
PAYEE_IBAN = get_secret("payment.iban", "")
PAYEE_BIC  = get_secret("payment.bic", "")

def login(role: str) -> bool:
    """Vráti True, ak je používateľ prihlásený pre danú rolu."""
    key = f"auth_{role}_ok"
    if st.session_state.get(key):
        return True

    pwd_label = "Heslo pre organizátora" if role == "organizer" else "Heslo pre admina"
    password = st.text_input(pwd_label, type="password", key=f"pwd_{role}")

    organizer_pw = get_secret("auth.organizer_password", "organizator123")
    admin_pw = get_secret("auth.admin_password", "admin123")

    ok = False
    if role == "organizer" and password == organizer_pw:
        ok = True
    if role == "admin" and password == admin_pw:
        ok = True

    if st.button("Prihlásiť", key=f"login_{role}"):
        if ok:
            st.session_state[key] = True
            st.success("Prihlásenie úspešné.")
        else:
            st.error("Nesprávne heslo.")
    return st.session_state.get(key, False)


# -----------------------------
# Utility
# -----------------------------

def to_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def from_json(s: Optional[str]):
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def time_range(start: time, end: time, step_min: int) -> List[Tuple[time, time]]:
    cur = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    out = []
    while cur < end_dt:
        nxt = cur + timedelta(minutes=step_min)
        out.append((cur.time(), nxt.time()))
        cur = nxt
    return out
MAX_CAPACITY = 100

def _parse_instruments(instr_str: str) -> list[str]:
    if not instr_str:
        return []
    return [x.strip() for x in str(instr_str).split(",") if x.strip()]

def get_public_dashboard_stats(conn) -> dict:
    """
    Vracia štatistiky pre horný dashboard:
    - registrations_count = počet riadkov
    - participants_sum = suma people_count (ak chýba -> 1)
    - remaining = MAX_CAPACITY - participants_sum (min 0)
    - top_instruments = list[(instrument, count)]
    """
    df = pd.read_sql_query("SELECT people_count, instrument FROM registrations", conn)

    if df.empty:
        return {
            "registrations_count": 0,
            "participants_sum": 0,
            "remaining": MAX_CAPACITY,
            "top_instruments": [],
        }

    # people_count: ak je prázdne -> 1
    df["people_count"] = pd.to_numeric(df["people_count"], errors="coerce").fillna(1).astype(int)
    participants_sum = int(df["people_count"].sum())

    # instrument: rozparsovať multiselect string "alt sax, tenor sax"
    counts = {}
    for s in df["instrument"].fillna("").tolist():
        for inst in _parse_instruments(s):
            counts[inst] = counts.get(inst, 0) + 1

    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:6]

    remaining = max(0, MAX_CAPACITY - participants_sum)

    return {
        "registrations_count": int(len(df)),
        "participants_sum": participants_sum,
        "remaining": remaining,
        "top_instruments": top,
    }
import qrcode
from io import BytesIO

def _epc_sct_payload(
    *,
    name: str,
    iban: str,
    amount_eur: float,
    bic: str = "",
    remittance: str = "",
) -> str:
    """
    EPC / SEPA Credit Transfer QR payload (EPC069-12).
    amount_eur: napr. 211.50
    remittance: poznámka pre príjemcu (max ~140 znakov je rozumné)
    """
    amt = f"{float(amount_eur):.2f}"
    rem = (remittance or "").strip().replace("\n", " ")[:140]

    # Pozor: poradie riadkov je dôležité
    return "\n".join([
        "BCD",
        "002",
        "1",
        "SCT",
        (bic or "").strip(),
        (name or "").strip(),
        (iban or "").replace(" ", "").strip(),
        f"EUR{amt}",
        "",   # purpose (voliteľné)
        "",   # remittance structured (voliteľné)
        rem,  # remittance unstructured
    ])

def make_qr_png_bytes(payload: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()
def make_paybysquare_png_bytes(*, amount: float, iban: str, bic: str, recipient: str, note: str, vs: str = "") -> bytes:
    # Pozn.: note má mať max ~35 znakov (podľa služby)
    base = "https://qr.slada.sk/qr.php"  # alebo tvoja vlastná hostovaná verzia
    params = {
        "price": f"{float(amount):.2f}",
        "note": (note or "")[:35],
        "recipient": (recipient or "")[:70],  # služba má “?” v README, ale toto je bezpečné
        "iban": (iban or "").replace(" ", ""),
        "swift": (bic or "").replace(" ", ""),
        "vs": (vs or ""),
        "pixelsize": "4",
        "pixelpadding": "2",
    }
    r = requests.get(base, params=params, timeout=15)
    r.raise_for_status()
    return r.content


# -----------------------------
# Ceny – výpočet / persist
# -----------------------------

def compute_prices(
    df: pd.DataFrame,
    rate_night: float,
    rate_breakfast: float,
    rate_lunch: float,
    rate_citytax: float,
    course_prices: dict,
    rate_course_default: float = 0.0,
) -> pd.DataFrame:

    def nights(row):
        try:
            a = row.get("arrival_date")
            d = row.get("departure_date")
            if a and d and str(a) != "" and str(d) != "":
                a = pd.to_datetime(a).date()
                d = pd.to_datetime(d).date()
                return max(0, (d - a).days)
        except Exception:
            return 0
        return 0

    df = df.copy()

    ppl = pd.to_numeric(df.get("people_count", 1), errors="coerce").fillna(1).astype(int)

    wants = pd.to_numeric(df.get("wants_accommodation", 0), errors="coerce").fillna(0).astype(int)
    has_acc = wants == 1

    n = df.apply(nights, axis=1)
    n = n.where(has_acc, 0)  # ✅ ak nechce ubytovanie, noci = 0

    bfast = pd.to_numeric(df.get("breakfasts", 0), errors="coerce").fillna(0).astype(int)
    bfast = bfast.where(has_acc, 0)  # ✅ raňajky len pri ubytovaní

    lunch = pd.to_numeric(df.get("lunches", 0), errors="coerce").fillna(0).astype(int)  # obedy môžu byť aj bez ubytovania

    df["price_accommodation"] = n * float(rate_night)
    df["price_breakfasts"] = bfast * float(rate_breakfast)
    df["price_lunches"] = lunch * float(rate_lunch)
    df["price_citytax"] = (n * ppl * float(rate_citytax)).where(has_acc, 0)  # ✅ city tax len pri ubytovaní

    def _course_price(x):
        c = (str(x or "")).strip().upper()
        if c in course_prices:
            return float(course_prices[c])
        return float(rate_course_default)

    df["price_course"] = df.get("course", "").apply(_course_price)

    df["price_total"] = df[
        ["price_accommodation", "price_breakfasts", "price_lunches", "price_citytax", "price_course"]
    ].sum(axis=1)

    return df



def persist_prices(conn: sqlite3.Connection, priced_df: pd.DataFrame):
    cols = ["price_accommodation","price_breakfasts","price_lunches","price_citytax","price_course","price_total"]
    cur = conn.cursor()
    for _, r in priced_df.iterrows():
        if "id" not in r or pd.isna(r["id"]):
            continue
        values = [r.get(c) for c in cols]
        cur.execute(
            "UPDATE registrations SET price_accommodation=?, price_breakfasts=?, price_lunches=?, price_citytax=?, price_course=?, price_total=? WHERE id=?",
            values + [int(r["id"])],
        )
    conn.commit()


# -----------------------------
# Verejná prihláška
# -----------------------------

def page_application():
    lang = st.session_state.get("lang", "SK")
    txt = TEXTS.get(lang, TEXTS["SK"])

    st.header(txt["application_header"])
    st.write(txt["application_fill"])

    # -----------------------------
    # Prihláška (BEZ st.form) – aby fungoval live update počtu ľudí
    # -----------------------------

    # Základné údaje
    name = st.text_input(txt["name"], key="app_name")
    email = st.text_input(txt["email"], key="app_email")
    phone = st.text_input(txt["phone"], key="app_phone")
    age = st.number_input(txt["age"], min_value=5, max_value=100, value=18, key="app_age")
    course = st.selectbox(txt["course"], options=COURSES, key="app_course")
    instrument = st.multiselect(txt["instrument"], options=INSTRUMENTS, key="app_instrument")

    school_label = txt["school"] + (
        " (napr. ZUŠ, konzervatórium)" if lang == "SK"
        else " (e.g. music school, conservatory)"
    )
    school = st.text_input(school_label, key="app_school")

    year_label = "Ročník štúdia" if lang == "SK" else "Year of study"
    year_of_study = st.text_input(year_label, key="app_year_of_study")

    # --- Skupina / ensemble (poradie: Typ -> Počet ľudí -> Názov telesa) ---
    AUTO_PEOPLE = {
        "jednotlivec": 1,
        "duo": 2,
        "trio": 3,
        "kvarteto": 4,
        "kvinteto": 5,
    }

    ensemble_label = (
        "Typ (jednotlivec / duo / trio / kvarteto ...)"
        if lang == "SK" else
        "Type (solo / duo / trio / quartet ...)"
    )

    people_label = (
        "Počet ľudí v skupine (1 = jednotlivec)"
        if lang == "SK" else
        "Number of people in the group (1 = solo)"
    )

    members_label = (
        "Názov hudobného telesa"
        if lang == "SK" else
        "Name of ensemble / group"
    )

    # init session_state
    st.session_state.setdefault("ensemble_type", ENSEMBLE_TYPES[0])
    st.session_state.setdefault("people_count", 1)
    st.session_state.setdefault("member_names", "")

    def _sync_people():
        t = (st.session_state.get("ensemble_type") or "")
        base = t.split("/")[0].strip().lower()
        is_other = ("iné" in base) or ("ine" in base) or ("other" in base)
        if (base in AUTO_PEOPLE) and (not is_other):
            st.session_state["people_count"] = int(AUTO_PEOPLE[base])

    ensemble_type = st.selectbox(
        ensemble_label,
        ENSEMBLE_TYPES,
        key="ensemble_type",
        on_change=_sync_people
    )

    base_type = (ensemble_type or "").split("/")[0].strip().lower()
    is_other = ("iné" in base_type) or ("ine" in base_type) or ("other" in base_type)
    is_auto = (base_type in AUTO_PEOPLE) and (not is_other)

    people_count = st.number_input(
        people_label,
        min_value=1,
        max_value=10,
        step=1,
        key="people_count",
        disabled=is_auto
    )

    # jednotlivec = pole read-only, skupina = editovateľné
    is_solo = base_type == "jednotlivec"

    member_names = st.text_input(
        members_label,
        key="member_names",
        disabled=is_solo
    )

    lesson_count = 0  # určí organizátor

    # Lektori
    conn = get_conn()
    lectors_df = pd.read_sql_query("SELECT name FROM lectors ORDER BY name", conn)
    lectors = lectors_df["name"].tolist() or DEFAULT_LECTORS

    pref_label = (
        "Preferovaní lektori (v poradí priority)"
        if lang == "SK" else
        "Preferred teachers (in order of priority)"
    )
    preferred_lectors = st.multiselect(pref_label, options=lectors, default=[], key="app_preferred_lectors")

    # Ubytovanie a strava (ponechaj ako máš, len pridaj keys ak chceš)
    st.subheader("Ubytovanie a strava" if lang == "SK" else "Accommodation and meals")

    wants_label = "Potrebujem ubytovanie" if lang == "SK" else "I need accommodation"
    wants_accommodation = st.checkbox(wants_label, value=False, key="app_wants_accommodation")

    arrival_date = st.date_input("Príchod" if lang == "SK" else "Arrival", value=EVENT_START, key="app_arrival")
    departure_date = st.date_input("Odchod" if lang == "SK" else "Departure", value=EVENT_END, key="app_departure")

    room_type = st.selectbox("Typ izby" if lang == "SK" else "Room type", ROOM_TYPES, key="app_room_type")

    _days_inclusive = (EVENT_END - EVENT_START).days
    breakfasts = st.number_input("Počet raňajok" if lang == "SK" else "Number of breakfasts", 0, 10, _days_inclusive, key="app_breakfasts")
    lunches = st.number_input("Počet obedov" if lang == "SK" else "Number of lunches", 0, 15, _days_inclusive, key="app_lunches")

    notes_label = (
        "Poznámka k strave (alergie, intolerancie a pod.)"
        if lang == "SK" else
        "Notes on diet (allergies, intolerances, etc.)"
    )
    notes = st.text_area(notes_label, key="app_notes")

    submit_label = txt.get("submit", "Odoslať prihlášku" if lang == "SK" else "Submit application")
    submitted = st.button(submit_label, key="app_submit")

    if submitted:
        if not name or not email:
            st.error("Meno a e-mail sú povinné." if lang == "SK" else "Name and e-mail are required.")
        else:
            instrument_str = ", ".join(instrument) if instrument else ""

            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO registrations (
                    created_at, name, email, phone, age, course, instrument,
                    school, year_of_study, people_count, ensemble_type, member_names,
                    lesson_count, preferred_lectors, wants_accommodation,
                    arrival_date, departure_date, room_type, breakfasts, lunches, notes,
                    room_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    name,
                    email,
                    phone,
                    int(age),
                    course,
                    instrument_str,
                    school,
                    year_of_study,
                    int(people_count),
                    ensemble_type,
                    member_names,
                    0,
                    to_json(preferred_lectors),
                    1 if wants_accommodation else 0,
                    arrival_date.isoformat(),
                    departure_date.isoformat(),
                    room_type,
                    int(breakfasts),
                    int(lunches),
                    notes,
                    None,
                ),
            )
            conn.commit()
            st.success(txt["success"])



# -----------------------------
# Organizátor – prehľad a export
# -----------------------------

def save_edited_registrations(conn: sqlite3.Connection, df: pd.DataFrame):
    cur = conn.cursor()

    # Stĺpce, ktoré CHCEME zapisovať
    desired_cols = [
        "phone","age","course","instrument","people_count","ensemble_type","member_names","lesson_count",
        "wants_accommodation","arrival_date","departure_date","room_type","breakfasts","lunches","notes",
        "price_accommodation","price_breakfasts","price_citytax","price_course","price_total", "price_lunches",
        "room_code",
    ]

    # Zistíme, ktoré stĺpce naozaj existujú v DB
    cur.execute("PRAGMA table_info(registrations)")
    db_cols = {row[1] for row in cur.fetchall()}

    # Použijeme len prienik: existuje v DB aj v DataFrame
    cols = [c for c in desired_cols if c in db_cols and c in df.columns]

    for _, r in df.iterrows():
        reg_id = r.get("id")
        # ak chýba ID (napr. nový prázdny riadok), preskočíme
        if reg_id is None or (pd.isna(reg_id)):
            continue

        values = []
        for c in cols:
            v = r.get(c)

            # Ak je tam zoznam (hlavne pri room_code), prekonvertuj na string
            if isinstance(v, (list, tuple)):
                if c == "room_code":
                    # vyber prvý kód izby alebo None
                    v = v[0] if v else None
                else:
                    # ostatné listy spojíme čiarkou
                    v = ", ".join(str(x) for x in v)

            values.append(v)

        placeholders = ", ".join(f"{c}=?" for c in cols)
        cur.execute(
            f"UPDATE registrations SET {placeholders} WHERE id=?",
            values + [int(reg_id)],
        )

    conn.commit()




def compute_room_occupancy(reg_df: pd.DataFrame) -> Dict[str, int]:
    """Spočíta obsadenosť podľa room_code a people_count (chýbajúce = 1)."""
    df = reg_df.copy()
    if "people_count" not in df.columns:
        df["people_count"] = 1
    if "room_code" not in df.columns:
        return {code: 0 for code in ROOM_CODES}

    assigned = df.dropna(subset=["room_code"])
    grouped = assigned.groupby("room_code")["people_count"].sum().to_dict()
    # doplň nuly pre neobsadené izby
    for code in ROOM_CODES:
        grouped.setdefault(code, 0)
    return grouped


def capacity_overview(reg_df: pd.DataFrame):
    st.subheader("Ubytovacie kapacity – plnenie")
    occ = compute_room_occupancy(reg_df)

    total_capacity = sum(ROOM_CAPACITY_BY_CODE.values())
    total_occupied = sum(min(occ[c], ROOM_CAPACITY_BY_CODE[c]) for c in ROOM_CODES)
    st.write(f"Spolu obsadené: **{total_occupied}** / **{total_capacity}** miest")

    for code in ROOM_CODES:
        cap = ROOM_CAPACITY_BY_CODE[code]
        used = occ.get(code, 0)
        ratio = min(used / cap if cap else 0, 1.0)
        label = ROOM_LABEL_BY_CODE[code]
        over = used > cap

        st.write(f"**{code}** – {label}: {used}/{cap}" + ("  ⚠️ nad kapacitou!" if over else ""))
        st.progress(ratio)
        if over:
            st.warning(f"Izba {code} je preplnená o {used - cap} miest.")


def save_repertoire(conn: sqlite3.Connection, df_rep: pd.DataFrame):
    """Uloží vybrané party (Skladba 1–5) podľa ID."""
    cur = conn.cursor()
    cols = [f"piece{i}_part" for i in range(1, 6)]

    for _, r in df_rep.iterrows():
        # Bez ID nič neukladáme
        if "id" not in r or pd.isna(r["id"]):
            continue

        values = []
        for c in cols:
            v = r.get(c)

            # Streamlit vie niekedy vrátiť list (napr. [1]) – zoberieme prvú hodnotu
            if isinstance(v, (list, tuple)):
                v = v[0] if v else None

            values.append(v)

        placeholders = ", ".join([f"{c}=?" for c in cols])
        cur.execute(
            f"UPDATE registrations SET {placeholders} WHERE id=?",
            values + [int(r["id"])],
        )

    conn.commit()


def _get_gmail_creds():
    """Načítaj prihlasovacie údaje z .streamlit/secrets.toml"""
    user = get_secret("gmail.user")
    app_password = get_secret("gmail.app_password")
    sender_name = get_secret("gmail.sender_name", "Saxophobia")
    return user, app_password, sender_name

def _clean_emails(emails: List[str]) -> List[str]:
    out = []
    for e in emails:
        if not e:
            continue
        e = str(e).strip()
        if "@" in e and "." in e:
            out.append(e)
    # unikátne + zachovať poradie
    seen = set()
    uniq = []
    for e in out:
        if e not in seen:
            uniq.append(e); seen.add(e)
    return uniq

def send_email_smtp(subject: str, body: str, to_addrs: List[str], bcc_addrs: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Odošle e-mail cez Gmail SMTP (STARTTLS).
    Posiela multipart/alternative: text + HTML (pevný font, správne odseky).
    """
    user, app_password, sender_name = _get_gmail_creds()
    if not user or not app_password:
        return False, "Chýbajú Gmail prihlasovacie údaje v secrets."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{user}>"
    msg["To"] = ", ".join(to_addrs) if to_addrs else user  # fallback
    if bcc_addrs:
        msg["Bcc"] = ", ".join(bcc_addrs)

    # plain-text + HTML varianta
    msg.set_content(body or "")
    html_body = _wrap_html_from_text(body or "")
    msg.add_alternative(html_body, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(context=context)
            server.login(user, app_password)
            server.send_message(msg)
        return True, "E-mail odoslaný."
    except Exception as e:
        return False, f"Chyba pri odosielaní: {e}"



def page_organizer():
    st.header("Organizátor – prehľad prihlášok a kalkulácia")
    if not login("organizer"):
        st.stop()

    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM registrations ORDER BY created_at DESC", conn)

    # Sadzby (nastaviteľné organizátorom)
    with st.expander("Sadzby a hromadný výpočet cien"):
        colA, colB, colC, colD, colE = st.columns(5)

        with colA:
            rate_night = st.number_input("Cena za noc (€)", min_value=0.0, value=36.0, step=1.0)
        with colB:
            rate_breakfast = st.number_input("Cena raňajok (€) / ks", min_value=0.0, value=3.0, step=0.5)
        with colC:
            rate_lunch = st.number_input("Cena obeda (€) / ks", min_value=0.0, value=10.5, step=0.5)  # ✅ NOVÉ
        with colD:
            rate_citytax = st.number_input("Mestská daň (€) / osoba / noc", min_value=0.0, value=3.5, step=0.5)
        with colE:
            st.markdown("**Kurz (€)**")
            rate_course_A = st.number_input("A (aktívna)", min_value=0.0, value=180.0, step=10.0)
            rate_course_P = st.number_input("P (pasívna)", min_value=0.0, value=100.0, step=10.0)
            rate_course_O = st.number_input("O (orchester)", min_value=0.0, value=20.0, step=10.0)
            course_prices = {"A": rate_course_A, "P": rate_course_P, "O": rate_course_O}


        if st.button("Vypočítať ceny podľa sadzieb") and not df.empty:
            df_priced = compute_prices(
                df,
                rate_night=rate_night,
                rate_breakfast=rate_breakfast,
                rate_lunch=rate_lunch,
                rate_citytax=rate_citytax,
                course_prices=course_prices,
                rate_course_default=0.0,
            )
            persist_prices(conn, df_priced)
            df = pd.read_sql_query("SELECT * FROM registrations ORDER BY created_at DESC", conn)


    # Parsovanie preferovaných lektorov pre zobrazenie
    if not df.empty:
        df["preferred_lectors"] = df["preferred_lectors"].apply(lambda s: ", ".join(from_json(s) or []))
        for col in ["arrival_date","departure_date"]:
            if col in df.columns:
                df[col] = df[col].fillna("")

        # V hornej tabuľke NEZOBRAZUJEME žiadne 'piece*' stĺpce (patria len do bloku Repertoár)
        piece_cols = [c for c in df.columns if c.startswith("piece")]
        df_top = df.drop(columns=piece_cols, errors="ignore").copy()

        st.caption("Stĺpce sú upraviteľné, vrátane *Počet lekcií*. Stĺpce repertoáru sú presunuté nižšie do samostatného bloku.")
        editable_cols = [
            "phone","age","course","instrument","people_count","ensemble_type","member_names","lesson_count",
            "wants_accommodation","arrival_date","departure_date","room_type","breakfasts","lunches","notes",
            "price_accommodation","price_breakfasts","price_citytax","price_course","price_total", "price_lunches",
            "room_code",
        ]

        column_config = {
            "room_code": st.column_config.SelectboxColumn(
                "Kód izby",
                help="Vyber kód podľa inventára (napr. JK10-1, JK4-2, DK8-1).",
                options=ROOM_CODES,
                required=False,
            ),
        }

        edited = st.data_editor(
            df_top,
            use_container_width=True,
            num_rows="dynamic",
            disabled=[c for c in df_top.columns if c not in editable_cols],
            column_config=column_config,
        )

        col_save, col_export = st.columns([1,2])
        with col_save:
            if st.button("Uložiť zmeny"):
                save_edited_registrations(conn, edited)
                st.success("Zmeny uložené.")
                df = pd.read_sql_query("SELECT * FROM registrations ORDER BY created_at DESC", conn)
                df_top = df.drop(columns=[c for c in df.columns if c.startswith('piece')], errors='ignore').copy()
        with col_export:
            # Export len hornej tabuľky (bez repertoára)
            xlsx_top = to_excel_bytes(edited if isinstance(edited, pd.DataFrame) else df_top)
            st.download_button(
                "Stiahnuť XLSX – Prehľad prihlášok (bez repertoára)",
                data=xlsx_top,
                file_name="registracie_prehlad.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    else:
        st.info("Zatiaľ bez prihlášok.")

        # Kapacitné plnenie – prehľad
    if not df.empty:
        capacity_overview(df)

    # ---------- QR PLATBA (PayBySquare) ----------
    st.subheader("💳 QR platba (PayBySquare)")

    if not PAYEE_IBAN:
        st.warning("Doplň IBAN do secrets: [payment] iban=... (voliteľne aj bic=...)")
    else:
        if df.empty:
            st.info("Zatiaľ bez prihlášok.")
        else:
            pick = st.selectbox(
                "Vyber účastníka",
                options=df["id"].tolist(),
                format_func=lambda rid: f"ID {rid} – {df.loc[df['id']==rid, 'name'].values[0]}",
                key="qr_pick_id",
            )

            row = df[df["id"] == pick].iloc[0]
            amount = float(row.get("price_total") or 0.0)

            note = f"Saxophobia {EVENT_START.year} | ID {int(row['id'])} | {row.get('name','')}".strip()

            st.write(f"Suma: **{amount:.2f} €**")

            qr_png = make_paybysquare_png_bytes(
                amount=amount,
                iban=PAYEE_IBAN,
                bic=PAYEE_BIC,
                recipient=PAYEE_NAME,
                note=note,
                vs=str(int(row["id"])),
            )

            st.image(
                qr_png,
                caption="Naskenuj v bankovej appke (PayBySquare)",
                width=260
            )

            st.download_button(
                "Stiahnuť QR (PNG)",
                data=qr_png,
                file_name=f"qr_platba_ID{int(row['id'])}_paybysquare.png",
                mime="image/png",
            )


     
    # --- Hromadné vymazanie registrácií (nový ročník) ---
    with st.expander("Hromadné vymazanie registrácií – OPATRNE"):
        st.warning(
            "Toto vymaže všetky prihlášky zo systému vrátane ich priradení "
            "k lekciám. Použi len pri začiatku nového ročníka."
        )

        confirm = st.checkbox(
            "Áno, chcem vymazať všetky registrácie a súvisiace priradenia.",
            value=False,
            key="confirm_delete_regs",
        )

        if st.button("Vymazať všetky registrácie", disabled=not confirm, key="btn_delete_regs"):
            cur = conn.cursor()

            # 1) zmazať závislé tabuľky (priradenia)
            cur.execute("DELETE FROM assignments")

            # 2) zmazať registrácie
            cur.execute("DELETE FROM registrations")

            # 3) reset AUTOINCREMENT počítadiel (SQLite)
            # funguje len pre tabuľky, ktoré majú AUTOINCREMENT (ty ho máš)
            try:
                cur.execute("DELETE FROM sqlite_sequence WHERE name='assignments'")
                cur.execute("DELETE FROM sqlite_sequence WHERE name='registrations'")
            except Exception:
                pass  # ak by sqlite_sequence neexistovala (pri non-autoincrement DB), ignoruj

            conn.commit()

            st.success("Všetky registrácie a priradenia boli vymazané. Nové ID začne od 1.")
            st.rerun()

    

    # --- 📧 EMAILY ORGANIZÁTORA ---
    st.subheader("📧 Odoslať e-maily")

    # --- ŠABLÓNY E-MAILOV (len správa/uloženie) ---
    st.markdown("### 🧩 E-mailové šablóny")
    templates = load_email_templates(conn)
    with st.expander("Upraviť a uložiť šablóny (1–3)"):
        tabs_tpl = st.tabs([f"Šablóna {i}" for i in [1, 2, 3]])
        for i, tab in zip([1, 2, 3], tabs_tpl):
            with tab:
                tname = st.text_input("Názov šablóny", value=templates[i]["name"], key=f"tpl_name_{i}")
                tsubj = st.text_input("Predmet", value=templates[i]["subject"], key=f"tpl_subj_{i}")
                tbody = st.text_area("Telo správy", value=templates[i]["body"], height=200, key=f"tpl_body_{i}")
                if st.button(f"Uložiť šablónu {i}", key=f"save_tpl_{i}"):
                    save_email_template(conn, i, tname, tsubj, tbody)
                    st.success(f"Šablóna {i} uložená.")
                    st.rerun()

    if df.empty:
        st.info("Žiadne prihlášky – nie je komu posielať e-mail.")
    else:
        # Zoznam príjemcov
        all_names_emails = df[["name", "email"]].fillna("")
        all_emails = _clean_emails(all_names_emails["email"].tolist())

        tabs = st.tabs(["Skupinový e-mail", "Jednotlivcom"])

        # --- Skupinový e-mail (BCC) ---
        with tabs[0]:
            st.caption(f"Vybraných príjemcov: {len(all_emails)}")
            st.write(", ".join(all_emails) if all_emails else "—")

            # výber šablóny + načítanie
            group_tpl_id = st.selectbox(
                "Použiť šablónu",
                options=[1, 2, 3],
                index=0,
                format_func=lambda i: f"{i} – {templates[i]['name']}",
                key="group_tpl_id",
            )
            if st.button("Načítať šablónu do formulára", key="load_group_tpl"):
                st.session_state["subj_group"] = templates[group_tpl_id]["subject"]
                st.session_state["body_group"] = templates[group_tpl_id]["body"]

            subj_group = st.text_input(
                "Predmet (skupinový)",
                value=st.session_state.get("subj_group", templates[group_tpl_id]["subject"]),
                key="subj_group",
            )
            body_group = st.text_area(
                "Text správy (skupinový)",
                value=st.session_state.get("body_group", templates[group_tpl_id]["body"]),
                height=200,
                key="body_group",
            )

            # Len dve tlačidlá: Gmail + predvolený klient (mailto)
            col_gmail, col_mailto = st.columns([1, 1])

            with col_gmail:
                gmail_url = (
                    "https://mail.google.com/mail/?view=cm&fs=1&tf=1"
                    f"&su={quote(subj_group or '')}"
                    f"&body={quote((body_group or '').replace('\n', '\r\n'))}"
                    f"&bcc={quote(','.join(all_emails))}"
                )
                st.link_button("Otvoriť v Gmaili (BCC)", gmail_url)

            with col_mailto:
                mailto_bcc = ",".join(all_emails)
                mailto_link = (
                    f"mailto:?subject={quote(subj_group or '')}"
                    f"&body={quote((body_group or '').replace('\n', '\r\n'))}"
                    f"&bcc={quote(mailto_bcc)}"
                )
                st.link_button("Otvoriť v predvolenom klientovi (BCC)", mailto_link)


        # --- Jednotlivé e-maily ---
        with tabs[1]:
            st.caption("Vyber účastníkov, ktorým chceš poslať individuálny e-mail (napr. k platbám).")

            ind_tpl_id = st.selectbox(
                "Použiť šablónu",
                options=[1, 2, 3],
                index=1,
                format_func=lambda i: f"{i} – {templates[i]['name']}",
                key="ind_tpl_id",
            )
            if st.button("Načítať šablónu do formulára", key="load_ind_tpl"):
                st.session_state["subj_ind"] = templates[ind_tpl_id]["subject"]
                st.session_state["body_ind"] = templates[ind_tpl_id]["body"]

            subj_ind = st.text_input(
                "Predmet (individuálne)",
                value=st.session_state.get("subj_ind", templates[ind_tpl_id]["subject"]),
                key="subj_ind",
            )
            body_ind = st.text_area(
                "Text správy (individuálne)",
                value=st.session_state.get("body_ind", templates[ind_tpl_id]["body"]),
                height=180,
                key="body_ind",
            )

            df_mail = all_names_emails.copy()
            df_mail["send"] = False
            df_mail = st.data_editor(
                df_mail,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "name": st.column_config.TextColumn("Meno", disabled=True),
                    "email": st.column_config.TextColumn("E-mail", disabled=True),
                    "send": st.column_config.CheckboxColumn("Odoslať?", help="Zaškrtni pre odoslanie."),
                },
            )

            chosen_clean = _clean_emails(df_mail[df_mail["send"] == True]["email"].tolist())

            # Len dve tlačidlá pre každého vybraného príjemcu: Gmail + predvolený klient
            if chosen_clean:
                st.info("Otvoriť správy pre vybraných príjemcov:")
                for rcpt in chosen_clean:
                    col_gm, col_mt = st.columns([1, 1])

                    with col_gm:
                        gmail_link = (
                            "https://mail.google.com/mail/?view=cm&fs=1&tf=1"
                            f"&to={quote(rcpt)}"
                            f"&su={quote(subj_ind or '')}"
                            f"&body={quote((body_ind or '').replace('\n', '\r\n'))}"
                        )
                        st.link_button(f"Otvoriť v Gmaili pre {rcpt}", gmail_link)

                    with col_mt:
                        mailto_link = (
                            f"mailto:{rcpt}?subject={quote(subj_ind or '')}"
                            f"&body={quote((body_ind or '').replace('\n', '\r\n'))}"
                        )
                        st.link_button(f"Otvoriť v predvolenom klientovi pre {rcpt}", mailto_link)
            else:
                st.caption("Vyber aspoň jedného príjemcu v tabuľke vyššie.")



    # Repertoár účastníkov – len 5 dropdown stĺpcov, hlavičky editovateľné globálne
    st.subheader("Repertoár účastníkov")
    titles = get_repertoire_titles(conn)
    with st.expander("Názvy skladieb (globálne)"):
        t1, t2, t3, t4, t5 = st.columns(5)
        with t1: titles[0] = st.text_input("Skladba 1 – názov", value=titles[0])
        with t2: titles[1] = st.text_input("Skladba 2 – názov", value=titles[1])
        with t3: titles[2] = st.text_input("Skladba 3 – názov", value=titles[2])
        with t4: titles[3] = st.text_input("Skladba 4 – názov", value=titles[3])
        with t5: titles[4] = st.text_input("Skladba 5 – názov", value=titles[4])
        if st.button("Uložiť názvy skladieb"):
            save_repertoire_titles(conn, titles)
            st.success("Názvy skladieb uložené.")
            st.rerun()

    if not df.empty:
        base_cols = ["id","name","age","school","instrument"]
        for c in [f"piece{i}_part" for i in range(1,6)]:
            if c not in df.columns:
                df[c] = None
        rep_df = df[base_cols + [f"piece{i}_part" for i in range(1,6)]].copy()

        part_options = ["1","1/1","1/2","2","3","4","solo 1","solo 2"]
        cfg = {
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "name": st.column_config.TextColumn("Meno účastníka", disabled=True),
            "age": st.column_config.NumberColumn("Vek", disabled=True),
            "school": st.column_config.TextColumn("Škola", disabled=True),
            "instrument": st.column_config.TextColumn("Nástroj", disabled=True),
        }
        for i in range(1,6):
            cfg[f"piece{i}_part"] = st.column_config.SelectboxColumn(
                titles[i-1],
                options=part_options,
                required=False,
            )

        edited_rep = st.data_editor(
            rep_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config=cfg,
        )

        col_rep_save, col_rep_export = st.columns([1,2])
        with col_rep_save:
            if st.button("Uložiť repertoár"):
                save_repertoire(conn, edited_rep)
                st.success("Repertoár uložený.")
                st.rerun()
        with col_rep_export:
            rep_export = edited_rep.rename(columns={f"piece{i}_part": titles[i-1] for i in range(1,6)}) \
                         if isinstance(edited_rep, pd.DataFrame) else \
                         rep_df.rename(columns={f"piece{i}_part": titles[i-1] for i in range(1,6)})
            xlsx_rep = to_excel_bytes(rep_export)
            st.download_button(
                "Stiahnuť XLSX – Repertoár účastníkov",
                data=xlsx_rep,
                file_name="repertoar_ucastnikov.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return output.getvalue()


# -----------------------------
# Admin – lektori, sloty, auto-rozvrh
# -----------------------------


def save_lectors_changes(conn: sqlite3.Connection,
                         edited_df: pd.DataFrame,
                         original_df: pd.DataFrame) -> bool:
    """Uloží zmeny v tabuľke lektorov.
       - pridá nové riadky (id prázdne)
       - premenuje existujúcich (a prepíše meno aj v slots.teacher a v preferred_lectors)
       - zmaže riadky, ktoré v editovanej tabuľke chýbajú (a odstráni ich sloty)
    """
    cur = conn.cursor()

    # 1) kontrola duplicít mien (case-insensitive)
    names = [(str(x).strip()) for x in edited_df.get("name", pd.Series([])).tolist() if str(x).strip()]
    if len({n.lower() for n in names}) != len(names):
        st.error("Mená lektorov musia byť jedinečné (nezáleží na veľkosti písmen).")
        return False

    # mapy/ID
    orig_map = pd.Series(original_df["name"].values, index=original_df["id"].values).to_dict()

    added = updated = deleted = 0

    # 2) zmazané riadky
    orig_ids = set(original_df["id"].dropna().astype(int)) if not original_df.empty else set()
    edited_ids = set(edited_df["id"].dropna().astype(int)) if "id" in edited_df and not edited_df.empty else set()
    for del_id in sorted(orig_ids - edited_ids):
        old = orig_map.get(del_id)
        cur.execute("DELETE FROM lectors WHERE id=?", (int(del_id),))
        # čistka slotov tohto lektora (nech nezostanú siroty)
        cur.execute("DELETE FROM slots WHERE teacher=?", (old,))
        deleted += 1

    # 3) nové + premenované
    for _, row in edited_df.iterrows():
        new_name = (row.get("name") or "").strip()
        if not new_name:
            continue
        rid = row.get("id")
        if pd.isna(rid) or rid is None:
            # nový lektor
            try:
                cur.execute("INSERT INTO lectors(name) VALUES(?)", (new_name,))
                added += 1
            except Exception as e:
                st.error(f"Nepodarilo sa pridať '{new_name}': {e}")
        else:
            rid = int(rid)
            old_name = orig_map.get(rid)
            if old_name and old_name != new_name:
                try:
                    # premenovať v master tabuľke
                    cur.execute("UPDATE lectors SET name=? WHERE id=?", (new_name, rid))
                    # premapovať sloty
                    cur.execute("UPDATE slots SET teacher=? WHERE teacher=?", (new_name, old_name))
                    # premapovať preferencie v registráciách
                    rows = conn.execute("SELECT id, preferred_lectors FROM registrations").fetchall()
                    for rr in rows:
                        pref = from_json(rr["preferred_lectors"]) or []
                        if old_name in pref:
                            pref = [new_name if x == old_name else x for x in pref]
                            conn.execute("UPDATE registrations SET preferred_lectors=? WHERE id=?",
                                         (to_json(pref), rr["id"]))
                    updated += 1
                except Exception as e:
                    st.error(f"Nepodarilo sa premenovať '{old_name}' na '{new_name}': {e}")

    conn.commit()
    st.success(f"Zmeny uložené – pridané: {added}, premenované: {updated}, odstránené: {deleted}.")
    return True



def page_admin():
    st.header("Admin – rozvrh a lektori")
    if not login("admin"):
        st.stop()

    conn = get_conn()
    cur = conn.cursor()

    # --- Lektori ---
    st.subheader("Lektori")

    orig_lec_df = pd.read_sql_query("SELECT id, name FROM lectors ORDER BY id", conn)

    st.caption("Tabuľka je editovateľná. Môžeš pridávať nové riadky alebo mazať existujúce.")
    edited_lec_df = st.data_editor(
        orig_lec_df,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "name": st.column_config.TextColumn("Meno lektora"),
        },
    )

    col_lec_save, col_lec_seed = st.columns([1, 1])
    with col_lec_save:
        if st.button("Uložiť zmeny lektorov"):
            if save_lectors_changes(conn, edited_lec_df, orig_lec_df):
                st.rerun()

    with col_lec_seed:
        # len pomocné tlačidlo – keď je tabuľka úplne prázdna
        if st.button("Doplnit vzorový zoznam (ak je prázdne)"):
            check = pd.read_sql_query("SELECT COUNT(*) AS c FROM lectors", conn)["c"].iloc[0]
            if check == 0:
                cur.executemany("INSERT INTO lectors(name) VALUES(?)",
                                [(n,) for n in DEFAULT_LECTORS])
                conn.commit()
                st.success("Doplnili sme vzorový zoznam.")
                st.rerun()
            else:
                st.info("Tabuľka nie je prázdna.")


    # --- Sloty ---
    st.subheader("Časové sloty")
    st.caption("Slot = riadok v matici: deň, od–do, podľa učiteľa alebo špeciálny program (blokované).")

    # Rýchle generovanie slotov podľa denného plánu
    with st.expander("Generovať sloty (rýchlo)"):
        colA, colB, colC = st.columns(3)
        with colA:
            day_from = st.date_input("Od dňa", value=EVENT_START)
            day_to   = st.date_input("Do dňa", value=EVENT_END)
        with colB:
            start_default = st.time_input("Predvolený začiatok", value=time(9, 0),  key="gen_start")
            end_default   = st.time_input("Predvolený koniec",   value=time(18, 0), key="gen_end")
        with colC:
            len_default   = st.number_input("Dĺžka lekcie (min)", min_value=15, max_value=120, value=45, step=5, key="gen_len")
            teachers      = pd.read_sql_query("SELECT name FROM lectors ORDER BY name", conn)["name"].tolist()

        # zoznam dní v intervale (vrátane)
        days = []
        d = day_from
        while d <= day_to:
            days.append(d)
            d += timedelta(days=1)

        st.markdown("#### Denný plán (nastav pre každý deň iné časy)")
        st.caption("Predvolené hodnoty vyššie vieš jedným klikom prepísať do všetkých dní.")

        # Pomocné tlačidlá na vyplnenie
        cfill1, cfill2, cclear = st.columns([1,1,1])
        with cfill1:
            if st.button("Predvyplniť všetky dni predvolenými časmi"):
                for _d in days:
                    st.session_state[f"start_{_d.isoformat()}"] = start_default
                    st.session_state[f"end_{_d.isoformat()}"]   = end_default
                    st.session_state[f"len_{_d.isoformat()}"]   = len_default
        with cfill2:
            if st.button("Festivalový preset (Pi 8–17, So 8–16, Ne 8–15)"):
                for _d in days:
                    wd = _d.weekday()  # 0=Po ... 4=Pi, 5=So, 6=Ne
                    if wd == 4:
                        st.session_state[f"start_{_d.isoformat()}"] = time(8,0)
                        st.session_state[f"end_{_d.isoformat()}"]   = time(17,0)
                    elif wd == 5:
                        st.session_state[f"start_{_d.isoformat()}"] = time(8,0)
                        st.session_state[f"end_{_d.isoformat()}"]   = time(16,0)
                    elif wd == 6:
                        st.session_state[f"start_{_d.isoformat()}"] = time(8,0)
                        st.session_state[f"end_{_d.isoformat()}"]   = time(15,0)
                    else:
                        st.session_state[f"start_{_d.isoformat()}"] = start_default
                        st.session_state[f"end_{_d.isoformat()}"]   = end_default
                    st.session_state[f"len_{_d.isoformat()}"]       = len_default
        with cclear:
            if st.button("Vyčistiť nastavenia dní"):
                for _d in days:
                    for k in (f"start_{_d.isoformat()}", f"end_{_d.isoformat()}", f"len_{_d.isoformat()}"):
                        if k in st.session_state:
                            del st.session_state[k]

        # Editor pre každý deň
        for _d in days:
            c1, c2, c3, c4 = st.columns([1.2, 1, 1, 0.8])
            with c1:
                st.markdown(f"**{_d.strftime('%a %Y-%m-%d')}**")
            with c2:
                st.time_input("Začiatok", key=f"start_{_d.isoformat()}",
                              value=st.session_state.get(f"start_{_d.isoformat()}", start_default))
            with c3:
                st.time_input("Koniec",   key=f"end_{_d.isoformat()}",
                              value=st.session_state.get(f"end_{_d.isoformat()}", end_default))
            with c4:
                st.number_input("Min/lekcia", 15, 120,
                                value=st.session_state.get(f"len_{_d.isoformat()}", len_default),
                                step=5, key=f"len_{_d.isoformat()}")

        st.divider()

        # Generovanie podľa denného plánu pre všetkých lektorov
        if st.button("Vygenerovať sloty podľa plánu (všetci lektori)"):
            if not teachers:
                st.warning("Najprv zadaj aspoň jedného lektora v tabuľke Lektori.")
            else:
                created = 0
                for _d in days:
                    s = st.session_state.get(f"start_{_d.isoformat()}", start_default)
                    e = st.session_state.get(f"end_{_d.isoformat()}", end_default)
                    L = int(st.session_state.get(f"len_{_d.isoformat()}", len_default))

                    if not (isinstance(s, time) and isinstance(e, time)) or s >= e:
                        st.warning(f"Deň {_d.isoformat()}: preskočené (neplatný rozsah).")
                        continue

                    for (ts, te) in time_range(s, e, L):
                        for t in teachers:
                            exists = cur.execute(
                                "SELECT 1 FROM slots WHERE day=? AND start=? AND end=? AND teacher=?",
                                (_d.isoformat(), ts.strftime('%H:%M'), te.strftime('%H:%M'), t)
                            ).fetchone()
                            if exists:
                                continue
                            cur.execute(
                                "INSERT INTO slots(day, start, end, teacher, label, is_blocked) VALUES(?,?,?,?,?,?)",
                                (_d.isoformat(), ts.strftime('%H:%M'), te.strftime('%H:%M'), t, None, 0)
                            )
                            created += 1
                conn.commit()
                st.success(f"Vytvorených nových slotov: {created}.")


    # Manuálna práca so slotmi
    slots_df = pd.read_sql_query("SELECT * FROM slots ORDER BY day, start, teacher", conn)
    st.dataframe(slots_df, use_container_width=True)

    with st.expander("Pridať špeciálny program / blokovanie"):
        sp_day   = st.date_input("Deň", value=EVENT_START, key="block_day")
        sp_from  = st.time_input("Od",  value=time(12, 0), key="block_from")
        sp_to    = st.time_input("Do",  value=time(13, 0), key="block_to")
        sp_label = st.text_input("Popis (napr. ORCHESTER, REGISTRÁCIA)")

        if st.button("Pridať blok"):
            day_iso = sp_day.isoformat()
            s = sp_from.strftime("%H:%M")
            e = sp_to.strftime("%H:%M")

            # 1) vlož samotný blok (bez učiteľa)
            cur.execute(
                "INSERT INTO slots(day, start, end, teacher, label, is_blocked) VALUES(?,?,?,?,?,1)",
                (day_iso, s, e, None, sp_label),
            )

            # 2) zmaž všetky učiteľské sloty, ktoré sa časovo prekrývajú s blokom
            cur.execute(
                """
                DELETE FROM slots
                WHERE day=? AND is_blocked=0 AND teacher IS NOT NULL
                  AND NOT (end <= ? OR start >= ?)
                """,
                (day_iso, s, e),
            )

            conn.commit()
            st.success("Blok pridaný a prekrývajúce sa učiteľské sloty zmazané.")


    # Odstrániť všetky sloty (opatrne)
    with st.expander("Hromadné mazanie slotov – OPATRNE"):
        if st.button("Vymazať všetky sloty a priradenia"):
            cur.execute("DELETE FROM assignments")
            cur.execute("DELETE FROM slots")
            conn.commit()
            st.warning("Všetky sloty a priradenia boli vymazané.")

    st.subheader("Automatické priraďovanie lekcií")
    st.caption("Automatické priraďovanie: 1 lekcia na deň a účastníka, preferencie + férová rotácia.")


    if st.button("Spustiť auto-rozvrh"):
        assigned = auto_schedule(conn)
        st.success(f"Hotovo. Nových priradení: {assigned}.")

    # Zobrazenie matice podobnej hárku "Lekcie"
    st.subheader("Matica lekcií (náhľad)")
    matrix_df = build_matrix_like_excel(conn)
    st.dataframe(matrix_df, use_container_width=True)

    if not matrix_df.empty:
        xlsx = to_excel_bytes(matrix_df)
        st.download_button(
            "Stiahnuť maticu (XLSX)",
            data=xlsx,
            file_name="Lekcie.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# -----------------------------
# Rozvrhovanie – jadro (z app.py)
# -----------------------------

def auto_schedule(conn: sqlite3.Connection) -> int:
    """
    Víkendový auto-rozvrh:
    - Piatok, sobota, nedeľa
    - Max 1 lekcia na deň pre účastníka
    - Preferovaní lektori majú prednosť a prideľujú sa účastníkom s nižším ID (skôr prihlásení)
    - Potom sa dopĺňajú zvyšné voľné sloty, opäť podľa ID
    """
    from collections import defaultdict

    cur = conn.cursor()

    slots = pd.read_sql_query(
        "SELECT id, day, start, end, teacher, is_blocked "
        "FROM slots "
        "ORDER BY day, start, COALESCE(teacher,'')",
        conn,
    )
    if slots.empty:
        return 0

    # iba piatok–nedeľa
    days = sorted([d for d in slots["day"].unique().tolist()
                   if pd.to_datetime(d).weekday() in (4, 5, 6)])
    if not days:
        return 0

    # indexy slotov: podľa dňa a učiteľa + „ploché“
    by_day_teacher = defaultdict(lambda: defaultdict(list))
    by_day_any = defaultdict(list)
    for _, r in slots.iterrows():
        if int(r["is_blocked"]) == 0 and pd.notna(r["teacher"]) and r["day"] in days:
            s = {"id": int(r["id"]), "start": r["start"], "end": r["end"], "teacher": r["teacher"]}
            by_day_teacher[r["day"]][r["teacher"]].append(s)
            by_day_any[r["day"]].append(s)

    # existujúce priradenia
    existing = pd.read_sql_query(
        """
        SELECT a.slot_id, a.registration_id, s.day
        FROM assignments a
        JOIN slots s ON s.id = a.slot_id
        """,
        conn,
    )
    taken = set(existing["slot_id"].astype(int).tolist())
    assigned_days_by_reg = defaultdict(set)
    for _, r in existing.iterrows():
        assigned_days_by_reg[int(r["registration_id"])].add(r["day"])

    # registrácie: poradie = ID ASC (skôr prihlásení majú nižšie ID)
    regs_df = pd.read_sql_query(
        "SELECT id, preferred_lectors FROM registrations ORDER BY id ASC",
        conn,
    )
    regs = regs_df.to_dict("records")

    def _take_first_free(cands):
        for s in cands:
            if s["id"] not in taken:
                return s
        return None

    new_asg = 0

    for day in days:
        # PASS 1 – len tí, čo majú preferovaných lektorov (ID ASC)
        for r in regs:
            rid = int(r["id"])
            if day in assigned_days_by_reg[rid]:
                continue
            prefs = from_json(r.get("preferred_lectors")) or []
            if not prefs:
                continue

            chosen = None
            for p in prefs:
                chosen = _take_first_free(by_day_teacher[day].get(p, []))
                if chosen:
                    break

            if chosen:
                cur.execute("INSERT INTO assignments(slot_id, registration_id) VALUES(?, ?)",
                            (chosen["id"], rid))
                taken.add(chosen["id"])
                assigned_days_by_reg[rid].add(day)
                by_day_any[day] = [s for s in by_day_any[day] if s["id"] != chosen["id"]]
                new_asg += 1

        # PASS 2 – všetci ostatní (ID ASC), vyplniť zvyšné voľné sloty hociktorým učiteľom
        for r in regs:
            rid = int(r["id"])
            if day in assigned_days_by_reg[rid]:
                continue

            chosen = _take_first_free(by_day_any[day])
            if chosen:
                cur.execute("INSERT INTO assignments(slot_id, registration_id) VALUES(?, ?)",
                            (chosen["id"], rid))
                taken.add(chosen["id"])
                assigned_days_by_reg[rid].add(day)
                by_day_any[day] = [s for s in by_day_any[day] if s["id"] != chosen["id"]]
                new_asg += 1

    conn.commit()
    return new_asg



def build_matrix_like_excel(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Jeden riadok = jeden časový slot (day, start–end).
    V bunkách pod menami učiteľov je vždy max. jedno meno (ak existuje priradenie).
    Pre bloky (is_blocked=1) sa vyplní stĺpec 'SPECIAL PROGRAM'.
    """
    # poradie lektorov = poradie stĺpcov
    lectors = pd.read_sql_query(
        "SELECT name FROM lectors ORDER BY name", conn
    )["name"].tolist()

    # sloty aj s učiteľom (alebo NULL pri bloku)
    slots_df = pd.read_sql_query(
        "SELECT id, day, start, end, teacher, is_blocked, label "
        "FROM slots ORDER BY day, start, end, COALESCE(teacher,'')",
        conn,
    )
    if slots_df.empty:
        return pd.DataFrame(columns=["day", "time", "PARTICIPANTS"] + lectors + ["SPECIAL PROGRAM"])

    # priradenia k slotom (očakávame max 1, ale keby ich bolo viac, spojíme ' / ')
    asg_df = pd.read_sql_query(
        """
        SELECT a.slot_id, r.name AS student_name, r.people_count, r.ensemble_type
        FROM assignments a
        JOIN registrations r ON r.id = a.registration_id
        """,
        conn,
    )
    asg_by_slot = {}
    for _, rr in asg_df.iterrows():
        nm = rr["student_name"]
        if int(rr.get("people_count") or 1) > 1 and rr.get("ensemble_type"):
            nm += f" ({rr['ensemble_type']})"
        asg_by_slot.setdefault(int(rr["slot_id"]), []).append(nm)

    rows = []
    # zoskup podľa (day, start, end) => jeden riadok na čas
    for (day, start, end), grp in slots_df.groupby(["day", "start", "end"], sort=False):
        row = {"day": day, "time": f"{start} - {end}", "PARTICIPANTS": None}
        for lec in lectors:
            row[lec] = None
        row["SPECIAL PROGRAM"] = None

        names_in_row = []
        for _, s in grp.iterrows():
            if int(s["is_blocked"]) == 1:
                row["SPECIAL PROGRAM"] = s["label"] or "Blokované"
                continue
            teacher = s["teacher"]
            cell_names = " / ".join(asg_by_slot.get(int(s["id"]), [])) or None
            if teacher in row:
                row[teacher] = cell_names
            if cell_names:
                names_in_row.extend(asg_by_slot.get(int(s["id"]), []))

        row["PARTICIPANTS"] = " / ".join(names_in_row) if names_in_row else None
        rows.append(row)

    columns = ["day", "time"] + lectors + ["SPECIAL PROGRAM"]
    return pd.DataFrame(rows, columns=columns)

# -----------------------------
# UI – navigácia
# -----------------------------

hide_streamlit_menu()


def main():
    st.set_page_config(page_title="Saxophobia – registrácia", layout="wide")
    init_db()

    # Aktuálny jazyk zo session (default SK)
    current_lang = st.session_state.get("lang", "SK")
    txt = TEXTS.get(current_lang, TEXTS["SK"])

    # -----------------------------
    # TOP BAR (logo + jazyk + menu)
    # -----------------------------
        # -----------------------------
    # TOP BAR (logo + jazyk + dashboard)
    # -----------------------------
    conn = get_conn()
    stats = get_public_dashboard_stats(conn)

    col_logo, col_mid, col_lang = st.columns([1.2, 3.2, 1.2])

    with col_logo:
        st.image("Logo.jpg", width='stretch')

    with col_mid:
        st.markdown("## Saxophobia")

        # Mini dashboard (pekne v jednom riadku)
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Prihlásení / Participants", stats["participants_sum"])
        with m2:
            st.metric("Voľné miesta / Free places", stats["remaining"])
        #with m3:
            #st.metric("Registrácie (záznamy)", stats["registrations_count"])

        # Obsadenosť (progress)
        filled = min(stats["participants_sum"], MAX_CAPACITY)
        ratio = filled / MAX_CAPACITY if MAX_CAPACITY else 0
        st.progress(ratio)
        st.caption(f"Kapacita/Capacity: {filled}/{MAX_CAPACITY}")

        # Top nástroje (krátky prehľad)
        if stats["top_instruments"]:
            top_txt = " • ".join([f"{k}: {v}" for k, v in stats["top_instruments"]])
            st.caption(f"Prehľad počtu nástrojov/Instruments overview: {top_txt}")
        else:
            st.caption("Zatiaľ nie sú žiadne prihlášky.")

    with col_lang:
        st.markdown(f"**{txt['lang_label']}**")
        lang = st.radio(
            "Language",
            ["SK", "EN"],
            horizontal=True,
            key="lang",
            index=0 if current_lang == "SK" else 1,
            label_visibility="collapsed",
        )



    # Po zmene jazyka refresh
    txt = TEXTS.get(lang, TEXTS["SK"])

    # Dynamické menu podľa prihlásenia
    menu_items = [txt["nav_application"], txt["nav_feedback"]]

    # organizer vidí Organizátor
    if st.session_state.get("auth_organizer_ok"):
        if txt["nav_organizer"] not in menu_items:
            menu_items.insert(1, txt["nav_organizer"])

    # admin vidí Admin (a aj Organizátor)
    if st.session_state.get("auth_admin_ok"):
        if txt["nav_organizer"] not in menu_items:
            menu_items.insert(1, txt["nav_organizer"])
        if txt["nav_admin"] not in menu_items:
            menu_items.insert(2, txt["nav_admin"])

    page = st.radio(
        txt["nav_label"],
        menu_items,
        horizontal=True,
        key="top_nav",
    )

    st.divider()

    # -----------------------------
    # Prihlásenie / Odhlásenie (hore)
    # -----------------------------
    with st.expander("Prihlásenie (organizátor/admin)"):
        c1, c2 = st.columns(2)

        # Organizer
        with c1:
            if not st.session_state.get("auth_organizer_ok"):
                org_pwd = st.text_input("Heslo organizátor", type="password", key="top_pwd_organizer")
                if st.button("Prihlásiť ako organizátor", key="top_login_organizer"):
                    organizer_pw = get_secret("auth.organizer_password", "organizator123")
                    if org_pwd == organizer_pw:
                        st.session_state["auth_organizer_ok"] = True
                        st.success("OK – organizátor prihlásený.")
                        st.rerun()
                    else:
                        st.error("Nesprávne heslo organizátora.")
            else:
                st.success("Organizátor prihlásený ✅")

        # Admin
        with c2:
            if not st.session_state.get("auth_admin_ok"):
                adm_pwd = st.text_input("Heslo admin", type="password", key="top_pwd_admin")
                if st.button("Prihlásiť ako admin", key="top_login_admin"):
                    admin_pw = get_secret("auth.admin_password", "admin123")
                    if adm_pwd == admin_pw:
                        st.session_state["auth_admin_ok"] = True
                        st.success("OK – admin prihlásený.")
                        st.rerun()
                    else:
                        st.error("Nesprávne heslo admina.")
            else:
                st.success("Admin prihlásený ✅")

        if st.button("Odhlásiť (admin/organizátor)", key="top_logout"):
            for k in ["auth_organizer_ok", "auth_admin_ok"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    st.divider()

    # -----------------------------
    # Router na stránky
    # -----------------------------
    if page == txt["nav_application"]:
        page_application()
    elif page == txt["nav_organizer"]:
        page_organizer()
    elif page == txt["nav_admin"]:
        page_admin()
    elif page == txt["nav_feedback"]:
        page_feedback()


if __name__ == "__main__":
    main()

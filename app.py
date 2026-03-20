import streamlit as st
import redis
import json
import uuid
import datetime
import hashlib
import time
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional, Tuple, Dict, Any
import os
import urllib.request

from act.game import game_page
from act.rules import display as display_rules

# ==========================================
# GLOBAL CONFIGURATION
# ==========================================
MAX_PLAYERS: int = 5
PREFIX: str = "game_session:"
TTL: int = 86400

st.set_page_config(page_title="act!", page_icon="🎭", layout="wide")


# ==========================================
# AUTO-DOWNLOAD FONTS FOR PILLOW
# ==========================================
def ensure_assets_exist():
    if not os.path.exists("assets"):
        os.makedirs("assets")

    fonts = {
        "Kalam-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/kalam/Kalam-Regular.ttf",
        "PermanentMarker-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/apache/permanentmarker/PermanentMarker-Regular.ttf",
    }

    for font_name, url in fonts.items():
        font_path = os.path.join("assets", font_name)
        if not os.path.exists(font_path):
            try:
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Fehler beim Laden von {font_name}: {e}")


# ==========================================
# SECURITY & DB
# ==========================================
@st.cache_resource
def get_rate_limiter() -> dict:
    return {}


def check_rate_limit(user_id: str) -> bool:
    limiter = get_rate_limiter()
    now = time.time()
    history = [t for t in limiter.get(user_id, []) if now - t < 60]
    if len(history) >= 3:
        limiter[user_id] = history
        return False
    history.append(now)
    limiter[user_id] = history
    return True


def init_language() -> None:
    if "language" not in st.session_state:
        st.session_state.language = "en"
    col_spacer, col_lang = st.columns([10, 1])
    with col_lang:
        new_lang = st.selectbox(
            "🌐",
            ["en", "de"],
            index=0 if st.session_state.language == "en" else 1,
            label_visibility="collapsed",
        )
        if new_lang != st.session_state.language:
            st.session_state.language = new_lang
            st.rerun()
    try:
        with open("locales/act.json", "r", encoding="utf-8") as f:
            all_strings = json.load(f)
            st.session_state.text = all_strings[st.session_state.language]
        with open("locales/rules.json", "r", encoding="utf-8") as f:
            rules_strings = json.load(f)
            st.session_state.text.update(rules_strings[st.session_state.language])
    except FileNotFoundError:
        st.error("Error: locales files not found!")
        st.stop()


def inject_creative_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Permanent+Marker&family=Kalam:wght@400;700&display=swap');
        
        @media (min-width: 768px) {
            [data-testid="stAppViewContainer"] { transform: scale(0.8); transform-origin: top left; width: 125%; height: 125%; }
        }

        html, body, [data-testid="stAppViewContainer"], .st-emotion-cache-1vt458e p, label { font-family: 'Kalam', cursive; font-size: 1.1rem; }
        h1, h2, h3, h4, h5, h6, .stButton button { font-family: 'Permanent Marker', cursive; letter-spacing: 0.05rem; }
        [data-testid="stHeader"] h1 { color: #E74C3C; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); font-size: 4rem; margin-bottom: 0; padding-bottom: 0; }
        .actor-slogan { font-family: 'Permanent Marker', cursive; color: #F39C12; font-size: 1.8rem; margin-top: -1.5rem; margin-bottom: 2rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); }
        .subtitle-line { font-family: 'Kalam', cursive; font-size: 1.4rem; font-weight: 700; margin-bottom: 0.2rem; }
        .create-header { background-color: #E74C3C; padding: 1rem; border-radius: 15px; color: #FFFFFF; font-family: 'Permanent Marker', cursive; text-align: center; font-size: 2rem; margin-bottom: 1rem; }
        .join-header { background-color: #2ECC71; padding: 1rem; border-radius: 15px; color: #FFFFFF; font-family: 'Permanent Marker', cursive; text-align: center; font-size: 2rem; margin-bottom: 1rem; }
        div[data-testid="stColumn"]:nth-child(1) button, div[data-testid="column"]:nth-child(1) button { background-color: #E74C3C !important; color: #FFFFFF !important; border: 1px solid #E74C3C !important; }
        div[data-testid="stColumn"]:nth-child(2) button, div[data-testid="column"]:nth-child(2) button { background-color: #2ECC71 !important; color: #FFFFFF !important; border: 1px solid #2ECC71 !important; }
        [data-testid="stForm"] input { border-radius: 8px !important; }
        .legal-footer { text-align: center; margin-top: 4rem; padding-top: 1rem; font-family: 'Kalam', cursive; font-size: 0.9rem; }
        .legal-footer a { color: #7F8C8D; text-decoration: none; margin: 0 10px; transition: color 0.3s; }
        .legal-footer a:hover { color: #F39C12; }
        </style>
    """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def get_redis_client() -> redis.Redis:
    try:
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            try:
                if "REDIS_URL" in st.secrets:
                    redis_url = st.secrets["REDIS_URL"]
            except Exception:
                pass
        if not redis_url:
            st.error("REDIS_URL is not set.")
            st.stop()
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        st.error(f"DB error: {e}")
        st.stop()


def generate_session_hash() -> str:
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8].upper()


class GameSessionManager:
    @classmethod
    def save_user_state(
        cls, user_id: str, session_id: str, player_name: str, is_creator: bool
    ) -> None:
        get_redis_client().setex(
            f"user_state:{user_id}",
            TTL,
            json.dumps(
                {
                    "session_id": session_id,
                    "player_name": player_name,
                    "is_creator": is_creator,
                }
            ),
        )

    @classmethod
    def get_user_state(cls, user_id: str) -> Optional[dict]:
        data = get_redis_client().get(f"user_state:{user_id}")
        return json.loads(data) if data else None

    @classmethod
    def clear_user_state(cls, user_id: str) -> None:
        get_redis_client().delete(f"user_state:{user_id}")

    @classmethod
    def create_session(cls, creator_name: str, password: str) -> str:
        session_hash = generate_session_hash()
        get_redis_client().setex(
            f"{PREFIX}{session_hash}",
            TTL,
            json.dumps(
                {
                    "password_hash": generate_password_hash(password),
                    "creator": creator_name,
                    "status": "pairing",
                    "players": [creator_name],
                }
            ),
        )
        return session_hash

    @classmethod
    def get_session(cls, session_hash: str) -> Optional[Dict[str, Any]]:
        data = get_redis_client().get(f"{PREFIX}{session_hash}")
        return json.loads(data) if data else None

    @classmethod
    def update_session_data(cls, session_hash: str, new_data: dict) -> None:
        get_redis_client().set(
            f"{PREFIX}{session_hash}", json.dumps(new_data), keepttl=True
        )

    @classmethod
    def join_session(
        cls, session_hash: str, player_name: str, password: str
    ) -> Tuple[bool, str]:
        session = cls.get_session(session_hash)
        if not session:
            return False, "Session not found."
        if session.get("redirect"):
            return False, "Session ID changed."
        if session.get("status") != "pairing":
            return False, "Game started."
        if len(session.get("players", [])) >= MAX_PLAYERS:
            return False, "Lobby full."
        if not check_password_hash(session["password_hash"], password):
            return False, "Invalid password."
        if player_name in session.get("players", []):
            return False, "Name taken."
        session["players"].append(player_name)
        get_redis_client().set(
            f"{PREFIX}{session_hash}", json.dumps(session), keepttl=True
        )
        return True, "Joined successfully."

    @classmethod
    def start_game(cls, session_hash: str) -> None:
        session = cls.get_session(session_hash)
        if session:
            session["status"] = "running"
            get_redis_client().set(
                f"{PREFIX}{session_hash}", json.dumps(session), keepttl=True
            )

    @classmethod
    def stop_session(cls, session_hash: str) -> None:
        get_redis_client().delete(f"{PREFIX}{session_hash}")

    @classmethod
    def regenerate_session_id(cls, old_session_hash: str) -> Optional[str]:
        session = cls.get_session(old_session_hash)
        if not session:
            return None
        new_hash = generate_session_hash()
        get_redis_client().setex(f"{PREFIX}{new_hash}", TTL, json.dumps(session))
        get_redis_client().setex(
            f"{PREFIX}{old_session_hash}", 30, json.dumps({"redirect": new_hash})
        )
        return new_hash


def render_footer() -> None:
    text = st.session_state.text
    st.markdown(
        f"""
        <div class="legal-footer">
            <a href="https://versteckmich.de/sokrates" target="_blank">{text.get("imprint", "Impressum")}</a> | 
            <a href="https://versteckmich.de/sokrates" target="_blank">{text.get("privacy_policy", "Datenschutz")}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def landing_page() -> None:
    text = st.session_state.text
    user_id = st.session_state.user_id
    st.title(text["app_title"])
    st.markdown(
        f'<div class="actor-slogan">{text["slogan"]}</div>', unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="subtitle-line">{text["subtitle_line1"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="subtitle-line"><span style="color: #E74C3C;">{text["subtitle_line2_part1"]}</span>{text["subtitle_line2_or"]}<span style="color: #2ECC71;">{text["subtitle_line2_part2"]}</span></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div class="create-header">{text["create_title"]}</div>',
            unsafe_allow_html=True,
        )
        with st.form("create_form"):
            creator_name = st.text_input(text["stage_name"], max_chars=20)
            create_pw = st.text_input(text["stage_pw"], type="password")
            if (
                st.form_submit_button(text["btn_create"], use_container_width=True)
                and creator_name
                and create_pw
            ):
                if not check_rate_limit(user_id):
                    st.error("Too many sessions created.")
                else:
                    session_hash = GameSessionManager.create_session(
                        creator_name, create_pw
                    )
                    GameSessionManager.save_user_state(
                        user_id, session_hash, creator_name, True
                    )
                    (
                        st.session_state.session_id,
                        st.session_state.player_name,
                        st.session_state.is_creator,
                        st.session_state.current_page,
                    ) = (session_hash, creator_name, True, "lobby")
                    st.rerun()
    with col2:
        st.markdown(
            f'<div class="join-header">{text["join_title"]}</div>',
            unsafe_allow_html=True,
        )
        with st.form("join_form"):
            join_id = st.text_input(text["join_id"], max_chars=8).upper()
            join_name = st.text_input(text["stage_name"], max_chars=20)
            join_pw = st.text_input(text["stage_pw"], type="password")
            if (
                st.form_submit_button(text["btn_join"], use_container_width=True)
                and join_id
                and join_name
                and join_pw
            ):
                success, msg = GameSessionManager.join_session(
                    join_id, join_name, join_pw
                )
                if success:
                    GameSessionManager.save_user_state(
                        user_id, join_id, join_name, False
                    )
                    (
                        st.session_state.session_id,
                        st.session_state.player_name,
                        st.session_state.is_creator,
                        st.session_state.current_page,
                    ) = (join_id, join_name, False, "lobby")
                    st.rerun()
                else:
                    st.error(msg)

    st.write("")
    st.write("")
    display_rules(text)


@st.fragment(run_every="5s")
def render_lobby() -> None:
    text = st.session_state.text
    session_data = GameSessionManager.get_session(st.session_state.session_id)
    if not session_data:
        st.error(text.get("waiting_host", "Session not found."))
        if st.button("Back to Hub"):
            GameSessionManager.clear_user_state(st.session_state.user_id)
            st.session_state.current_page = "landing"
            st.rerun()
        return
    if session_data.get("redirect"):
        st.session_state.session_id = session_data["redirect"]
        GameSessionManager.save_user_state(
            st.session_state.user_id,
            session_data["redirect"],
            st.session_state.player_name,
            st.session_state.is_creator,
        )
        st.rerun()
    if session_data.get("status") == "running":
        st.session_state.current_page = "game"
        st.rerun()
    st.write(f"### Dressing Room: ID")
    st.code(st.session_state.session_id, language=None)
    st.divider()
    players = session_data.get('players', [])
    st.write(f"**Cast Members ({len(players)}/{MAX_PLAYERS}):**")
    for p in players:
        st.write(f"- {p}{' 👑 *(Host)*' if p == session_data.get('creator') else ''}")
    st.write("")
    if st.session_state.is_creator:
        col_start, col_regen, col_stop = st.columns(3)
        with col_start:
            if st.button(
                text["btn_start_scene"], type="primary", use_container_width=True
            ):
                GameSessionManager.start_game(st.session_state.session_id)
                st.session_state.current_page = "game"
                st.rerun()
        with col_regen:
            if st.button(text["btn_regen_id"], use_container_width=True):
                new_id = GameSessionManager.regenerate_session_id(
                    st.session_state.session_id
                )
                if new_id:
                    st.session_state.session_id = new_id
                    st.rerun()
        with col_stop:
            if st.button(
                text["btn_end_scene"], type="secondary", use_container_width=True
            ):
                GameSessionManager.stop_session(st.session_state.session_id)
                GameSessionManager.clear_user_state(st.session_state.user_id)
                st.session_state.current_page = "landing"
                st.rerun()
    else:
        st.info(f"🔄 {text['waiting_host']}")


def main() -> None:
    ensure_assets_exist()
    init_language()
    inject_creative_styles()

    # ========================================================
    # DIE NEUE MAGIC: Wir lesen die ID direkt aus der URL aus!
    # (Keine Cookie-Banner, kein stx.CookieManager mehr)
    # ========================================================
    user_id = st.query_params.get("uid")

    # Fallback, falls jemand den HF-Space direkt ohne Netlify aufruft
    if not user_id:
        if "fallback_uid" not in st.session_state:
            st.session_state.fallback_uid = str(uuid.uuid4())
        user_id = st.session_state.fallback_uid

    st.session_state.user_id = user_id
    # ========================================================

    if "current_page" not in st.session_state:
        restored_state = GameSessionManager.get_user_state(user_id)
        if restored_state:
            session_data = GameSessionManager.get_session(restored_state["session_id"])
            if session_data:
                if session_data.get("redirect"):
                    st.session_state.session_id = session_data["redirect"]
                    GameSessionManager.save_user_state(
                        user_id,
                        session_data["redirect"],
                        restored_state["player_name"],
                        restored_state["is_creator"],
                    )
                    session_data = GameSessionManager.get_session(
                        session_data["redirect"]
                    )
                else:
                    st.session_state.session_id = restored_state["session_id"]
                st.session_state.player_name = restored_state["player_name"]
                st.session_state.is_creator = restored_state["is_creator"]
                st.session_state.current_page = (
                    "game"
                    if session_data and session_data.get("status") == "running"
                    else "lobby"
                )
            else:
                GameSessionManager.clear_user_state(user_id)
                st.session_state.current_page = "landing"
        else:
            st.session_state.current_page = "landing"

    if st.session_state.current_page == "landing":
        landing_page()
    elif st.session_state.current_page == "lobby":
        render_lobby()
    elif st.session_state.current_page == "game":
        game_page(GameSessionManager)

    render_footer()


if __name__ == "__main__":
    main()

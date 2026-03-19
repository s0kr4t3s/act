import streamlit as st
import redis
import json
import uuid
import datetime
import hashlib
import time
import extra_streamlit_components as stx
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional, Tuple, Dict, Any
import os

# IMPORTIERE DIE GAME LOGIK
from act.game import game_page

# ==========================================
# GLOBAL CONFIGURATION
# ==========================================
MAX_PLAYERS: int = 12
PREFIX: str = "game_session:"
TTL: int = 86400  # 24 hours

st.set_page_config(page_title="act!", page_icon="🎭", layout="wide")


# ==========================================
# LANGUAGE SETUP & i18n
# ==========================================
def init_language() -> None:
    if "language" not in st.session_state:
        st.session_state.language = "en"

    # Sprachwähler oben rechts
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

    # Lade die Strings
    try:
        with open("locales/act.json", "r", encoding="utf-8") as f:
            all_strings = json.load(f)
            st.session_state.text = all_strings[st.session_state.language]
    except FileNotFoundError:
        st.error("Error: act.json not found! Please create the language file.")
        st.stop()


# ==========================================
# CREATIVE STYLING INJECTION (CSS)
# ==========================================
def inject_creative_styles() -> None:
    st.markdown(
        """
        <style>
        /* Load Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Permanent+Marker&family=Kalam:wght@400;700&display=swap');

        /* Main app font for body and form labels */
        html, body, [data-testid="stAppViewContainer"], .st-emotion-cache-1vt458e p, label {
            font-family: 'Kalam', cursive;
            font-size: 1.1rem;
        }

        /* Headings and buttons */
        h1, h2, h3, h4, h5, h6, .stButton button {
            font-family: 'Permanent Marker', cursive;
            letter-spacing: 0.05rem;
        }
        
        /* Specific styling for st.title ("act!") */
        [data-testid="stHeader"] h1 {
            color: #E74C3C;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            font-size: 4rem;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        
        /* Slogan directly under the title */
        .actor-slogan {
            font-family: 'Permanent Marker', cursive;
            color: #F39C12;
            font-size: 1.8rem;
            margin-top: -1.5rem;
            margin-bottom: 2rem;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }

        /* Subtitle Typography */
        .subtitle-line {
            font-family: 'Kalam', cursive;
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        
        /* Styled Header Banners for the Columns */
        .create-header {
            background-color: #E74C3C; /* Ruby Red */
            padding: 1rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3);
            color: #FFFFFF;
            font-family: 'Permanent Marker', cursive;
            text-align: center;
            font-size: 2rem;
            margin-bottom: 1rem;
        }

        .join-header {
            background-color: #2ECC71; /* Emerald Green */
            padding: 1rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(46, 204, 113, 0.3);
            color: #FFFFFF;
            font-family: 'Permanent Marker', cursive;
            text-align: center;
            font-size: 2rem;
            margin-bottom: 1rem;
        }

        /* --- BUTTON COLOR HACKS --- */
        /* Target buttons in the FIRST column (Create) */
        div[data-testid="stColumn"]:nth-child(1) button,
        div[data-testid="column"]:nth-child(1) button {
            background-color: #E74C3C !important;
            color: #FFFFFF !important;
            border: 1px solid #E74C3C !important;
            box-shadow: 0 4px 10px rgba(231, 76, 60, 0.2) !important;
        }
        div[data-testid="stColumn"]:nth-child(1) button:hover,
        div[data-testid="column"]:nth-child(1) button:hover {
            background-color: #C0392B !important;
            border: 1px solid #C0392B !important;
        }

        /* Target buttons in the SECOND column (Join) */
        div[data-testid="stColumn"]:nth-child(2) button,
        div[data-testid="column"]:nth-child(2) button {
            background-color: #2ECC71 !important;
            color: #FFFFFF !important;
            border: 1px solid #2ECC71 !important;
            box-shadow: 0 4px 10px rgba(46, 204, 113, 0.2) !important;
        }
        div[data-testid="stColumn"]:nth-child(2) button:hover,
        div[data-testid="column"]:nth-child(2) button:hover {
            background-color: #27AE60 !important;
            border: 1px solid #27AE60 !important;
        }

        /* Subtle glow for the vertical dashed line */
        div[data-testid="stVerticalBlock"] div:nth-child(2) hr {
            border-color: #f0f2f6 !important;
            box-shadow: 0 0 10px rgba(240, 242, 246, 0.5);
        }
        
        /* Make standard Streamlit input elements look a bit cleaner */
        [data-testid="stForm"] input {
            border-radius: 8px !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


# ==========================================
# DATABASE CONNECTION
# ==========================================
@st.cache_resource
def get_redis_client() -> redis.Redis:
    try:
        # Check OS environment variables first (for Hugging Face Docker),
        # fallback to st.secrets (for local testing with .streamlit/secrets.toml)
        redis_url = os.environ.get("REDIS_URL") or st.secrets.get("REDIS_URL")

        if not redis_url:
            st.error("REDIS_URL is not set in the environment or secrets.")
            st.stop()

        client: redis.Redis = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        st.error(f"DB connection failed. Error: {e}")
        st.stop()


# ==========================================
# CORE LOGIC
# ==========================================
def generate_session_hash() -> str:
    internal_id: str = str(uuid.uuid4())
    return hashlib.md5(internal_id.encode()).hexdigest()[:8].upper()


class GameSessionManager:
    @classmethod
    def create_session(cls, creator_name: str, password: str) -> str:
        redis_client: redis.Redis = get_redis_client()
        session_hash: str = generate_session_hash()
        hashed_pw: str = generate_password_hash(password)

        session_data: Dict[str, Any] = {
            "password_hash": hashed_pw,
            "creator": creator_name,
            "status": "pairing",
            "players": [creator_name],
        }

        db_key: str = f"{PREFIX}{session_hash}"
        redis_client.setex(db_key, TTL, json.dumps(session_data))
        return session_hash

    @classmethod
    def get_session(cls, session_hash: str) -> Optional[Dict[str, Any]]:
        redis_client: redis.Redis = get_redis_client()
        db_key: str = f"{PREFIX}{session_hash}"
        data_str: Optional[str] = redis_client.get(db_key)

        if data_str:
            return json.loads(data_str)
        return None

    @classmethod
    def update_session_data(cls, session_hash: str, new_data: dict) -> None:
        redis_client: redis.Redis = get_redis_client()
        db_key: str = f"{PREFIX}{session_hash}"
        redis_client.set(db_key, json.dumps(new_data), keepttl=True)

    @classmethod
    def join_session(
        cls, session_hash: str, player_name: str, password: str
    ) -> Tuple[bool, str]:
        redis_client: redis.Redis = get_redis_client()
        db_key: str = f"{PREFIX}{session_hash}"

        session: Optional[Dict[str, Any]] = cls.get_session(session_hash)
        if not session:
            return False, "Session not found."
        if session.get("redirect"):
            return False, "Session ID changed. Ask host for new ID."
        if session.get("status") != "pairing":
            return False, "Game already started."
        if len(session.get("players", [])) >= MAX_PLAYERS:
            return False, f"Lobby full (Max {MAX_PLAYERS})."
        if not check_password_hash(session["password_hash"], password):
            return False, "Invalid password."
        if player_name in session.get("players", []):
            return False, "Name already taken."

        session["players"].append(player_name)
        redis_client.set(db_key, json.dumps(session), keepttl=True)
        return True, "Joined successfully."

    @classmethod
    def start_game(cls, session_hash: str) -> None:
        redis_client: redis.Redis = get_redis_client()
        db_key: str = f"{PREFIX}{session_hash}"
        session: Optional[Dict[str, Any]] = cls.get_session(session_hash)
        if session:
            session["status"] = "running"
            redis_client.set(db_key, json.dumps(session), keepttl=True)

    @classmethod
    def stop_session(cls, session_hash: str) -> None:
        redis_client: redis.Redis = get_redis_client()
        db_key: str = f"{PREFIX}{session_hash}"
        redis_client.delete(db_key)

    @classmethod
    def regenerate_session_id(cls, old_session_hash: str) -> Optional[str]:
        redis_client: redis.Redis = get_redis_client()
        old_db_key: str = f"{PREFIX}{old_session_hash}"

        session: Optional[Dict[str, Any]] = cls.get_session(old_session_hash)
        if not session:
            return None

        new_session_hash: str = generate_session_hash()
        new_db_key: str = f"{PREFIX}{new_session_hash}"

        redis_client.setex(new_db_key, TTL, json.dumps(session))

        redirect_payload: Dict[str, str] = {"redirect": new_session_hash}
        redis_client.setex(old_db_key, 30, json.dumps(redirect_payload))

        return new_session_hash


# ==========================================
# FRONTEND COMPONENTS
# ==========================================
def check_cookies() -> None:
    if st.session_state.get("cookies_accepted", False):
        return

    cookie_manager: stx.CookieManager = stx.CookieManager(key="global_cookie_manager")
    consent: Optional[str] = cookie_manager.get(cookie="cookie_consent")

    if consent == "true":
        st.session_state.cookies_accepted = True
        return

    with st.container():
        st.info("🍪 Cookies are required for session stability.")
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Accept", type="primary"):
                expires: datetime.datetime = (
                    datetime.datetime.now() + datetime.timedelta(days=30)
                )
                cookie_manager.set(
                    "cookie_consent",
                    "true",
                    expires_at=expires,
                    key="set_cookie_consent",
                )
                cookie_manager.set(
                    "user_id",
                    str(uuid.uuid4()),
                    expires_at=expires,
                    key="set_cookie_uid",
                )
                st.session_state.cookies_accepted = True
                time.sleep(0.2)
                st.rerun()
        with col2:
            if st.button("Decline"):
                st.error("Cookies are mandatory. Reload the page to accept.")
                st.stop()
    st.stop()


def landing_page() -> None:
    text = st.session_state.text

    st.title(text["app_title"])

    st.markdown(
        f'<div class="actor-slogan">{text["slogan"]}</div>', unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="subtitle-line">{text["subtitle_line1"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'''
        <div class="subtitle-line">
            <span style="color: #E74C3C;">{text["subtitle_line2_part1"]}</span>{text["subtitle_line2_or"]}<span style="color: #2ECC71;">{text["subtitle_line2_part2"]}</span>
        </div>
    ''',
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
            creator_name: str = st.text_input(text["stage_name"], max_chars=20)
            create_pw: str = st.text_input(text["stage_pw"], type="password")
            submitted_create: bool = st.form_submit_button(
                text["btn_create"], use_container_width=True
            )

            if submitted_create and creator_name and create_pw:
                session_hash: str = GameSessionManager.create_session(
                    creator_name, create_pw
                )
                st.session_state.session_id = session_hash
                st.session_state.player_name = creator_name
                st.session_state.is_creator = True
                st.session_state.current_page = "lobby"
                st.rerun()

    with col2:
        st.markdown(
            f'<div class="join-header">{text["join_title"]}</div>',
            unsafe_allow_html=True,
        )
        with st.form("join_form"):
            join_id: str = st.text_input(text["join_id"], max_chars=8).upper()
            join_name: str = st.text_input(text["stage_name"], max_chars=20)
            join_pw: str = st.text_input(text["stage_pw"], type="password")
            submitted_join: bool = st.form_submit_button(
                text["btn_join"], use_container_width=True
            )

            if submitted_join and join_id and join_name and join_pw:
                success, msg = GameSessionManager.join_session(
                    join_id, join_name, join_pw
                )
                if success:
                    st.session_state.session_id = join_id
                    st.session_state.player_name = join_name
                    st.session_state.is_creator = False
                    st.session_state.current_page = "lobby"
                    st.rerun()
                else:
                    st.error(msg)


@st.fragment(run_every="2s")
def render_lobby() -> None:
    text = st.session_state.text
    session_id: str = st.session_state.session_id
    is_creator: bool = st.session_state.is_creator
    session_data: Optional[Dict[str, Any]] = GameSessionManager.get_session(session_id)

    if not session_data:
        st.error(text.get("waiting_host", "Session not found."))
        if st.button("Back to Hub"):
            st.session_state.current_page = "landing"
            st.rerun()
        return

    if session_data.get("redirect"):
        st.session_state.session_id = session_data["redirect"]
        st.rerun()

    if session_data.get("status") == "running":
        st.session_state.current_page = "game"
        st.rerun()

    st.write(f"### Dressing Room: ID `{session_id}`")
    st.divider()

    players: list = session_data.get('players', [])
    st.write(f"**Cast Members ({len(players)}/{MAX_PLAYERS}):**")
    for p in players:
        is_host: str = " 👑 *(Host)*" if p == session_data.get('creator') else ""
        st.write(f"- {p}{is_host}")

    st.write("")

    if is_creator:
        col_start, col_regen, col_stop = st.columns(3)

        with col_start:
            if st.button(
                text["btn_start_scene"], type="primary", use_container_width=True
            ):
                GameSessionManager.start_game(session_id)
                st.session_state.current_page = "game"
                st.rerun()

        with col_regen:
            if st.button(text["btn_regen_id"], use_container_width=True):
                new_id: Optional[str] = GameSessionManager.regenerate_session_id(
                    session_id
                )
                if new_id:
                    st.session_state.session_id = new_id
                    st.rerun()

        with col_stop:
            if st.button(
                text["btn_end_scene"], type="secondary", use_container_width=True
            ):
                GameSessionManager.stop_session(session_id)
                st.session_state.current_page = "landing"
                st.rerun()
    else:
        st.info(f"🔄 {text['waiting_host']}")


# ==========================================
# MAIN APP ROUTING
# ==========================================
def main() -> None:
    init_language()
    inject_creative_styles()
    check_cookies()

    if "current_page" not in st.session_state:
        st.session_state.current_page = "landing"

    if st.session_state.current_page == "landing":
        landing_page()
    elif st.session_state.current_page == "lobby":
        render_lobby()
    elif st.session_state.current_page == "game":
        game_page(GameSessionManager)


if __name__ == "__main__":
    main()

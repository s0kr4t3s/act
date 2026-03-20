import streamlit as st
import streamlit.components.v1 as components  # HINZUGEFÜGT für den JS-Cookie-Injector
import redis
import json
import uuid
import datetime
import hashlib
import time
import hmac
import extra_streamlit_components as stx
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional, Tuple, Dict, Any
import os

# IMPORTIERE DIE GAME LOGIK
from act.game import game_page

# ==========================================
# GLOBAL CONFIGURATION
# ==========================================
MAX_PLAYERS: int = 5
PREFIX: str = "game_session:"
TTL: int = 86400  # 24 hours

st.set_page_config(page_title="act!", page_icon="🎭", layout="wide")


# ==========================================
# COOKIE SECURITY WORKAROUND
# ==========================================
def set_secure_cookie(name: str, value: str, days: int = 30):
    """Setzt einen Cookie mit SameSite=None und Secure. ZWINGEND für Streamlit Cloud iFrames!"""
    js = f"""
    <script>
        var d = new Date();
        d.setTime(d.getTime() + ({days}*24*60*60*1000));
        var expires = "expires="+ d.toUTCString();
        document.cookie = "{name}={value};" + expires + ";path=/;SameSite=None;Secure";
    </script>
    """
    components.html(js, height=0, width=0)


# ==========================================
# SECURITY & RATE LIMITING
# ==========================================
def get_cookie_secret() -> bytes:
    secret = os.environ.get("COOKIE_SECRET") or st.secrets.get(
        "COOKIE_SECRET", "super-secret-dev-key"
    )
    return secret.encode('utf-8')


def sign_cookie(user_id: str) -> str:
    signature = hmac.new(
        get_cookie_secret(), user_id.encode('utf-8'), hashlib.sha256
    ).hexdigest()
    return f"{user_id}|{signature}"


def verify_cookie(cookie_val: str) -> bool:
    try:
        if not cookie_val or "|" not in cookie_val:
            return False
        user_id, signature = cookie_val.split("|", 1)
        expected_sig = hmac.new(
            get_cookie_secret(), user_id.encode('utf-8'), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_sig)
    except Exception:
        return False


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


# ==========================================
# LANGUAGE SETUP & i18n
# ==========================================
def init_language() -> None:
    if "language" not in st.session_state:
        st.session_state.language = "en"

    col_spacer, col_lang = st.columns([10, 4])
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
        @import url('https://fonts.googleapis.com/css2?family=Permanent+Marker&family=Kalam:wght@400;700&display=swap');

        html, body, [data-testid="stAppViewContainer"], .st-emotion-cache-1vt458e p, label {
            font-family: 'Kalam', cursive;
            font-size: 1.1rem;
        }

        h1, h2, h3, h4, h5, h6, .stButton button {
            font-family: 'Permanent Marker', cursive;
            letter-spacing: 0.05rem;
        }
        
        [data-testid="stHeader"] h1 {
            color: #E74C3C;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            font-size: 4rem;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        
        .actor-slogan {
            font-family: 'Permanent Marker', cursive;
            color: #F39C12;
            font-size: 1.8rem;
            margin-top: -1.5rem;
            margin-bottom: 2rem;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }

        .subtitle-line {
            font-family: 'Kalam', cursive;
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        
        .create-header {
            background-color: #E74C3C;
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
            background-color: #2ECC71;
            padding: 1rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(46, 204, 113, 0.3);
            color: #FFFFFF;
            font-family: 'Permanent Marker', cursive;
            text-align: center;
            font-size: 2rem;
            margin-bottom: 1rem;
        }

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

        div[data-testid="stVerticalBlock"] div:nth-child(2) hr {
            border-color: #f0f2f6 !important;
            box-shadow: 0 0 10px rgba(240, 242, 246, 0.5);
        }
        
        [data-testid="stForm"] input {
            border-radius: 8px !important;
        }
        
        .legal-footer {
            text-align: center;
            margin-top: 4rem;
            padding-top: 1rem;
            font-family: 'Kalam', cursive;
            font-size: 0.9rem;
        }
        .legal-footer a {
            color: #7F8C8D;
            text-decoration: none;
            margin: 0 10px;
            transition: color 0.3s;
        }
        .legal-footer a:hover {
            color: #F39C12;
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
    def save_user_state(
        cls, user_id: str, session_id: str, player_name: str, is_creator: bool
    ) -> None:
        redis_client = get_redis_client()
        key = f"user_state:{user_id}"
        data = {
            "session_id": session_id,
            "player_name": player_name,
            "is_creator": is_creator,
        }
        redis_client.setex(key, TTL, json.dumps(data))

    @classmethod
    def get_user_state(cls, user_id: str) -> Optional[dict]:
        redis_client = get_redis_client()
        data = redis_client.get(f"user_state:{user_id}")
        return json.loads(data) if data else None

    @classmethod
    def clear_user_state(cls, user_id: str) -> None:
        redis_client = get_redis_client()
        redis_client.delete(f"user_state:{user_id}")

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
def render_footer() -> None:
    text = st.session_state.text
    imprint_text = text.get("imprint", "Impressum")
    privacy_text = text.get("privacy_policy", "Datenschutz")

    st.markdown(
        f"""
        <div class="legal-footer">
            <a href="https://versteckmich.de/sokrates" target="_blank">{imprint_text}</a> | 
            <a href="https://versteckmich.de/sokrates" target="_blank">{privacy_text}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def check_cookies() -> None:
    if st.session_state.get("cookies_accepted", False):
        return

    cookie_manager: stx.CookieManager = stx.CookieManager(key="global_cookie_manager")
    cookie_val: Optional[str] = cookie_manager.get(cookie="user_id")

    if cookie_val and verify_cookie(cookie_val):
        st.session_state.cookies_accepted = True
        st.session_state.user_id = cookie_val.split("|")[0]
        return

    with st.container():
        st.info("🍪 Cookies are required for session stability.")
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Accept", type="primary"):
                # Generiere die ID und das HMAC-Signierte Token
                raw_uuid = str(uuid.uuid4())
                signed_id = sign_cookie(raw_uuid)

                st.session_state.cookies_accepted = True
                st.session_state.user_id = raw_uuid

                # Signal für die main() Funktion setzen, um den JS-Injector abzufeuern
                st.session_state.set_cookie_now = signed_id

                st.rerun()
        with col2:
            if st.button("Decline"):
                st.error("Cookies are mandatory. Reload the page to accept.")
                render_footer()
                st.stop()

    render_footer()
    st.stop()


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
                if not check_rate_limit(user_id):
                    st.error("Too many sessions created. Please wait a minute.")
                else:
                    session_hash: str = GameSessionManager.create_session(
                        creator_name, create_pw
                    )

                    GameSessionManager.save_user_state(
                        user_id, session_hash, creator_name, True
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
                    GameSessionManager.save_user_state(
                        user_id, join_id, join_name, False
                    )

                    st.session_state.session_id = join_id
                    st.session_state.player_name = join_name
                    st.session_state.is_creator = False
                    st.session_state.current_page = "lobby"
                    st.rerun()
                else:
                    st.error(msg)


# --- OPTIMIERT FÜR MINIMALE DATENBANKABFRAGEN ---
@st.fragment(run_every="5s")
def render_lobby() -> None:
    text = st.session_state.text
    session_id: str = st.session_state.session_id
    is_creator: bool = st.session_state.is_creator
    user_id = st.session_state.user_id

    session_data: Optional[Dict[str, Any]] = GameSessionManager.get_session(session_id)

    if not session_data:
        st.error(text.get("waiting_host", "Session not found."))
        if st.button("Back to Hub"):
            GameSessionManager.clear_user_state(user_id)
            st.session_state.current_page = "landing"
            st.rerun()
        return

    if session_data.get("redirect"):
        new_id = session_data["redirect"]
        st.session_state.session_id = new_id
        GameSessionManager.save_user_state(
            user_id, new_id, st.session_state.player_name, is_creator
        )
        st.rerun()

    if session_data.get("status") == "running":
        st.session_state.current_page = "game"
        st.rerun()

    st.write(f"### Dressing Room: ID")
    st.code(session_id, language=None)
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
                GameSessionManager.clear_user_state(user_id)
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

    # --- WORKAROUND: Unsichtbare Cookie-Injection NACH dem Button-Klick ---
    # Das feuert, wenn check_cookies() st.session_state.set_cookie_now gesetzt hat.
    if "set_cookie_now" in st.session_state:
        set_secure_cookie("cookie_consent", "true", 30)
        set_secure_cookie("user_id", st.session_state.set_cookie_now, 30)
        del st.session_state["set_cookie_now"]

    check_cookies()

    user_id = st.session_state.user_id

    if "current_page" not in st.session_state:
        restored_state = GameSessionManager.get_user_state(user_id)

        if restored_state:
            session_data = GameSessionManager.get_session(restored_state["session_id"])

            if session_data:
                if session_data.get("redirect"):
                    new_id = session_data["redirect"]
                    st.session_state.session_id = new_id
                    GameSessionManager.save_user_state(
                        user_id,
                        new_id,
                        restored_state["player_name"],
                        restored_state["is_creator"],
                    )
                    session_data = GameSessionManager.get_session(new_id)
                else:
                    st.session_state.session_id = restored_state["session_id"]

                st.session_state.player_name = restored_state["player_name"]
                st.session_state.is_creator = restored_state["is_creator"]

                if session_data and session_data.get("status") == "running":
                    st.session_state.current_page = "game"
                else:
                    st.session_state.current_page = "lobby"
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

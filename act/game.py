import streamlit as st
import time
import random
import json
from typing import Dict, Any


def load_game_data(lang: str) -> tuple:
    """Loads the game data from JSON files based on the selected language."""
    emotions = json.load(open("locales/emotions.json"))[lang]
    roles = json.load(open("locales/roles.json"))
    sentences = json.load(open("locales/sentences.json"))[lang]
    return emotions, roles, sentences


def generate_prompt(mode: int, lang: str) -> Dict[str, str]:
    """Generates a random prompt based on the selected game mode."""
    emotions, roles, sentences = load_game_data(lang)
    prompt = {"emotion": "", "character": "", "source": "", "sentence": ""}

    prompt["sentence"] = random.choice(sentences)

    if mode in [1, 3]:
        prompt["emotion"] = random.choice(emotions)
    if mode in [2, 3]:
        role = random.choice(roles)
        prompt["character"] = role["name"]
        prompt["source"] = role["source"]

    return prompt


def handle_loading(text: str, duration: float = 1.0):
    """Displays a fast progress bar blocking execution."""
    bar = st.progress(0, text=text)
    steps = 50
    sleep_time = duration / steps
    for i in range(steps):
        time.sleep(sleep_time)
        bar.progress(int((i + 1) * (100 / steps)), text=text)
    time.sleep(0.1)
    bar.empty()


# --- OPTIMIERT FÜR MINIMALE DATENBANKABFRAGEN ---
@st.fragment(run_every="3s")
def render_game_board(session_manager):
    """
    Polls the Redis database every 3 seconds to ensure all players
    see exactly the same screen.
    """
    session_id = st.session_state.session_id
    session_data = session_manager.get_session(session_id)
    text = st.session_state.text
    lang = st.session_state.language
    user_id = st.session_state.user_id

    if not session_data or session_data.get("status") != "running":
        session_manager.clear_user_state(user_id)
        st.session_state.current_page = "landing"
        st.rerun()

    if "game_phase" not in session_data:
        session_data["game_phase"] = 1
        session_data["selected_mode"] = None
        session_data["current_prompt"] = {}
        session_manager.update_session_data(session_id, session_data)

    phase = session_data["game_phase"]

    # ==========================================
    # PHASE 1: MODE SELECTION
    # ==========================================
    if phase == 1:
        st.markdown(
            f"<h2 style='text-align: center; font-family: \"Permanent Marker\", cursive; color: #F39C12;'>{text['phase1_title']}</h2>",
            unsafe_allow_html=True,
        )
        st.write("")

        if st.session_state.get("is_loading_mode"):
            mode = st.session_state.loading_mode
            st.markdown(
                f"""
                <div style="background-color: #2ECC71; color: white; padding: 2rem; border-radius: 15px; text-align: center; font-family: 'Permanent Marker', cursive; font-size: 1.5rem; box-shadow: 0 0 20px #2ECC71;">
                    Mode {mode} Selected!
                </div>
                <br>
            """,
                unsafe_allow_html=True,
            )
            handle_loading(text["loading_stage"], 1.0)

            prompt = generate_prompt(mode, lang)
            session_data["game_phase"] = 2
            session_data["selected_mode"] = mode
            session_data["current_prompt"] = prompt
            session_manager.update_session_data(session_id, session_data)

            st.session_state.is_loading_mode = False
            st.rerun()
            return

        st.markdown(
            """
            <style>
            .mode-btn button { font-family: 'Permanent Marker', cursive !important; font-size: 1.2rem !important; padding: 1.5rem !important; }
            </style>
        """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="mode-btn">', unsafe_allow_html=True)
            if st.button(text["mode1_btn"], use_container_width=True, key="m1"):
                st.session_state.is_loading_mode = True
                st.session_state.loading_mode = 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="mode-btn">', unsafe_allow_html=True)
            if st.button(text["mode2_btn"], use_container_width=True, key="m2"):
                st.session_state.is_loading_mode = True
                st.session_state.loading_mode = 2
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="mode-btn">', unsafe_allow_html=True)
            if st.button(text["mode3_btn"], use_container_width=True, key="m3"):
                st.session_state.is_loading_mode = True
                st.session_state.loading_mode = 3
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # PHASE 2: ACTING DISPLAY
    # ==========================================
    elif phase == 2:
        prompt = session_data["current_prompt"]
        mode = session_data["selected_mode"]

        if st.session_state.get("clicked_great"):
            st.balloons()

            st.markdown(
                """
                <style>
                div[data-testid="stButton"] button {
                    background-color: #F1C40F !important;
                    color: #333333 !important;
                    border: none !important;
                    font-family: 'Permanent Marker', cursive !important;
                    font-size: 1.5rem !important;
                    padding: 1.5rem !important;
                    box-shadow: 0 4px 15px rgba(241, 196, 15, 0.6) !important;
                }
                </style>
            """,
                unsafe_allow_html=True,
            )
            st.button(
                "🌟 " + text["btn_great"],
                key="great_btn_active",
                disabled=True,
                use_container_width=True,
            )

            handle_loading(text["loading_return"], 1.0)

            session_data["game_phase"] = 1
            session_data["selected_mode"] = None
            session_data["current_prompt"] = {}
            session_manager.update_session_data(session_id, session_data)

            st.session_state.clicked_great = False
            st.rerun()
            return

        if prompt.get("emotion"):
            st.markdown(
                f"""
            <div style='background-color: #F39C12; padding: 1.5rem; border-radius: 15px; margin-bottom: 1rem; box-shadow: 0 4px 10px rgba(0,0,0,0.2);'>
                <h4 style='color: white; margin-bottom: 0; font-family: "Permanent Marker", cursive;'>{text['label_emotion']}</h4>
                <h2 style='color: white; margin-top: 0;'>{prompt['emotion']}</h2>
            </div>
            """,
                unsafe_allow_html=True,
            )

        if prompt.get("character"):
            st.markdown(
                f"""
            <div style='background-color: #2ECC71; padding: 1.5rem; border-radius: 15px; margin-bottom: 1rem; box-shadow: 0 4px 10px rgba(0,0,0,0.2);'>
                <h4 style='color: white; margin-bottom: 0; font-family: "Permanent Marker", cursive;'>{text['label_character']}</h4>
                <h2 style='color: white; margin-top: 0;'>{prompt['character']} <span style='font-size: 1.2rem; opacity: 0.8;'>({prompt['source']})</span></h2>
            </div>
            """,
                unsafe_allow_html=True,
            )

        if prompt.get("sentence"):
            st.markdown(
                f"""
            <div style='background-color: #E74C3C; padding: 1.5rem; border-radius: 15px; margin-bottom: 1rem; box-shadow: 0 4px 10px rgba(0,0,0,0.2);'>
                <h4 style='color: white; margin-bottom: 0; font-family: "Permanent Marker", cursive;'>{text['label_sentence']}</h4>
                <h1 style='color: white; font-family: "Kalam", cursive; font-style: italic; margin-top: 0;'>" {prompt['sentence']} "</h1>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.write("")
        st.write("")

        col_reroll, col_great = st.columns([1, 2])

        with col_reroll:
            st.markdown(
                """
                <style>
                div[data-testid="column"]:nth-child(1) button[key="reroll_btn"] {
                    font-family: 'Permanent Marker', cursive !important;
                    font-size: 1.2rem !important;
                    padding: 1.5rem !important;
                }
                </style>
            """,
                unsafe_allow_html=True,
            )

            if st.button(
                "🎲 " + text.get("btn_reroll", "Reroll"),
                use_container_width=True,
                key="reroll_btn",
            ):
                session_data["current_prompt"] = generate_prompt(mode, lang)
                session_manager.update_session_data(session_id, session_data)
                st.rerun()

        with col_great:
            st.markdown(
                """
                <style>
                div[data-testid="column"]:nth-child(2) button[key="great_btn"] {
                    background-color: #7F8C8D !important;
                    color: #FFFFFF !important;
                    border: none !important;
                    font-family: 'Permanent Marker', cursive !important;
                    font-size: 1.5rem !important;
                    padding: 1.5rem !important;
                    box-shadow: 0 4px 10px rgba(127, 140, 141, 0.4) !important;
                }
                div[data-testid="column"]:nth-child(2) button[key="great_btn"]:hover {
                    background-color: #95A5A6 !important;
                }
                </style>
            """,
                unsafe_allow_html=True,
            )

            if st.button(
                "🌟 " + text["btn_great"], use_container_width=True, key="great_btn"
            ):
                st.session_state.clicked_great = True
                st.rerun()


def game_page(session_manager):
    text = st.session_state.text
    user_id = st.session_state.user_id

    st.title(text["app_title"])
    st.markdown(
        f'<div class="actor-slogan" style="margin-top: -1rem; margin-bottom: 2rem;">{text["slogan"]}</div>',
        unsafe_allow_html=True,
    )

    render_game_board(session_manager)

    st.divider()
    if st.button(text["leave_scene"], type="secondary"):
        session_manager.clear_user_state(user_id)
        st.session_state.current_page = "landing"
        st.session_state.session_id = None
        st.rerun()

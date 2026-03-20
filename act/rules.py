import streamlit as st


@st.fragment
def display(text: dict) -> None:
    """
    Zeigt die Spielregeln in einem ausklappbaren Expander an.
    Nimmt das zentrale 'text' Dictionary aus dem st.session_state als Argument.
    """
    with st.expander(text.get("rules_title", "📖 How to play act!"), expanded=False):
        st.markdown(f"**{text.get('rules_intro', '')}**")
        st.write("---")

        st.markdown(f"### {text.get('rules_step1_title', '')}")
        st.write(text.get('rules_step1_text', ''))

        st.markdown(f"### {text.get('rules_mode1_title', '')}")
        st.write(text.get('rules_mode1_text', ''))

        st.markdown(f"### {text.get('rules_mode2_title', '')}")
        st.write(text.get('rules_mode2_text', ''))

        st.markdown(f"### {text.get('rules_mode3_title', '')}")
        st.write(text.get('rules_mode3_text', ''))

        st.write("---")
        st.markdown(f"### {text.get('rules_scoring_title', '')}")
        st.write(text.get('rules_scoring_text', ''))

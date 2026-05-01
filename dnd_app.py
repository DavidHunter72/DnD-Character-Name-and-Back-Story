import streamlit as st
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="D&D Character Generator", page_icon="🧙")

st.title("🧙 AI D&D Character Creator")
st.caption("Generate names, backstories, and personalities for your D&D Beyond characters")

# --- Inputs ---
race = st.text_input("Race (e.g., Elf, Tiefling, Human)")
char_class = st.text_input("Class (e.g., Rogue, Wizard, Fighter)")
background = st.text_input("Background (optional)")
traits = st.text_area("Personality / Traits (optional)")

# --- Generate Name ---
if st.button("🎲 Generate Name"):
    if race:
        prompt = f"Generate a unique fantasy name suitable for a {race} character."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        generated_name = response.choices[0].message.content.strip()
        st.session_state["name"] = generated_name

# Use generated name or manual input
name = st.text_input("Character Name", value=st.session_state.get("name", ""))
def generate_portrait(name, race, char_class):
    prompt = f"""
    A detailed fantasy portrait of a {race} {char_class} named {name}.
    Highly detailed, cinematic lighting, digital art, D&D style, character portrait.
    """

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="512x512"
    )

    return result.data[0].url
# --- Generate Backstory ---
if st.button("📜 Generate Full Character"):
    if name and race and char_class:
        prompt = f"""
        Create a detailed Dungeons & Dragons character.

        Name: {name}
        Race: {race}
        Class: {char_class}
        Background: {background}
        Traits: {traits}

        Include:
        - Origin story
        - Personality
        - Motivation
        - A unique plot hook
        """

        with st.spinner("Forging your character..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            story = response.choices[0].message.content

        st.subheader("✨ Your Character")
        st.write(story)

    else:
        st.warning("Please fill in name, race, and class.")

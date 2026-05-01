import streamlit as st
from openai import OpenAI

#background art
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("https://images.unsplash.com/photo-1518709268805-4e9042af2176");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}

/* Dark overlay for readability */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    z-index: -1;
}
</style>
""", unsafe_allow_html=True)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="D&D Character Generator", page_icon="🧙")

st.title("🧙 AI D&D Character Creator")
st.caption("Generate names, backstories, and personalities for your D&D Beyond characters")

# --- Inputs ---
race = st.text_input("Race (e.g., Elf, Tiefling, Human)")
char_class = st.text_input("Class (e.g., Rogue, Wizard, Fighter)")
background = st.text_input("Background (optional)")
traits = st.text_area("Personality / Traits (optional)")
name = st.text_input(
    "Character Name",
    value=st.session_state.get("name", "")
)
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
import base64

def generate_portrait(name, race, char_class):
    try:
        prompt = f"""
        Fantasy character portrait of a {race} {char_class} named {name}.
        Highly detailed, cinematic lighting, D&D style, digital art.
        """

        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="512x512"
        )

        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        return image_bytes

    except Exception as e:
        st.error(f"Image generation failed: {e}")
        return None
# --- Generate Backstory ---

if st.button("📜 Generate Full Character"):
    if name and race and char_class:

        with st.spinner("Forging your character..."):
            # Generate story
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"""
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
                }]
            )

            story = response.choices[0].message.content

        # 🎨 Generate portrait AFTER inputs exist
        st.subheader("🎨 Character Portrait")

        with st.spinner("Painting your character..."):
         image = generate_portrait(name, race, char_class)

if st.button("📜 Generate Full Character"):
    if name and race and char_class:

        with st.spinner("Forging your character..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"""
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
                }]
            )

            story = response.choices[0].message.content

        # 🎨 Portrait
        st.subheader("🎨 Character Portrait")

        with st.spinner("Painting your character..."):
            image = generate_portrait(name, race, char_class)

        if image:
            st.image(image, caption=f"{name} the {race} {char_class}")
        else:
            st.warning("Could not generate portrait.")

        # 📜 Story
        st.subheader("✨ Your Character")
        st.write(story)

    else:
        st.warning("Please fill in name, race, and class.")

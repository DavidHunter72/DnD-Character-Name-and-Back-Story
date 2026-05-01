import streamlit as st
from openai import OpenAI
import base64
from io import BytesIO

# -------------------------------
# 🔐 API
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="D&D Character Generator", page_icon="🧙")

# -------------------------------
# 🎨 STYLING
# -------------------------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("https://images.unsplash.com/photo-1518709268805-4e9042af2176");
    background-size: cover;
    background-attachment: fixed;
}
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    z-index: -1;
}
.card {
    background: rgba(20,20,30,0.9);
    padding: 20px;
    border-radius: 15px;
    border: 2px solid #c9a96e;
}
.title {
    font-size: 28px;
    color: #f5d27a;
    font-weight: bold;
}
.sub {
    color: #ddd;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 🎲 FUNCTIONS
# -------------------------------
def generate_name(race):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"""
            Generate ONE fantasy character name for a {race}.

            STRICT RULES:
            - Only output the name
            - No explanations
            - No extra text
            - 1–3 words maximum
            - Must sound like a person, not a place or object
            """
        }]
    )

    name = response.choices[0].message.content.strip()

    # 🧹 Clean up bad outputs
    name = name.split("\n")[0]  # remove extra lines

    # 🚫 Reject bad responses
    bad_words = ["catacombs", "dungeon", "temple", "fortress", "cave"]
    if any(word in name.lower() for word in bad_words):
        return "Arin Valeth"  # fallback safe name

    return name


def generate_stats():
    import random
    return {
        "STR": random.randint(8, 18),
        "DEX": random.randint(8, 18),
        "CON": random.randint(8, 18),
        "INT": random.randint(8, 18),
        "WIS": random.randint(8, 18),
        "CHA": random.randint(8, 18),
    }


def generate_story(name, race, char_class, background, traits):
    prompt = f"""
    Create a detailed Dungeons & Dragons character.

    Name: {name}
    Race: {race}
    Class: {char_class}
    Background: {background}
    Traits: {traits}

    Include origin, personality, motivation, and a plot hook.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def generate_portrait(name, race, char_class):
    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=f"fantasy portrait of {name}, a {race} {char_class}, D&D style",
            size="512x512"
        )
        img = base64.b64decode(result.data[0].b64_json)
        return img
    except:
        return None


# -------------------------------
# 🖥️ UI INPUTS
# -------------------------------

st.title("🧙 AI D&D Character Creator")

race = st.text_input("Race")
char_class = st.text_input("Class")
background = st.text_input("Background")
traits = st.text_area("Traits")

if st.button("🎲 Generate Name"):
    if race:
        st.session_state["name"] = generate_name(race)

name = st.text_input("Name", value=st.session_state.get("name", ""))

level = st.slider("Level", 1, 20, 1)

# -------------------------------
# 📜 GENERATE CHARACTER
# -------------------------------

if st.button("📜 Generate Character", key="gen_char"):
    if name and race and char_class:

        with st.spinner("Generating character..."):
            story = generate_story(name, race, char_class, background, traits)
            stats = generate_stats()
            hp = stats["CON"] * level
            image = generate_portrait(name, race, char_class)

        # -------------------------------
        # 🎴 CHARACTER CARD
        # -------------------------------
        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.markdown(f'<div class="title">{name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sub">{race} {char_class} | Level {level}</div>', unsafe_allow_html=True)

        st.markdown("---")

        col1, col2 = st.columns([1,2])

        with col1:
            if image:
                st.image(image)
            else:
                st.image("https://via.placeholder.com/300x400?text=No+Portrait")

            st.markdown(f"**❤️ HP:** {hp}")

            st.markdown("### 📊 Stats")
            for k, v in stats.items():
                st.write(f"{k}: {v}")

        with col2:
            st.markdown("### 📜 Backstory")
            st.write(story)

        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------------------
        # 📄 DOWNLOAD
        # -------------------------------
        file_content = f"""
        {name}
        {race} {char_class} (Level {level})

        HP: {hp}

        Stats:
        {stats}

        Backstory:
        {story}
        """

        st.download_button(
            "📄 Download Character Sheet",
            data=file_content,
            file_name=f"{name}_character.txt"
        )

    else:
        st.warning("Fill in name, race, and class.")

import streamlit as st
from openai import OpenAI
import random

# -----------------------------
# 🔐 CONFIG
# -----------------------------
st.set_page_config(page_title="D&D Character Generator", page_icon="🧙")

api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("Missing API key")
    st.stop()

client = OpenAI(api_key=api_key)

# -----------------------------
# 🧠 SESSION STATE INIT
# -----------------------------
if "name" not in st.session_state:
    st.session_state.name = ""

# -----------------------------
# 🎲 FUNCTIONS
# -----------------------------

def generate_name(race):
    prompt = f"Generate one fantasy character name for a {race}. Only output the name."
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip().split("\n")[0]


def generate_stats():
    return {k: random.randint(8, 18) for k in ["STR","DEX","CON","INT","WIS","CHA"]}


def calculate_hp(char_class, level, con):
    hit_die = {"fighter":10,"rogue":8,"wizard":6}
    return hit_die.get(char_class.lower(), 8) * level + (con - 10)


def generate_story(name, race, char_class, background, traits):
    prompt = f"""
    Create a D&D character.

    Name: {name}
    Race: {race}
    Class: {char_class}
    Background: {background}
    Traits: {traits}

    Include origin, personality, and motivation.
    """
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )
    return res.choices[0].message.content


def generate_equipment(char_class):
    base = ["Backpack","Torch","Rations","Waterskin"]
    class_items = {
        "fighter":["Longsword","Shield"],
        "wizard":["Spellbook","Staff"],
        "rogue":["Dagger","Thieves’ Tools"]
    }
    gear = class_items.get(char_class.lower(), ["Dagger"]) + base
    gold = random.randint(10,150)
    return gear, gold


def generate_spells(char_class):
    if char_class.lower() not in ["wizard","cleric","sorcerer"]:
        return []

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role":"user",
            "content":f"List 5 spells for a {char_class}. Names only."
        }]
    )
    return [s.strip("- ") for s in res.choices[0].message.content.split("\n") if s]


# -----------------------------
# 🖥️ UI
# -----------------------------
st.title("🧙 D&D Character Generator")

race = st.text_input("Race", key="race")
char_class = st.text_input("Class", key="class")
background = st.text_input("Background", key="background")
traits = st.text_area("Traits", key="traits")

# 🎲 Name generator
if st.button("🎲 Generate Name", key="gen_name_btn"):
    if race:
        st.session_state.name = generate_name(race)
    else:
        st.warning("Enter a race first")

# Name input (linked to state)
name = st.text_input("Name", key="name")

level = st.slider("Level", 1, 20, 1, key="level")

# -----------------------------
# 🚀 GENERATE CHARACTER
# -----------------------------
if st.button("📜 Generate Character", key="gen_char_btn"):

    if not (name and race and char_class):
        st.warning("Please fill in Name, Race, and Class")
        st.stop()

    with st.spinner("Generating character..."):

        stats = generate_stats()
        hp = calculate_hp(char_class, level, stats["CON"])
        story = generate_story(name, race, char_class, background, traits)
        gear, gold = generate_equipment(char_class)
        spells = generate_spells(char_class)

    # -----------------------------
    # 🎴 DISPLAY
    # -----------------------------
    st.subheader(f"{name} — Level {level} {race} {char_class}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Stats")
        for k, v in stats.items():
            st.write(f"{k}: {v}")

        st.markdown(f"### ❤️ HP: {hp}")
        st.markdown(f"### 💰 Gold: {gold}")

        st.markdown("### ⚔️ Equipment")
        for item in gear:
            st.write(f"- {item}")

    with col2:
        st.markdown("### 📜 Backstory")
        st.write(story)

        if spells:
            st.markdown("### 🧙 Spells")
            for spell in spells:
                st.write(f"✨ {spell}")

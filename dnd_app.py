import streamlit as st
from openai import OpenAI
import random
import base64
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

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
# 🧠 SESSION STATE
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "builder"

if "name" not in st.session_state:
    st.session_state.name = ""

# -----------------------------
# 🎲 FUNCTIONS
# -----------------------------

def generate_name(race):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"Generate ONE fantasy character name for a {race}. Only the name."
        }]
    )
    return res.choices[0].message.content.strip().split("\n")[0]


def generate_stats():
    return {k: random.randint(8, 18) for k in ["STR","DEX","CON","INT","WIS","CHA"]}


def stat_modifier(score):
    return (score - 10) // 2


def calculate_hp(char_class, level, con):
    hit_die = {"fighter":10,"rogue":8,"wizard":6,"cleric":8}
    return hit_die.get(char_class.lower(), 8) * level + stat_modifier(con) * level


def generate_story(name, race, char_class, background, traits):
    prompt = f"""
    Create a D&D character.

    Name: {name}
    Race: {race}
    Class: {char_class}
    Background: {background}
    Traits: {traits}

    Include origin, personality, motivation, and a plot hook.
    """
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )
    return res.choices[0].message.content


def generate_equipment(char_class):
    base = ["Backpack","Torch","Rations","Waterskin"]
    class_items = {
        "fighter":["Longsword","Shield","Chain Mail"],
        "wizard":["Spellbook","Staff"],
        "rogue":["Dagger","Thieves’ Tools"],
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
            "content":f"""
            List 5 D&D spells for a {char_class}.
            Format:
            Spell Name - short description
            """
        }]
    )

    spells = []
    for line in res.choices[0].message.content.split("\n"):
        if "-" in line:
            name, desc = line.split("-", 1)
            spells.append({"name": name.strip(), "desc": desc.strip()})
    return spells


def generate_portrait(name, race, char_class):
    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=f"""
            Epic fantasy portrait of {name}, a {race} {char_class}.
            cinematic lighting, ultra detailed, dnd style, no text
            """,
            size="512x512"
        )
        return base64.b64decode(result.data[0].b64_json)
    except:
        return None


def create_pdf(char):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph(f"<b>{char['name']}</b>", styles["Title"]))
    elements.append(Paragraph(f"{char['race']} {char['class']} (Level {char['level']})", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Stats table
    stats_data = [["Stat", "Score", "Mod"]]
    for k, v in char["stats"].items():
        stats_data.append([k, v, stat_modifier(v)])

    table = Table(stats_data)
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"HP: {char['hp']}", styles["Normal"]))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Equipment", styles["Heading2"]))
    for item in char["gear"]:
        elements.append(Paragraph(f"- {item}", styles["Normal"]))

    if char["spells"]:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Spells", styles["Heading2"]))
        for s in char["spells"]:
            elements.append(Paragraph(f"{s['name']}: {s['desc']}", styles["Normal"]))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Backstory", styles["Heading2"]))
    elements.append(Paragraph(char["story"], styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# -----------------------------
# 🎮 NAVIGATION
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    if st.button("🛠 Builder"):
        st.session_state.page = "builder"

with col2:
    if st.button("🎴 Character Sheet"):
        st.session_state.page = "sheet"

# -----------------------------
# 🛠 BUILDER PAGE
# -----------------------------
if st.session_state.page == "builder":

    st.title("🧙 Character Builder")

    race = st.text_input("Race")
    char_class = st.text_input("Class")
    background = st.text_input("Background")
    traits = st.text_area("Traits")

    if st.button("🎲 Generate Name", key="gen_name"):
        if race:
            st.session_state.name = generate_name(race)

    name = st.text_input("Name", key="name")
    level = st.slider("Level", 1, 20, 1)

    if st.button("📜 Generate Character"):

        if not (name and race and char_class):
            st.warning("Fill required fields")
            st.stop()

        with st.spinner("Generating..."):
            stats = generate_stats()
            hp = calculate_hp(char_class, level, stats["CON"])
            story = generate_story(name, race, char_class, background, traits)
            gear, gold = generate_equipment(char_class)
            spells = generate_spells(char_class)
            image = generate_portrait(name, race, char_class)

        st.session_state.character = {
            "name": name,
            "race": race,
            "class": char_class,
            "level": level,
            "hp": hp,
            "stats": stats,
            "gear": gear,
            "gold": gold,
            "spells": spells,
            "story": story,
            "image": image
        }

        st.success("Character created! Go to Character Sheet →")

# -----------------------------
# 🎴 CHARACTER SHEET PAGE
# -----------------------------
elif st.session_state.page == "sheet":

    char = st.session_state.get("character")

    if not char:
        st.warning("No character yet")
    else:
        st.title(char["name"])
        st.write(f"{char['race']} {char['class']} | Level {char['level']}")

        if char["image"]:
            st.image(char["image"])

        st.markdown("### 📊 Stats")
        for k, v in char["stats"].items():
            st.write(f"{k}: {v} (mod {stat_modifier(v)})")

        st.markdown(f"### ❤️ HP: {char['hp']}")
        st.markdown(f"### 💰 Gold: {char['gold']}")

        st.markdown("### ⚔️ Equipment")
        for item in char["gear"]:
            st.write(f"- {item}")

        if char["spells"]:
            st.markdown("### 🧙 Spells")
            for s in char["spells"]:
                st.write(f"✨ {s['name']} — {s['desc']}")

        st.markdown("### 📜 Backstory")
        st.write(char["story"])

        # PDF
        pdf = create_pdf(char)

        st.download_button(
            "📄 Download PDF Character Sheet",
            pdf,
            file_name=f"{char['name']}.pdf"
        )

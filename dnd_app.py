import streamlit as st
from openai import OpenAI
import random
import base64
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# -----------------------------
# 🔐 CONFIG
# -----------------------------
st.set_page_config(page_title="D&D Character Generator", page_icon="🧙")

api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("Missing OpenAI API key")
    st.stop()

client = OpenAI(api_key=api_key)

# -----------------------------
# 🎨 STYLING
# -----------------------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("https://images.unsplash.com/photo-1518709268805-4e9042af2176");
    background-size: cover;
}
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
}
.card {
    background: rgba(20,20,30,0.9);
    padding: 20px;
    border-radius: 15px;
    border: 2px solid #c9a96e;
}
.title { color: #f5d27a; font-size: 26px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

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


def generate_portrait(name, race, char_class):
    try:
        img = client.images.generate(
            model="gpt-image-1",
            prompt=f"fantasy portrait of {name}, a {race} {char_class}",
            size="512x512"
        )
        return base64.b64decode(img.data[0].b64_json)
    except:
        return None


def generate_equipment(char_class):
    base = ["Backpack","Torch","Rations","Waterskin"]
    class_items = {
        "fighter":["Longsword","Shield","Chain Mail"],
        "wizard":["Spellbook","Staff"],
        "rogue":["Dagger","Thieves’ Tools"],
    }
    gear = class_items.get(char_class.lower(), ["Dagger"]) + base
    gold = random.randint(10,150)
    magic = ["Potion of Healing"] if random.random() < 0.4 else []
    return gear, gold, magic


def get_spell_slots(char_class, level):
    if char_class.lower() not in ["wizard","cleric","sorcerer"]:
        return None
    return {"Level 1": min(4, level+1), "Level 2": max(0, level-2)}


def generate_spells(char_class):
    if char_class.lower() not in ["wizard","cleric","sorcerer"]:
        return []
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"List 5 spells for a {char_class}. Names only."}]
    )
    return [s.strip("- ") for s in res.choices[0].message.content.split("\n") if s]


def calculate_hp(char_class, level, con):
    hit_die = {"fighter":10,"wizard":6,"rogue":8}
    return hit_die.get(char_class.lower(),8)*level + (con-10)


def create_pdf(name, race, char_class, level, hp, stats, gear, spells, story):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph(f"<b>{name}</b>", styles["Title"]))
    content.append(Paragraph(f"{race} {char_class} (Level {level})", styles["Normal"]))
    content.append(Spacer(1,10))

    content.append(Paragraph(f"HP: {hp}", styles["Normal"]))

    for k,v in stats.items():
        content.append(Paragraph(f"{k}: {v}", styles["Normal"]))

    content.append(Spacer(1,10))
    content.append(Paragraph("Equipment:", styles["Heading2"]))
    for item in gear:
        content.append(Paragraph(f"- {item}", styles["Normal"]))

    if spells:
        content.append(Paragraph("Spells:", styles["Heading2"]))
        for s in spells:
            content.append(Paragraph(f"- {s}", styles["Normal"]))

    content.append(Spacer(1,10))
    content.append(Paragraph("Backstory:", styles["Heading2"]))
    content.append(Paragraph(story, styles["Normal"]))

    doc.build(content)
    buffer.seek(0)
    return buffer

# -----------------------------
# 🖥️ UI
# -----------------------------
st.title("🧙 D&D Character Generator")

race = st.text_input("Race")
char_class = st.text_input("Class")
background = st.text_input("Background")
traits = st.text_area("Traits")

if st.button("🎲 Generate Name", key="name"):
    if race:
        st.session_state["name"] = generate_name(race)

name = st.text_input("Name", value=st.session_state.get("name",""))
level = st.slider("Level", 1, 20, 1)

# -----------------------------
# 🚀 GENERATE
# -----------------------------
if st.button("📜 Generate Character", key="char"):

    if not (name and race and char_class):
        st.warning("Fill required fields")
        st.stop()

    with st.spinner("Generating..."):
        stats = generate_stats()
        story = generate_story(name, race, char_class, background, traits)
        gear, gold, magic = generate_equipment(char_class)
        spells = generate_spells(char_class)
        slots = get_spell_slots(char_class, level)
        hp = calculate_hp(char_class, level, stats["CON"])
        image = generate_portrait(name, race, char_class)

    # 🎴 DISPLAY
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(f'<div class="title">{name}</div>', unsafe_allow_html=True)
    st.write(f"{race} {char_class} | Level {level} | HP {hp} | Gold {gold}")

    col1, col2 = st.columns([1,2])

    with col1:
        if image:
            st.image(image)
    with col2:
        st.write(story)

    st.markdown("### 📊 Stats")
    st.write(stats)

    st.markdown("### ⚔️ Equipment")
    st.write(gear)

    if magic:
        st.markdown("### ✨ Magic Items")
        st.write(magic)

    if slots:
        st.markdown("### 🧙 Spell Slots")
        st.write(slots)

    if spells:
        st.markdown("### 📖 Spells")
        st.write(spells)

    st.markdown('</div>', unsafe_allow_html=True)

    # 📄 PDF
    pdf = create_pdf(name, race, char_class, level, hp, stats, gear, spells, story)

    st.download_button(
        "📄 Download PDF",
        pdf,
        file_name=f"{name}.pdf"
    )

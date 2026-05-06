import streamlit as st
from openai import OpenAI
import random
import base64
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="D&D Character Generator", page_icon="🧙")

client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))

# -----------------------------
# STYLE (UI)
# -----------------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(-45deg, #1a1a2e, #16213e, #0f3460, #000000);
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
}

@keyframes gradientBG {
    0% {background-position:0% 50%;}
    50% {background-position:100% 50%;}
    100% {background-position:0% 50%;}
}

.card {
    background: rgba(0,0,0,0.75);
    padding: 20px;
    border-radius: 15px;
    border: 2px solid #c9a44c;
    margin-bottom: 15px;
}
.title {
    font-size: 28px;
    color: #f5d67b;
    font-weight: bold;
}
.section {
    color: #f5d67b;
    font-size: 20px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SESSION STATE
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "builder"

if "name" not in st.session_state:
    st.session_state.name = ""

# -----------------------------
# FUNCTIONS
# -----------------------------
def mod(x): return (x - 10) // 2

def generate_name(race):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"Fantasy name for a {race}. Only name."}]
    )
    return res.choices[0].message.content.strip()

def generate_stats():
    return {k: random.randint(8,18) for k in ["STR","DEX","CON","INT","WIS","CHA"]}

def hp_calc(cls, lvl, con):
    base = {"fighter":10,"rogue":8,"wizard":6, "barbarian":12, "sorcerer": 6}
    return base.get(cls.lower(),8)*lvl + mod(con)*lvl

def story(name,race,cls):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"Backstory for {name}, {race} {cls}"}]
    ).choices[0].message.content

def spells(cls):
    if cls.lower() not in ["wizard","cleric","sorcerer"]:
        return []
    txt = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"5 spells for {cls}: Spell - description"}]
    ).choices[0].message.content
    out=[]
    for l in txt.split("\n"):
        if "-" in l:
            n,d=l.split("-",1)
            out.append({"name":n.strip(),"desc":d.strip()})
    return out

def portrait(name, race, cls):
    try:
        cls_lower = cls.lower()

        # 🎯 Class-specific styling
        class_style = {
            "barbarian": "massive muscular warrior, fur armor, war paint, savage expression",
            "fighter": "armored knight, battle-worn steel armor, heroic stance",
            "rogue": "hooded assassin, leather armor, daggers, shadows",
            "wizard": "arcane mage, glowing runes, mystical robes, magic aura",
            "cleric": "holy warrior, radiant light, divine armor, glowing symbol",
            "sorcerer": "wild magic user, energy swirling, glowing hands",
        }

        style = class_style.get(cls_lower, "fantasy adventurer")

        prompt = f"""
        Epic high fantasy character portrait of {name}, a {race} {cls}.
        {style}.
        Ultra detailed, cinematic lighting, dramatic shadows,
        sharp focus, concept art, Dungeons and Dragons style,
        4k digital painting, artstation quality, highly detailed face.
        """

        img = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        return base64.b64decode(img.data[0].b64_json)

    except Exception as e:
        print("IMAGE ERROR:", e)
        return None

def pdf(c):
    buf=BytesIO()
    doc=SimpleDocTemplate(buf)
    styles=getSampleStyleSheet()
    elems=[]
    elems.append(Paragraph(f"<b>{c['name']}</b>",styles["Title"]))
    elems.append(Paragraph(f"{c['race']} {c['class']} Lvl {c['level']}",styles["Normal"]))
    elems.append(Spacer(1,10))
    for k,v in c["stats"].items():
        elems.append(Paragraph(f"{k}: {v} (mod {mod(v)})",styles["Normal"]))
    elems.append(Paragraph(f"HP: {c['hp']}",styles["Normal"]))
    doc.build(elems)
    buf.seek(0)
    return buf
def generate_stats(cls):
    base = {
        "STR": random.randint(8, 12),
        "DEX": random.randint(8, 12),
        "CON": random.randint(8, 12),
        "INT": random.randint(8, 12),
        "WIS": random.randint(8, 12),
        "CHA": random.randint(8, 12),
    }

    cls = cls.lower()

    if cls == "fighter":
        base["STR"] += random.randint(4, 6)
        base["CON"] += random.randint(2, 4)

    elif cls == "rogue":
        base["DEX"] += random.randint(4, 6)
        base["INT"] += random.randint(2, 4)

    elif cls == "wizard":
        base["INT"] += random.randint(4, 6)
        base["DEX"] += random.randint(2, 4)

    elif cls == "cleric":
        base["WIS"] += random.randint(4, 6)
        base["CON"] += random.randint(2, 4)

    elif cls == "sorcerer":
        base["CHA"] += random.randint(4, 6)
        base["CON"] += random.randint(2, 4)
        
    elif cls == "barbarian":
        base["STR"] += random.randint(4, 6)
        base["CON"] += random.randint(4, 6)
    
    for k in base:
        base[k] = min(base[k], 20)

    return base
# -----------------------------
# NAV
# -----------------------------
colA,colB = st.columns(2)
with colA:
    if st.button("🛠 Builder"):
        st.session_state.page="builder"
with colB:
    if st.button("🎴 Sheet"):
        st.session_state.page="sheet"

# -----------------------------
# BUILDER
# -----------------------------
if st.session_state.page == "builder":

    st.title("🧙 Character Builder")

    race = st.text_input("Race")
    cls = st.text_input("Class")

    if st.button("🎲 Generate Name"):
        if race:
            st.session_state.name = generate_name(race)

    name = st.text_input("Name", key="name")
    lvl = st.slider("Level", 1, 20, 1)

    if st.button("📜 Generate Character"):

        char_name = st.session_state.name

        if not (char_name and race and cls):
            st.warning("Fill all fields")
            st.stop()

        # ✅ NOW correctly inside block
        stats = generate_stats(cls)
        hp = hp_calc(cls, lvl, stats["CON"])

        c = {
            "name": char_name,
            "race": race,
            "class": cls,
            "level": lvl,
            "stats": stats,
            "hp": hp,
            "spells": spells(cls),
            "story": story(char_name, race, cls),
            "image": portrait(char_name, race, cls)
        }

        st.session_state.character = c
        st.success("Character Created → Sheet")

# -----------------------------
# SHEET
# -----------------------------
else:
    c = st.session_state.get("character")

    if not c:
        st.warning("Create a character first")
    else:
        st.markdown(f"""
        <div class="card">
            <div class="title">{c['name']}</div>
            {c['race']} {c['class']} • Level {c['level']}
        </div>
        """, unsafe_allow_html=True)

        col1,col2 = st.columns([1,2])

        with col1:
            if c["image"]:
                st.image(c["image"])
            else:
                st.image("https://images.unsplash.com/photo-1608889175123-8ee362201f81")

        with col2:
            st.markdown('<div class="card">',unsafe_allow_html=True)
            for k,v in c["stats"].items():
                st.write(f"{k}: {v} (mod {mod(v)})")
            st.markdown('</div>',unsafe_allow_html=True)

        st.markdown('<div class="card">',unsafe_allow_html=True)
        st.write(f"HP: {c['hp']}")
        st.write(c["story"])
        st.markdown('</div>',unsafe_allow_html=True)

        st.markdown('<div class="card">',unsafe_allow_html=True)
        for s in c["spells"]:
            st.write(f"{s['name']} — {s['desc']}")
        st.markdown('</div>',unsafe_allow_html=True)

        st.download_button("📄 Download PDF", pdf(c), file_name=f"{c['name']}.pdf")

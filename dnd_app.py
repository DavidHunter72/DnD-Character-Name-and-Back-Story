import streamlit as st
from openai import OpenAI
import random
import base64
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="D&D Character Generator", page_icon="🧙")

client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))

# -----------------------------
# SESSION STATE
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "builder"

if "name" not in st.session_state:
    st.session_state.name = ""

# -----------------------------
# DATA
# -----------------------------
OFFICIAL_BACKGROUNDS = {
    "Acolyte": {"skills": ["Insight","Religion"], "tools": ["None"], "feature": "Shelter of the Faithful"},
    "Criminal": {"skills": ["Deception","Stealth"], "tools": ["Thieves' Tools"], "feature": "Criminal Contact"},
    "Soldier": {"skills": ["Athletics","Intimidation"], "tools": ["Gaming Set"], "feature": "Military Rank"},
    "Sage": {"skills": ["Arcana","History"], "tools": ["None"], "feature": "Researcher"},
}

BACKGROUND_BONUSES = {
    "Acolyte": {"WIS": 1},
    "Criminal": {"DEX": 1},
    "Soldier": {"STR": 1},
    "Sage": {"INT": 1},
}

# -----------------------------
# FUNCTIONS
# -----------------------------
def generate_name(race):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"Generate one fantasy name for a {race}. Only name."}]
    )
    return res.choices[0].message.content.strip()

def generate_stats():
    return {k: random.randint(8,18) for k in ["STR","DEX","CON","INT","WIS","CHA"]}

def mod(score):
    return (score - 10)//2

def hp_calc(cls, lvl, con):
    hd = {"fighter":10,"rogue":8,"wizard":6,"cleric":8}
    return hd.get(cls.lower(),8)*lvl + mod(con)*lvl

def generate_story(name,race,cls):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"Create a short D&D backstory for {name}, a {race} {cls}."}]
    )
    return res.choices[0].message.content

def generate_spells(cls):
    if cls.lower() not in ["wizard","cleric","sorcerer"]:
        return []
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"List 5 spells for a {cls}. Format: Spell - description"}]
    )
    spells=[]
    for line in res.choices[0].message.content.split("\n"):
        if "-" in line:
            n,d=line.split("-",1)
            spells.append({"name":n.strip(),"desc":d.strip()})
    return spells

def generate_background(race,cls):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"Create D&D background for {race} {cls}. Include traits, ideal, flaw."}]
    )
    return res.choices[0].message.content

def roleplay_tags(name,race,cls):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"Give alignment and personality type for {name}, a {race} {cls}."}]
    )
    return res.choices[0].message.content

def portrait(name,race,cls):
    try:
        img = client.images.generate(
            model="gpt-image-1",
            prompt=f"epic fantasy portrait of {name}, {race} {cls}, cinematic lighting",
            size="512x512"
        )
        return base64.b64decode(img.data[0].b64_json)
    except:
        return None

def equipment(cls):
    base=["Backpack","Torch","Rations"]
    gear={"fighter":["Sword","Shield"],"wizard":["Staff","Spellbook"],"rogue":["Dagger","Tools"]}
    return gear.get(cls.lower(),["Dagger"])+base, random.randint(10,150)

def make_pdf(c):
    buf=BytesIO()
    doc=SimpleDocTemplate(buf)
    styles=getSampleStyleSheet()
    elems=[]

    elems.append(Paragraph(f"<b>{c['name']}</b>",styles["Title"]))
    elems.append(Paragraph(f"{c['race']} {c['class']} Level {c['level']}",styles["Normal"]))
    elems.append(Spacer(1,10))

    data=[["Stat","Score","Mod"]]
    for k,v in c["stats"].items():
        data.append([k,v,mod(v)])
    t=Table(data)
    t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black)]))
    elems.append(t)

    elems.append(Paragraph(f"HP: {c['hp']}",styles["Normal"]))

    elems.append(Paragraph("Equipment",styles["Heading2"]))
    for g in c["gear"]:
        elems.append(Paragraph(g,styles["Normal"]))

    elems.append(Paragraph("Spells",styles["Heading2"]))
    for s in c["spells"]:
        elems.append(Paragraph(f"{s['name']}: {s['desc']}",styles["Normal"]))

    elems.append(Paragraph("Background",styles["Heading2"]))
    elems.append(Paragraph(c["background"],styles["Normal"]))

    elems.append(Paragraph("Roleplay",styles["Heading2"]))
    elems.append(Paragraph(c["tags"],styles["Normal"]))

    doc.build(elems)
    buf.seek(0)
    return buf

# -----------------------------
# NAV
# -----------------------------
if st.button("🛠 Builder"): st.session_state.page="builder"
if st.button("🎴 Sheet"): st.session_state.page="sheet"

# -----------------------------
# BUILDER
# -----------------------------
if st.session_state.page == "builder":

    st.title("🧙 Character Builder")

    race = st.text_input("Race")
    cls = st.text_input("Class")

    bg_choice = st.selectbox(
        "Background",
        ["AI Generated"] + list(OFFICIAL_BACKGROUNDS.keys())
    )

    # Generate name
    if st.button("🎲 Generate Name"):
        if race:
            st.session_state.name = generate_name(race)

    name = st.text_input("Name", key="name")
    lvl = st.slider("Level", 1, 20, 1)

    # Generate character
    if st.button("📜 Generate Character"):

        char_name = st.session_state.name

        if not (char_name and race and cls):
            st.warning("Fill in Name, Race, and Class")
            st.stop()

        stats = generate_stats()

        # Apply background bonuses
        if bg_choice in BACKGROUND_BONUSES:
            for k, v in BACKGROUND_BONUSES[bg_choice].items():
                stats[k] += v

        hp = hp_calc(cls, lvl, stats["CON"])

        story = generate_story(char_name, race, cls)
        spells = generate_spells(cls)
        gear, gold = equipment(cls)
        img = portrait(char_name, race, cls)
        tags = roleplay_tags(char_name, race, cls)

        # Background
        if bg_choice == "AI Generated":
            bg = generate_background(race, cls)
        else:
            bg = str(OFFICIAL_BACKGROUNDS[bg_choice])

        st.session_state.character = {
            "name": char_name,
            "race": race,
            "class": cls,
            "level": lvl,
            "stats": stats,
            "hp": hp,
            "gear": gear,
            "gold": gold,
            "spells": spells,
            "story": story,
            "image": img,
            "background": bg,
            "tags": tags
        }

        st.success("Character Ready → Sheet")

# -----------------------------
# SHEET
# -----------------------------
else:
    c=st.session_state.get("character")

    if not c:
        st.warning("No character yet")
    else:
        st.title(c["name"])
        st.write(f"{c['race']} {c['class']} Level {c['level']}")

        if c["image"]:
            st.image(c["image"])

        st.markdown("### Stats")
        for k,v in c["stats"].items():
            st.write(f"{k}: {v} (mod {mod(v)})")

        st.write(f"HP: {c['hp']} | Gold: {c['gold']}")

        st.markdown("### Equipment")
        st.write(c["gear"])

        st.markdown("### Spells")
        for s in c["spells"]:
            st.write(f"{s['name']} - {s['desc']}")

        st.markdown("### Background")
        st.write(c["background"])

        st.markdown("### Roleplay")
        st.write(c["tags"])

        pdf=make_pdf(c)
        st.download_button("📄 Download PDF",pdf,file_name=f"{c['name']}.pdf")

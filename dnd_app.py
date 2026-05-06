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
# SESSION STATE
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "builder"

if "name" not in st.session_state:
    st.session_state.name = ""

# -----------------------------
# STYLE
# -----------------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(-45deg, #1a1a2e, #16213e, #0f3460, #000000);
}
.card {
    background: rgba(0,0,0,0.8);
    padding: 20px;
    border-radius: 12px;
    border: 2px solid #c9a44c;
    margin-bottom: 15px;
}
.title {
    font-size: 28px;
    color: #f5d67b;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# DATA
# -----------------------------
POINT_COST = {
    8:0,9:1,10:2,11:3,12:4,13:5,14:7,15:9
}

# -----------------------------
# FUNCTIONS
# -----------------------------
def mod(x):
    return (x - 10)//2

def generate_name(race):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":f"Fantasy name for a {race}. Only name."}]
    )
    return res.choices[0].message.content.strip()

def auto_stats(cls):
    stats = {k:8 for k in ["STR","DEX","CON","INT","WIS","CHA"]}
    points = 27

    priority = {
        "barbarian":["STR","CON","DEX"],
        "fighter":["STR","CON","DEX"],
        "rogue":["DEX","INT","CHA"],
        "wizard":["INT","DEX","CON"],
        "cleric":["WIS","CON","STR"],
        "sorcerer":["CHA","CON","DEX"]
    }

    for stat in priority.get(cls.lower(), stats.keys()):
        while stats[stat] < 15:
            cost = POINT_COST[stats[stat]+1]
            if points >= cost:
                stats[stat]+=1
                points-=cost
            else:
                break

    return stats

def hp_calc(cls, lvl, con):
    base = {
        "barbarian":12,
        "fighter":10,
        "rogue":8,
        "cleric":8,
        "wizard":6,
        "sorcerer":6
    }
    return base.get(cls.lower(),8)*lvl + mod(con)*lvl

def equipment(cls):
    base=["Backpack","Torch","Rations"]
    gear={
        "fighter":["Longsword","Shield"],
        "rogue":["Dagger","Thieves' Tools"],
        "wizard":["Staff","Spellbook"],
        "cleric":["Mace","Holy Symbol"],
        "sorcerer":["Wand"],
        "barbarian":["Greataxe","Javelins"]
    }
    return gear.get(cls.lower(),["Dagger"])+base, random.randint(10,150)

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

def portrait(name,race,cls):
    try:
        style_map = {
            "barbarian":"muscular warrior, fur armor, war paint",
            "fighter":"armored knight, heroic stance",
            "rogue":"hooded assassin, shadowy",
            "wizard":"arcane mage, glowing runes",
            "cleric":"holy warrior, radiant light",
            "sorcerer":"wild magic energy"
        }

        prompt = f"""
        Epic fantasy portrait of {name}, a {race} {cls}.
        {style_map.get(cls.lower(),'fantasy adventurer')}.
        cinematic lighting, ultra detailed, artstation, 4k
        """

        img = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="512x512"
        )

        return base64.b64decode(img.data[0].b64_json)

    except:
        return None

def make_pdf(c):
    buf=BytesIO()
    doc=SimpleDocTemplate(buf)
    styles=getSampleStyleSheet()
    elems=[]

    elems.append(Paragraph(f"<b>{c['name']}</b>",styles["Title"]))
    elems.append(Paragraph(f"{c['race']} {c['class']} Level {c['level']}",styles["Normal"]))
    elems.append(Spacer(1,10))

    for k,v in c["stats"].items():
        elems.append(Paragraph(f"{k}: {v} (mod {mod(v)})",styles["Normal"]))

    elems.append(Paragraph(f"HP: {c['hp']}",styles["Normal"]))

    elems.append(Paragraph("Equipment",styles["Heading2"]))
    for g in c["gear"]:
        elems.append(Paragraph(g,styles["Normal"]))

    elems.append(Paragraph("Spells",styles["Heading2"]))
    for s in c["spells"]:
        elems.append(Paragraph(f"{s['name']}: {s['desc']}",styles["Normal"]))

    doc.build(elems)
    buf.seek(0)
    return buf

# -----------------------------
# NAV
# -----------------------------
col1,col2 = st.columns(2)
if col1.button("🛠 Builder"):
    st.session_state.page="builder"
if col2.button("🎴 Sheet"):
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
    lvl = st.slider("Level",1,20,1)

    mode = st.radio("Stat Mode",["Auto","Manual"])

    manual_stats={}
    total_cost=0

    if mode=="Manual":
        for stat in ["STR","DEX","CON","INT","WIS","CHA"]:
            val=st.slider(stat,8,15,8,key=f"s_{stat}")
            manual_stats[stat]=val
            total_cost+=POINT_COST[val]

        st.write(f"Points: {total_cost}/27")

    if st.button("📜 Generate Character"):

        if not (name and race and cls):
            st.warning("Fill all fields")
            st.stop()

        stats = auto_stats(cls) if mode=="Auto" else manual_stats

        hp = hp_calc(cls,lvl,stats["CON"])
        gear,gold = equipment(cls)

        st.session_state.character = {
            "name":name,
            "race":race,
            "class":cls,
            "level":lvl,
            "stats":stats,
            "hp":hp,
            "gear":gear,
            "gold":gold,
            "spells":spells(cls),
            "story":story(name,race,cls),
            "image":portrait(name,race,cls)
        }

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
        st.write(f"HP: {c['hp']} | Gold: {c['gold']}")
        st.write(c["story"])
        st.markdown('</div>',unsafe_allow_html=True)

        st.markdown('<div class="card">',unsafe_allow_html=True)
        for s in c["spells"]:
            st.write(f"{s['name']} — {s['desc']}")
        st.markdown('</div>',unsafe_allow_html=True)

        st.download_button("📄 Download PDF", make_pdf(c), file_name=f"{c['name']}.pdf")

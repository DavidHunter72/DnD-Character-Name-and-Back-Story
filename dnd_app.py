import streamlit as st
from openai import OpenAI
import random
import base64
from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="AI D&D Character Creator",
    page_icon="🧙",
    layout="wide"
)

client = OpenAI(
    api_key=st.secrets.get("OPENAI_API_KEY")
)

# =========================================================
# SESSION STATE
# =========================================================
if "page" not in st.session_state:
    st.session_state.page = "builder"

if "name" not in st.session_state:
    st.session_state.name = ""

if "character" not in st.session_state:
    st.session_state.character = None

# =========================================================
# STYLE
# =========================================================
st.markdown("""
<style>

.stApp {
    background:
        linear-gradient(rgba(0,0,0,.75), rgba(0,0,0,.85)),
        url("https://images.unsplash.com/photo-1511512578047-dfb367046420");
    background-size: cover;
    background-attachment: fixed;
    color: white;
}

/* Main Cards */
.card {
    background: rgba(10,10,10,.82);
    border: 2px solid #c9a44c;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 18px;
    box-shadow: 0 0 15px rgba(0,0,0,.5);
}

/* Character Title */
.char-title {
    color: #f5d67b;
    font-size: 36px;
    font-weight: bold;
}

/* Section */
.section-title {
    color: #f5d67b;
    font-size: 22px;
    font-weight: bold;
    margin-bottom: 10px;
}

/* Stat Boxes */
.stat-box {
    background: rgba(255,255,255,.06);
    border: 1px solid #c9a44c;
    border-radius: 12px;
    padding: 14px;
    text-align: center;
}

/* Gold Text */
.gold {
    color: gold;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# DATA
# =========================================================
POINT_COST = {
    8: 0,
    9: 1,
    10: 2,
    11: 3,
    12: 4,
    13: 5,
    14: 7,
    15: 9
}

CLASS_DATA = {
    "barbarian": {
        "hit_die": 12,
        "primary": ["STR", "CON", "DEX"],
        "armor": "Medium Armor",
        "weapon": "Greataxe",
        "ac_base": 14
    },

    "fighter": {
        "hit_die": 10,
        "primary": ["STR", "CON", "DEX"],
        "armor": "Heavy Armor",
        "weapon": "Longsword",
        "ac_base": 16
    },

    "rogue": {
        "hit_die": 8,
        "primary": ["DEX", "INT", "CHA"],
        "armor": "Light Armor",
        "weapon": "Daggers",
        "ac_base": 14
    },

    "wizard": {
        "hit_die": 6,
        "primary": ["INT", "DEX", "CON"],
        "armor": "Robes",
        "weapon": "Quarterstaff",
        "ac_base": 12
    },

    "cleric": {
        "hit_die": 8,
        "primary": ["WIS", "CON", "STR"],
        "armor": "Medium Armor",
        "weapon": "Mace",
        "ac_base": 15
    },

    "sorcerer": {
        "hit_die": 6,
        "primary": ["CHA", "CON", "DEX"],
        "armor": "Mystic Cloth",
        "weapon": "Arcane Focus",
        "ac_base": 12
    }
}

SPELL_SLOTS = {
    1: [2],
    2: [3],
    3: [4,2],
    4: [4,3],
    5: [4,3,2]
}

# =========================================================
# HELPERS
# =========================================================
def mod(score):
    return (score - 10) // 2


def proficiency_bonus(level):
    return 2 + ((level - 1) // 4)


# =========================================================
# AI FUNCTIONS
# =========================================================
def generate_name(race):

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"""
                Create ONE fantasy Dungeons and Dragons name
                for a {race} character.

                Only return the name.
                """
            }
        ]
    )

    return res.choices[0].message.content.strip()


def generate_backstory(name, race, cls):

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"""
                Create an immersive D&D backstory for:

                Name: {name}
                Race: {race}
                Class: {cls}

                Include:
                - origin
                - motivation
                - flaw
                - personality
                - plot hook
                """
            }
        ]
    )

    return res.choices[0].message.content


def generate_spells(cls):

    if cls.lower() not in ["wizard", "cleric", "sorcerer"]:
        return []

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"""
                Generate 5 D&D spells for a {cls}.

                Format:
                Spell - short description
                """
            }
        ]
    )

    txt = res.choices[0].message.content

    out = []

    for line in txt.split("\n"):

        if "-" in line:

            n, d = line.split("-", 1)

            out.append({
                "name": n.strip(),
                "desc": d.strip()
            })

    return out


# =========================================================
# PORTRAIT
# =========================================================
def generate_portrait(name, race, cls):

    try:

        styles = {

            "barbarian":
                "massive muscular warrior, fur armor, war paint",

            "fighter":
                "battle worn knight, steel armor, heroic stance",

            "rogue":
                "hooded assassin, daggers, shadows",

            "wizard":
                "arcane mage, glowing runes, magical aura",

            "cleric":
                "holy warrior, radiant divine light",

            "sorcerer":
                "wild magic, glowing eyes, magical energy"
        }

        prompt = f"""
        Epic fantasy portrait of {name},
        a {race} {cls}.

        {styles.get(cls.lower(), "fantasy adventurer")}

        Cinematic lighting,
        ultra detailed,
        realistic fantasy art,
        Dungeons and Dragons style,
        highly detailed face,
        4k digital painting,
        fantasy concept art.
        """

        img = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        return base64.b64decode(
            img.data[0].b64_json
        )

    except Exception as e:

        print("IMAGE ERROR:", e)

        return None


# =========================================================
# STAT GENERATION
# =========================================================
def auto_stats(cls):
    stats = {
        "STR": 8,
        "DEX": 8,
        "CON": 8,
        "INT": 8,
        "WIS": 8,
        "CHA": 8
    }
    points = 27

    order = CLASS_DATA.get(cls.lower(), {}).get("primary", ["STR", "DEX", "CON"])

    changed = True
    while points > 0 and changed:
        changed = False
        for stat in order:
            if stats[stat] < 15:
                next_score = stats[stat] + 1
                cost = POINT_COST[next_score] - POINT_COST[stats[stat]]  # ✅ Incremental cost
                if points >= cost:
                    stats[stat] = next_score
                    points -= cost
                    changed = True

    return stats


# =========================================================
# EQUIPMENT
# =========================================================
def equipment(cls):

    data = CLASS_DATA.get(cls.lower(), {})

    gear = [
        data.get("weapon", "Dagger"),
        data.get("armor", "Traveler Clothes"),
        "Backpack",
        "Torch",
        "Rations",
        "Rope",
        "Waterskin"
    ]

    return gear, random.randint(20, 150)


# =========================================================
# COMBAT
# =========================================================
def armor_class(cls, dex_mod):

    base = CLASS_DATA.get(
        cls.lower(),
        {}
    ).get(
        "ac_base",
        10
    )

    return base + dex_mod


def initiative(dex_mod):
    return dex_mod


# =========================================================
# PDF
# =========================================================
def make_pdf(c):

    buf = BytesIO()

    doc = SimpleDocTemplate(buf)

    styles = getSampleStyleSheet()

    elems = []

    elems.append(
        Paragraph(
            f"<b>{c['name']}</b>",
            styles["Title"]
        )
    )

    elems.append(
        Paragraph(
            f"{c['race']} {c['class']} Level {c['level']}",
            styles["Normal"]
        )
    )

    elems.append(Spacer(1, 10))

    # Stats Table
    data = [["Stat", "Score", "Modifier"]]

    for k, v in c["stats"].items():

        data.append([
            k,
            str(v),
            str(mod(v))
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
    ]))

    elems.append(table)

    elems.append(Spacer(1, 10))

    elems.append(
        Paragraph(
            f"HP: {c['hp']}",
            styles["Normal"]
        )
    )

    elems.append(
        Paragraph(
            f"Armor Class: {c['ac']}",
            styles["Normal"]
        )
    )

    elems.append(
        Paragraph(
            f"Initiative: {c['initiative']}",
            styles["Normal"]
        )
    )

    elems.append(
        Paragraph(
            "Equipment",
            styles["Heading2"]
        )
    )

    for g in c["gear"]:

        elems.append(
            Paragraph(g, styles["Normal"])
        )

    elems.append(
        Paragraph(
            "Backstory",
            styles["Heading2"]
        )
    )

    elems.append(
        Paragraph(
            c["story"],
            styles["BodyText"]
        )
    )

    doc.build(elems)

    buf.seek(0)

    return buf


# =========================================================
# NAV
# =========================================================
nav1, nav2 = st.columns(2)

with nav1:

    if st.button("🛠 Builder"):
        st.session_state.page = "builder"

with nav2:

    if st.button("🎴 Character Sheet"):
        st.session_state.page = "sheet"


# =========================================================
# BUILDER PAGE
# =========================================================
if st.session_state.page == "builder":

    st.title("🧙 AI D&D Character Creator")

    race = st.text_input("Race")
    cls = st.selectbox(
        "Class",
        [
            "Barbarian",
            "Fighter",
            "Rogue",
            "Wizard",
            "Cleric",
            "Sorcerer"
        ]
    )

    # Name Generator
    if st.button("🎲 Generate Name"):

        if race:

            st.session_state.name = generate_name(race)

    name = st.text_input(
        "Character Name",
        key="name"
    )

    level = st.slider(
        "Level",
        1,
        20,
        1
    )

    # Mode
    mode = st.radio(
        "Stat Generation",
        [
            "Auto Optimized",
            "Manual Point Buy"
        ]
    )

    manual_stats = {}
    total_cost = 0

    if mode == "Manual Point Buy":

        st.markdown("### Point Buy")

        for stat in [
            "STR",
            "DEX",
            "CON",
            "INT",
            "WIS",
            "CHA"
        ]:

            val = st.slider(
                stat,
                8,
                15,
                8,
                key=f"pb_{stat}"
            )

            manual_stats[stat] = val
            total_cost += POINT_COST[val]

        st.write(f"Points Used: {total_cost}/27")

        if total_cost > 27:
            st.error("Too many points!")

    # Generate Character
    if st.button("📜 Generate Character"):

        if not (name and race and cls):

            st.warning(
                "Fill in all fields."
            )

            st.stop()

        # Stats
        if mode == "Auto Optimized":

            stats = auto_stats(cls)

        else:

            if total_cost > 27:

                st.warning(
                    "Invalid point buy."
                )

                st.stop()

            stats = manual_stats

        # Derived
        dex_mod = mod(stats["DEX"])

        hp = (
            CLASS_DATA[cls.lower()]["hit_die"]
            * level
        ) + (mod(stats["CON"]) * level)

        ac = armor_class(
            cls,
            dex_mod
        )

        init = initiative(dex_mod)

        gear, gold = equipment(cls)

        # AI
        story = generate_backstory(
            name,
            race,
            cls
        )

        spells = generate_spells(cls)

        portrait = generate_portrait(
            name,
            race,
            cls
        )

        # Save Character
        st.session_state.character = {

            "name": name,
            "race": race,
            "class": cls,
            "level": level,

            "stats": stats,

            "hp": hp,
            "ac": ac,
            "initiative": init,

            "gear": gear,
            "gold": gold,

            "spells": spells,

            "story": story,

            "image": portrait,

            "prof_bonus":
                proficiency_bonus(level)
        }

        st.success(
            "Character Generated!"
        )


# =========================================================
# SHEET PAGE
# =========================================================
else:

    c = st.session_state.character

    if not c:

        st.warning(
            "Generate a character first."
        )

    else:

        st.markdown(f"""
        <div class="card">
            <div class="char-title">
                {c['name']}
            </div>

            <div>
                {c['race']} {c['class']}
                • Level {c['level']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        left, right = st.columns([1, 2])

        # Portrait
        with left:

            if c["image"]:

                st.image(
                    c["image"],
                    use_container_width=True
                )

        # Stats
        with right:

            st.markdown(
                '<div class="card">',
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="section-title">Stats</div>',
                unsafe_allow_html=True
            )

            cols = st.columns(6)

            i = 0

            for k, v in c["stats"].items():

                with cols[i]:

                    st.markdown(f"""
                    <div class="stat-box">
                        <b>{k}</b><br>
                        <h2>{v}</h2>
                        mod {mod(v)}
                    </div>
                    """, unsafe_allow_html=True)

                i += 1

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )

        # Combat
        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="section-title">Combat</div>',
            unsafe_allow_html=True
        )

        st.write(f"❤️ HP: {c['hp']}")
        st.write(f"🛡️ Armor Class: {c['ac']}")
        st.write(f"⚡ Initiative: {c['initiative']}")
        st.write(f"🎯 Proficiency Bonus: +{c['prof_bonus']}")

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

        # Equipment
        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="section-title">Equipment</div>',
            unsafe_allow_html=True
        )

        for item in c["gear"]:

            st.write(f"• {item}")

        st.markdown(
            f"<div class='gold'>💰 Gold: {c['gold']}</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

        # Spells
        if c["spells"]:

            st.markdown(
                '<div class="card">',
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="section-title">Spells</div>',
                unsafe_allow_html=True
            )

            for s in c["spells"]:

                st.write(
                    f"✨ {s['name']} — {s['desc']}"
                )

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )

        # Story
        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="section-title">Backstory</div>',
            unsafe_allow_html=True
        )

        st.write(c["story"])

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

        # PDF
        st.download_button(
            "📄 Download Character Sheet PDF",
            make_pdf(c),
            file_name=f"{c['name']}.pdf"
        )

import streamlit as st
from anthropic import Anthropic
import random
import base64
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
import json

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="AI D&D Character Creator",
    page_icon="🧙",
    layout="wide"
)

client = Anthropic(api_key=st.secrets.get("ANTHROPIC_API_KEY"))

# =========================================================
# SESSION STATE
# =========================================================
for key, default in {
    "page": "builder",
    "name": "",
    "character": None,
    "portrait_error": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# =========================================================
# STYLE
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@400;700&family=Cinzel:wght@400;600&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');

.stApp {
    background: linear-gradient(135deg, #0a0a0f 0%, #12101a 50%, #0d0a12 100%);
    color: #e8dcc8;
    font-family: 'Crimson Text', serif;
}

h1, h2, h3 { font-family: 'Cinzel', serif !important; }

.main-title {
    font-family: 'Cinzel Decorative', serif;
    font-size: 2.8rem;
    background: linear-gradient(135deg, #d4a843, #f5d67b, #c9883a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    letter-spacing: 0.05em;
    margin-bottom: 0.2em;
}

.card {
    background: linear-gradient(145deg, rgba(20,15,30,0.95), rgba(15,10,22,0.98));
    border: 1px solid rgba(201,164,76,0.4);
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 18px;
    box-shadow: 0 4px 30px rgba(0,0,0,0.6), inset 0 1px 0 rgba(201,164,76,0.15);
    position: relative;
    overflow: hidden;
}

.card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(201,164,76,0.6), transparent);
}

.char-title {
    font-family: 'Cinzel Decorative', serif;
    font-size: 2.2rem;
    background: linear-gradient(135deg, #f5d67b, #d4a843);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.section-title {
    font-family: 'Cinzel', serif;
    color: #c9a44c;
    font-size: 1.1rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 14px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(201,164,76,0.25);
}

.stat-box {
    background: linear-gradient(145deg, rgba(201,164,76,0.08), rgba(201,164,76,0.03));
    border: 1px solid rgba(201,164,76,0.35);
    border-radius: 10px;
    padding: 14px 8px;
    text-align: center;
    transition: all 0.2s ease;
}

.stat-box:hover {
    border-color: rgba(201,164,76,0.7);
    background: rgba(201,164,76,0.12);
}

.stat-name {
    font-family: 'Cinzel', serif;
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    color: #c9a44c;
    text-transform: uppercase;
}

.stat-score {
    font-family: 'Cinzel Decorative', serif;
    font-size: 2rem;
    color: #f5d67b;
    line-height: 1.1;
}

.stat-mod {
    font-size: 0.85rem;
    color: #a89070;
}

.combat-stat {
    background: rgba(201,164,76,0.06);
    border: 1px solid rgba(201,164,76,0.2);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.tag {
    display: inline-block;
    background: rgba(201,164,76,0.15);
    border: 1px solid rgba(201,164,76,0.3);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.8rem;
    color: #d4a843;
    font-family: 'Cinzel', serif;
    letter-spacing: 0.05em;
    margin: 3px;
}

.gold { color: #d4a843; font-weight: 600; }
.subtitle { color: #a89070; font-style: italic; font-size: 1.05rem; }
.spell-card {
    background: rgba(100,60,180,0.08);
    border-left: 2px solid rgba(140,80,220,0.5);
    padding: 8px 14px;
    margin-bottom: 8px;
    border-radius: 0 8px 8px 0;
}

.nav-btn {
    background: linear-gradient(135deg, rgba(201,164,76,0.15), rgba(201,164,76,0.05));
    border: 1px solid rgba(201,164,76,0.4);
    color: #d4a843;
    border-radius: 8px;
    font-family: 'Cinzel', serif;
    letter-spacing: 0.08em;
}

.npc-card {
    background: rgba(60,40,100,0.15);
    border: 1px solid rgba(140,100,200,0.3);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
}

.error-box {
    background: rgba(180,40,40,0.15);
    border: 1px solid rgba(200,60,60,0.4);
    border-radius: 8px;
    padding: 10px 16px;
    color: #e88;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# GAME DATA
# =========================================================
POINT_COST = {8:0, 9:1, 10:2, 11:3, 12:4, 13:5, 14:7, 15:9}
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

CLASS_DATA = {
    "Barbarian": {"hit_die":12,"primary":["STR","CON","DEX"],"armor":"Medium Armor","weapon":"Greataxe","ac_base":14,"spellcaster":False,
        "subclasses":["Path of the Berserker","Path of the Totem Warrior","Path of the Storm Herald","Path of the Ancestral Guardian"],
        "saves":["STR","CON"],"skill_options":["Athletics","Intimidation","Nature","Perception","Survival","Animal Handling"]},
    "Fighter":  {"hit_die":10,"primary":["STR","CON","DEX"],"armor":"Heavy Armor","weapon":"Longsword & Shield","ac_base":16,"spellcaster":False,
        "subclasses":["Battle Master","Champion","Eldritch Knight","Psi Warrior"],
        "saves":["STR","CON"],"skill_options":["Acrobatics","Athletics","History","Insight","Intimidation","Perception","Survival"]},
    "Rogue":    {"hit_die":8,"primary":["DEX","INT","CHA"],"armor":"Light Armor","weapon":"Rapier & Hand Crossbow","ac_base":14,"spellcaster":False,
        "subclasses":["Thief","Assassin","Arcane Trickster","Phantom"],
        "saves":["DEX","INT"],"skill_options":["Acrobatics","Athletics","Deception","Insight","Intimidation","Investigation","Perception","Performance","Persuasion","Sleight of Hand","Stealth"]},
    "Wizard":   {"hit_die":6,"primary":["INT","DEX","CON"],"armor":"Robes","weapon":"Quarterstaff","ac_base":12,"spellcaster":True,
        "subclasses":["School of Evocation","School of Illusion","School of Necromancy","Bladesinging"],
        "saves":["INT","WIS"],"skill_options":["Arcana","History","Insight","Investigation","Medicine","Religion"]},
    "Cleric":   {"hit_die":8,"primary":["WIS","CON","STR"],"armor":"Medium Armor","weapon":"Mace & Holy Symbol","ac_base":15,"spellcaster":True,
        "subclasses":["Life Domain","Light Domain","War Domain","Trickery Domain"],
        "saves":["WIS","CHA"],"skill_options":["History","Insight","Medicine","Persuasion","Religion"]},
    "Sorcerer": {"hit_die":6,"primary":["CHA","CON","DEX"],"armor":"Mystic Cloth","weapon":"Arcane Focus","ac_base":12,"spellcaster":True,
        "subclasses":["Wild Magic Surge","Draconic Bloodline","Storm Sorcery","Divine Soul"],
        "saves":["CON","CHA"],"skill_options":["Arcana","Deception","Insight","Intimidation","Persuasion","Religion"]},
    "Paladin":  {"hit_die":10,"primary":["STR","CHA","CON"],"armor":"Heavy Armor","weapon":"Longsword & Shield","ac_base":17,"spellcaster":True,
        "subclasses":["Oath of Devotion","Oath of Vengeance","Oath of the Ancients","Oathbreaker"],
        "saves":["WIS","CHA"],"skill_options":["Athletics","Insight","Intimidation","Medicine","Persuasion","Religion"]},
    "Ranger":   {"hit_die":10,"primary":["DEX","WIS","CON"],"armor":"Medium Armor","weapon":"Longbow & Shortsword","ac_base":15,"spellcaster":True,
        "subclasses":["Hunter","Beast Master","Gloom Stalker","Swarmkeeper"],
        "saves":["STR","DEX"],"skill_options":["Animal Handling","Athletics","Insight","Investigation","Nature","Perception","Stealth","Survival"]},
    "Druid":    {"hit_die":8,"primary":["WIS","CON","DEX"],"armor":"Hide Armor","weapon":"Quarterstaff","ac_base":13,"spellcaster":True,
        "subclasses":["Circle of the Moon","Circle of the Land","Circle of Stars","Circle of Spores"],
        "saves":["INT","WIS"],"skill_options":["Arcana","Animal Handling","Insight","Medicine","Nature","Perception","Religion","Survival"]},
    "Bard":     {"hit_die":8,"primary":["CHA","DEX","CON"],"armor":"Light Armor","weapon":"Rapier","ac_base":13,"spellcaster":True,
        "subclasses":["College of Lore","College of Valor","College of Glamour","College of Swords"],
        "saves":["DEX","CHA"],"skill_options":["Athletics","Acrobatics","Arcana","Deception","History","Insight","Intimidation","Investigation","Medicine","Nature","Perception","Performance","Persuasion","Religion","Sleight of Hand","Stealth","Survival"]},
    "Warlock":  {"hit_die":8,"primary":["CHA","CON","DEX"],"armor":"Light Armor","weapon":"Eldritch Blast","ac_base":13,"spellcaster":True,
        "subclasses":["The Fiend","The Great Old One","The Archfey","The Hexblade"],
        "saves":["WIS","CHA"],"skill_options":["Arcana","Deception","History","Intimidation","Investigation","Nature","Religion"]},
    "Monk":     {"hit_die":8,"primary":["DEX","WIS","CON"],"armor":"No Armor (Unarmored)","weapon":"Unarmed Strike","ac_base":14,"spellcaster":False,
        "subclasses":["Way of the Open Hand","Way of Shadow","Way of the Four Elements","Way of the Astral Self"],
        "saves":["STR","DEX"],"skill_options":["Acrobatics","Athletics","History","Insight","Religion","Stealth"]},
}

RACE_BONUSES = {
    "Human":        {"STR":1,"DEX":1,"CON":1,"INT":1,"WIS":1,"CHA":1},
    "Elf":          {"DEX":2,"INT":1},
    "Half-Elf":     {"CHA":2,"DEX":1,"WIS":1},
    "Dwarf":        {"CON":2,"WIS":1},
    "Halfling":     {"DEX":2,"CHA":1},
    "Gnome":        {"INT":2,"DEX":1},
    "Half-Orc":     {"STR":2,"CON":1},
    "Tiefling":     {"INT":1,"CHA":2},
    "Dragonborn":   {"STR":2,"CHA":1},
    "Aasimar":      {"WIS":1,"CHA":2},
    "Tabaxi":       {"DEX":2,"CHA":1},
    "Kenku":        {"DEX":2,"WIS":1},
    "Firbolg":      {"WIS":2,"STR":1},
    "Goliath":      {"STR":2,"CON":1},
    "Genasi (Fire)":{"CON":2,"INT":1},
    "Lizardfolk":   {"CON":2,"WIS":1},
    "Custom/Other": {},
}

FEATS = [
    "Alert","Lucky","Observant","Resilient","Tough","War Caster",
    "Magic Initiate","Sharpshooter","Great Weapon Master","Polearm Master",
    "Sentinel","Mobile","Crossbow Expert","Dual Wielder","Shield Master",
]

ASI_LEVELS = {4, 8, 12, 16, 19}

# =========================================================
# HELPERS
# =========================================================
def mod(score): return (score - 10) // 2
def mod_str(score): m = mod(score); return f"+{m}" if m >= 0 else str(m)
def proficiency_bonus(level): return 2 + ((level - 1) // 4)

def apply_racial_bonuses(base_stats, race):
    bonuses = RACE_BONUSES.get(race, {})
    return {k: v + bonuses.get(k, 0) for k, v in base_stats.items()}

def get_asi_count(level):
    return sum(1 for l in ASI_LEVELS if l <= level)

def hp_calc(cls, level, con_mod):
    hit_die = CLASS_DATA[cls]["hit_die"]
    return hit_die + (hit_die // 2 + 1) * (level - 1) + con_mod * level

def armor_class(cls, dex_mod):
    base = CLASS_DATA[cls]["ac_base"]
    if cls in ["Wizard","Sorcerer","Bard","Warlock"]:
        return base + dex_mod
    return base

def initiative(dex_mod): return dex_mod

def skill_modifier(stats, skill, prof_bonus, proficient_skills):
    skill_stat = {
        "Acrobatics":"DEX","Animal Handling":"WIS","Arcana":"INT","Athletics":"STR",
        "Deception":"CHA","History":"INT","Insight":"WIS","Intimidation":"CHA",
        "Investigation":"INT","Medicine":"WIS","Nature":"INT","Perception":"WIS",
        "Performance":"CHA","Persuasion":"CHA","Religion":"INT","Sleight of Hand":"DEX",
        "Stealth":"DEX","Survival":"WIS",
    }
    stat = skill_stat.get(skill, "STR")
    base = mod(stats[stat])
    return base + (prof_bonus if skill in proficient_skills else 0)

def equipment(cls):
    data = CLASS_DATA[cls]
    gear = [data["weapon"], data["armor"], "Backpack", "Torch x5", "Rations x10", "50ft Rope", "Waterskin", "Bedroll", "Tinderbox"]
    return gear, random.randint(50, 200)

# =========================================================
# STAT GENERATION
# =========================================================
def auto_stats(cls):
    stats = {s: 8 for s in ["STR","DEX","CON","INT","WIS","CHA"]}
    points = 27
    order = CLASS_DATA[cls]["primary"]
    all_stats = order + [s for s in ["STR","DEX","CON","INT","WIS","CHA"] if s not in order]
    changed = True
    while points > 0 and changed:
        changed = False
        for stat in all_stats:
            if stats[stat] < 15:
                cost = POINT_COST[stats[stat] + 1] - POINT_COST[stats[stat]]
                if points >= cost:
                    stats[stat] += 1
                    points -= cost
                    changed = True
    return stats

def standard_array_stats(cls):
    order = CLASS_DATA[cls]["primary"]
    all_stats = ["STR","DEX","CON","INT","WIS","CHA"]
    remaining = [s for s in all_stats if s not in order]
    assignment = {}
    sorted_array = sorted(STANDARD_ARRAY, reverse=True)
    for i, stat in enumerate(order):
        assignment[stat] = sorted_array[i]
    for i, stat in enumerate(remaining):
        assignment[stat] = sorted_array[len(order) + i]
    return assignment

def roll_stats():
    stats = {}
    for s in ["STR","DEX","CON","INT","WIS","CHA"]:
        rolls = [random.randint(1,6) for _ in range(4)]
        stats[s] = sum(sorted(rolls)[1:])
    return stats

def apply_asi(stats, asi_choices):
    result = dict(stats)
    for stat, inc in asi_choices.items():
        result[stat] = min(20, result.get(stat, 8) + inc)
    return result

# =========================================================
# AI FUNCTIONS (Claude)
# =========================================================
def claude(prompt, system="You are a creative D&D assistant. Be vivid and concise."):
    res = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system,
        messages=[{"role":"user","content":prompt}]
    )
    return res.content[0].text.strip()

@st.cache_data(show_spinner=False)
def generate_name(race, cls):
    return claude(f"Create ONE fantasy D&D name for a {race} {cls}. Return ONLY the name, nothing else.")

@st.cache_data(show_spinner=False)
def generate_backstory(name, race, cls, subclass):
    return claude(
        f"Write an immersive D&D backstory for {name}, a {race} {subclass} {cls}.\n"
        "Include: origin, key motivation, a defining flaw, vivid personality trait, and a compelling plot hook.\n"
        "Write 3-4 paragraphs. Be specific and evocative."
    )

@st.cache_data(show_spinner=False)
def generate_personality(name, race, cls):
    prompt = (
        f"For a D&D character: {name}, {race} {cls}.\n"
        "Return ONLY a JSON object with keys: trait, ideal, bond, flaw. Each value is one vivid sentence.\n"
        "No markdown, no backticks, just raw JSON."
    )
    raw = claude(prompt)
    try:
        return json.loads(raw.strip().strip("```json").strip("```"))
    except:
        return {"trait":"Brave and reckless","ideal":"Freedom above all","bond":"A mentor long lost","flaw":"Cannot resist a challenge"}

@st.cache_data(show_spinner=False)
def generate_npcs(name, race, cls, backstory_snippet):
    prompt = (
        f"For D&D character {name} ({race} {cls}), create 3 named NPCs from their backstory.\n"
        "Return ONLY a JSON array of objects with keys: name, role, relationship, secret.\n"
        "No markdown, no backticks, just raw JSON array."
    )
    raw = claude(prompt)
    try:
        clean = raw.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except:
        return [{"name":"Unknown Ally","role":"Mentor","relationship":"Trusted friend","secret":"Harbors a dark past"}]

@st.cache_data(show_spinner=False)
def generate_quest_hook(name, race, cls, subclass):
    return claude(
        f"Write a single specific adventure quest hook (2-3 sentences) for {name}, a {race} {subclass} {cls}. "
        "Make it unique, personal, and immediately actionable. Include a named location and antagonist."
    )

@st.cache_data(show_spinner=False)
def generate_spells(cls, subclass, level):
    if not CLASS_DATA[cls]["spellcaster"]:
        return []
    n = min(3 + level // 2, 10)
    prompt = (
        f"Generate {n} D&D 5e spells for a level {level} {subclass} {cls}.\n"
        "Include cantrips and leveled spells appropriate for their level.\n"
        "Return ONLY a JSON array of objects with keys: name, level (0=cantrip), school, description (one sentence).\n"
        "No markdown, no backticks, just raw JSON array."
    )
    raw = claude(prompt)
    try:
        clean = raw.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except:
        return [{"name":"Magic Missile","level":1,"school":"Evocation","description":"Darts of force that always hit."}]

# =========================================================
# PDF EXPORT
# =========================================================
def make_pdf(c):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    elems = []

    elems.append(Paragraph(f"<b>{c['name']}</b>", styles["Title"]))
    elems.append(Paragraph(f"{c['race']} {c['subclass']} {c['class']} • Level {c['level']}", styles["Normal"]))
    elems.append(Spacer(1, 12))

    # Stats
    elems.append(Paragraph("Ability Scores", styles["Heading2"]))
    data = [["Stat","Score","Modifier","Save"]]
    saves = CLASS_DATA[c["class"]]["saves"]
    pb = c["prof_bonus"]
    for k, v in c["stats"].items():
        m = mod(v)
        save = m + (pb if k in saves else 0)
        data.append([k, str(v), mod_str(v), mod_str(save)])
    t = Table(data, colWidths=[80,60,80,60])
    t.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("BACKGROUND",(0,0),(-1,0),colors.Color(0.15,0.1,0.25)),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
    ]))
    elems.append(t)
    elems.append(Spacer(1,10))

    # Combat
    elems.append(Paragraph("Combat", styles["Heading2"]))
    elems.append(Paragraph(f"HP: {c['hp']}  |  AC: {c['ac']}  |  Initiative: {mod_str(c['initiative'])}  |  Proficiency: +{c['prof_bonus']}", styles["Normal"]))
    elems.append(Spacer(1,8))

    # Personality
    if c.get("personality"):
        elems.append(Paragraph("Personality", styles["Heading2"]))
        p = c["personality"]
        elems.append(Paragraph(f"<b>Trait:</b> {p.get('trait','')}", styles["Normal"]))
        elems.append(Paragraph(f"<b>Ideal:</b> {p.get('ideal','')}", styles["Normal"]))
        elems.append(Paragraph(f"<b>Bond:</b> {p.get('bond','')}", styles["Normal"]))
        elems.append(Paragraph(f"<b>Flaw:</b> {p.get('flaw','')}", styles["Normal"]))
        elems.append(Spacer(1,8))

    # Equipment
    elems.append(Paragraph("Equipment", styles["Heading2"]))
    for item in c["gear"]:
        elems.append(Paragraph(f"• {item}", styles["Normal"]))
    elems.append(Paragraph(f"Gold: {c['gold']} gp", styles["Normal"]))
    elems.append(Spacer(1,8))

    # Spells
    if c.get("spells"):
        elems.append(Paragraph("Spells", styles["Heading2"]))
        for s in c["spells"]:
            lvl = "Cantrip" if s.get("level")==0 else f"Level {s.get('level','?')}"
            elems.append(Paragraph(f"<b>{s['name']}</b> ({lvl}, {s.get('school','')}) — {s.get('description','')}", styles["Normal"]))
        elems.append(Spacer(1,8))

    # NPCs
    if c.get("npcs"):
        elems.append(Paragraph("Notable NPCs", styles["Heading2"]))
        for npc in c["npcs"]:
            elems.append(Paragraph(f"<b>{npc['name']}</b> ({npc.get('role','')}) — {npc.get('relationship','')}", styles["Normal"]))
            elems.append(Paragraph(f"Secret: {npc.get('secret','')}", styles["Normal"]))
        elems.append(Spacer(1,8))

    # Backstory
    elems.append(Paragraph("Backstory", styles["Heading2"]))
    elems.append(Paragraph(c["story"], styles["BodyText"]))

    if c.get("quest_hook"):
        elems.append(Spacer(1,8))
        elems.append(Paragraph("Quest Hook", styles["Heading2"]))
        elems.append(Paragraph(c["quest_hook"], styles["BodyText"]))

    doc.build(elems)
    buf.seek(0)
    return buf

# =========================================================
# JSON EXPORT / IMPORT
# =========================================================
def export_character(c):
    exportable = {k: v for k, v in c.items() if k != "image"}
    return json.dumps(exportable, indent=2)

# =========================================================
# NAV
# =========================================================
st.markdown('<div class="main-title">⚔️ AI D&D Character Creator</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,1,1])
with col1:
    if st.button("🛠️ Builder", use_container_width=True):
        st.session_state.page = "builder"
with col2:
    if st.button("🎴 Character Sheet", use_container_width=True):
        st.session_state.page = "sheet"
with col3:
    if st.button("📖 Import Character", use_container_width=True):
        st.session_state.page = "import"

st.markdown("---")

# =========================================================
# IMPORT PAGE
# =========================================================
if st.session_state.page == "import":
    st.markdown("### Import Character (JSON)")
    uploaded = st.file_uploader("Upload character JSON", type=["json"])
    raw_json = st.text_area("Or paste JSON here")
    if st.button("Load Character"):
        try:
            data = json.loads(uploaded.read() if uploaded else raw_json)
            st.session_state.character = data
            st.session_state.page = "sheet"
            st.success("Character loaded!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to parse JSON: {e}")

# =========================================================
# BUILDER PAGE
# =========================================================
elif st.session_state.page == "builder":

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">⚔️ Character Basics</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            race = st.selectbox("Race", list(RACE_BONUSES.keys()))
            cls  = st.selectbox("Class", list(CLASS_DATA.keys()))
        with col2:
            subclass = st.selectbox("Subclass", CLASS_DATA[cls]["subclasses"])
            level    = st.slider("Level", 1, 20, 1)

        # Name
        name_col, btn_col = st.columns([3,1])
        with btn_col:
            if st.button("🎲 Generate Name"):
                with st.spinner("Conjuring name..."):
                    st.session_state.name = generate_name(race, cls)
        with name_col:
            name = st.text_input("Character Name", key="name")

        st.markdown('</div>', unsafe_allow_html=True)

    # ---- STATS ----
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🎲 Ability Scores</div>', unsafe_allow_html=True)

        mode = st.radio("Stat Generation Method", ["Auto Optimized","Standard Array","Manual Point Buy","Dice Roll (4d6 drop lowest)"], horizontal=True)

        manual_stats = {}
        total_cost   = 0
        rolled_stats = {}

        if mode == "Manual Point Buy":
            st.caption("Budget: 27 points")
            cols = st.columns(6)
            for i, stat in enumerate(["STR","DEX","CON","INT","WIS","CHA"]):
                with cols[i]:
                    val = st.slider(stat, 8, 15, 8, key=f"pb_{stat}")
                    manual_stats[stat] = val
                    total_cost += POINT_COST[val]
            color = "🔴" if total_cost > 27 else "🟢"
            st.write(f"{color} Points Used: **{total_cost}/27**")

        elif mode == "Dice Roll (4d6 drop lowest)":
            if st.button("🎲 Roll Stats"):
                st.session_state["rolled"] = roll_stats()
            if "rolled" in st.session_state:
                rolled_stats = st.session_state["rolled"]
                cols = st.columns(6)
                for i, (stat, val) in enumerate(rolled_stats.items()):
                    with cols[i]:
                        st.metric(stat, val, mod_str(val))

        elif mode == "Standard Array":
            preview = standard_array_stats(cls)
            cols = st.columns(6)
            for i, (stat, val) in enumerate(preview.items()):
                with cols[i]:
                    st.metric(stat, val, f"→ {val + RACE_BONUSES.get(race,{}).get(stat,0)} w/ race")

        # ---- ASI ----
        asi_count = get_asi_count(level)
        asi_choices = {}
        if asi_count > 0:
            st.markdown("---")
            st.markdown(f'<div class="section-title">📈 Ability Score Improvements ({asi_count} available)</div>', unsafe_allow_html=True)
            st.caption("Each ASI gives +2 to one stat or +1 to two stats. Or choose a feat.")

            for i in range(asi_count):
                with st.expander(f"ASI #{i+1}"):
                    choice = st.radio(f"ASI {i+1} type", ["+2 to one stat","+1 to two stats","Take a Feat"], key=f"asi_type_{i}", horizontal=True)
                    if choice == "+2 to one stat":
                        s = st.selectbox("Stat", ["STR","DEX","CON","INT","WIS","CHA"], key=f"asi_s1_{i}")
                        asi_choices[s] = asi_choices.get(s, 0) + 2
                    elif choice == "+1 to two stats":
                        s1 = st.selectbox("First stat", ["STR","DEX","CON","INT","WIS","CHA"], key=f"asi_s2a_{i}")
                        s2 = st.selectbox("Second stat", ["STR","DEX","CON","INT","WIS","CHA"], key=f"asi_s2b_{i}", index=1)
                        asi_choices[s1] = asi_choices.get(s1, 0) + 1
                        asi_choices[s2] = asi_choices.get(s2, 0) + 1
                    else:
                        feat = st.selectbox("Feat", FEATS, key=f"feat_{i}")
                        if "feats" not in asi_choices:
                            asi_choices["feats"] = []
                        if isinstance(asi_choices.get("feats"), list):
                            asi_choices["feats"].append(feat)

        st.markdown('</div>', unsafe_allow_html=True)

    # ---- SKILLS ----
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🎓 Proficient Skills</div>', unsafe_allow_html=True)
        skill_pool = CLASS_DATA[cls]["skill_options"]
        max_skills = 4 if cls in ["Rogue","Bard"] else 2
        chosen_skills = st.multiselect(f"Choose up to {max_skills} skills", skill_pool, max_selections=max_skills)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- GENERATE ----
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📜 Generate Character", use_container_width=True, type="primary"):
        if not (name and race and cls):
            st.warning("Fill in all fields.")
            st.stop()
        if mode == "Manual Point Buy" and total_cost > 27:
            st.warning("Point buy exceeds 27 points.")
            st.stop()

        # Resolve base stats
        if mode == "Auto Optimized":
            base = auto_stats(cls)
        elif mode == "Standard Array":
            base = standard_array_stats(cls)
        elif mode == "Manual Point Buy":
            base = manual_stats
        else:
            base = rolled_stats if rolled_stats else auto_stats(cls)

        # Apply ASIs then racial bonuses
        feats_chosen = asi_choices.pop("feats", [])
        base = apply_asi(base, asi_choices)
        stats = apply_racial_bonuses(base, race)

        dex_mod = mod(stats["DEX"])
        con_mod = mod(stats["CON"])
        hp      = hp_calc(cls, level, con_mod)
        ac      = armor_class(cls, dex_mod)
        init    = initiative(dex_mod)
        gear, gold = equipment(cls)
        pb      = proficiency_bonus(level)

        with st.spinner("✨ Generating your character..."):
            story       = generate_backstory(name, race, cls, subclass)
            personality = generate_personality(name, race, cls)
            npcs        = generate_npcs(name, race, cls, story[:200])
            quest_hook  = generate_quest_hook(name, race, cls, subclass)
            spells      = generate_spells(cls, subclass, level)

        st.session_state.character = {
            "name": name, "race": race, "class": cls,
            "subclass": subclass, "level": level,
            "stats": stats, "hp": hp, "ac": ac,
            "initiative": init, "gear": gear, "gold": gold,
            "spells": spells, "story": story,
            "personality": personality, "npcs": npcs,
            "quest_hook": quest_hook, "image": None,
            "prof_bonus": pb, "chosen_skills": chosen_skills,
            "feats": feats_chosen,
        }

        st.success("✅ Character generated! Switch to the Character Sheet tab.")

# =========================================================
# SHEET PAGE
# =========================================================
elif st.session_state.page == "sheet":
    c = st.session_state.character
    if not c:
        st.warning("Generate a character first.")
        st.stop()

    # Header
    st.markdown(f"""
    <div class="card">
        <div class="char-title">{c['name']}</div>
        <div class="subtitle">{c['race']} • {c['subclass']} {c['class']} • Level {c['level']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tabs = st.tabs(["📊 Stats & Combat","🎒 Equipment","✨ Spells","🧠 Personality","📜 Backstory","👥 NPCs","⚔️ Quest Hook","📤 Export"])

    # ---- TAB 1: Stats & Combat ----
    with tabs[0]:
        pb = c["prof_bonus"]
        saves = CLASS_DATA[c["class"]]["saves"]

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Ability Scores</div>', unsafe_allow_html=True)
        cols = st.columns(6)
        for i, (stat, val) in enumerate(c["stats"].items()):
            with cols[i]:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-name">{stat}</div>
                    <div class="stat-score">{val}</div>
                    <div class="stat-mod">{mod_str(val)}</div>
                    {'<div class="gold">✦ Save</div>' if stat in saves else ''}
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Combat Stats</div>', unsafe_allow_html=True)
            for label, val in [
                ("❤️ Hit Points", c["hp"]),
                ("🛡️ Armor Class", c["ac"]),
                (f"⚡ Initiative", mod_str(c["initiative"])),
                (f"🎯 Proficiency Bonus", f"+{pb}"),
                ("🎲 Hit Die", f"d{CLASS_DATA[c['class']]['hit_die']}"),
            ]:
                st.markdown(f"""
                <div class="combat-stat">
                    <span>{label}</span>
                    <span class="gold"><b>{val}</b></span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Skills</div>', unsafe_allow_html=True)
            all_skills = ["Acrobatics","Animal Handling","Arcana","Athletics","Deception",
                          "History","Insight","Intimidation","Investigation","Medicine",
                          "Nature","Perception","Performance","Persuasion","Religion",
                          "Sleight of Hand","Stealth","Survival"]
            proficient = c.get("chosen_skills", [])
            for skill in all_skills:
                m = skill_modifier(c["stats"], skill, pb, proficient)
                star = "⭐" if skill in proficient else "  "
                st.markdown(f"<div style='display:flex;justify-content:space-between;padding:2px 0;'><span>{star} {skill}</span><span class='gold'>{mod_str(m)}</span></div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if c.get("feats"):
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Feats</div>', unsafe_allow_html=True)
            for feat in c["feats"]:
                st.markdown(f'<span class="tag">⭐ {feat}</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ---- TAB 2: Equipment ----
    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Gear & Equipment</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        items = c["gear"]
        for i, item in enumerate(items):
            (col1 if i % 2 == 0 else col2).markdown(f"• {item}")
        st.markdown(f"<br><div class='gold'>💰 Starting Gold: {c['gold']} gp</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- TAB 3: Spells ----
    with tabs[2]:
        if not c.get("spells"):
            st.info(f"{c['class']}s don't have spells (or none were generated).")
        else:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Spell List</div>', unsafe_allow_html=True)
            cantrips = [s for s in c["spells"] if s.get("level") == 0]
            leveled  = [s for s in c["spells"] if s.get("level", 0) > 0]
            if cantrips:
                st.markdown("**Cantrips**")
                for s in cantrips:
                    st.markdown(f"""<div class="spell-card"><b>{s['name']}</b> <span style='color:#a080d0;font-size:0.85em;'>({s.get('school','')})</span><br><span style='color:#c8b8a0;'>{s.get('description','')}</span></div>""", unsafe_allow_html=True)
            if leveled:
                st.markdown("**Leveled Spells**")
                for s in sorted(leveled, key=lambda x: x.get("level",1)):
                    st.markdown(f"""<div class="spell-card"><b>{s['name']}</b> <span style='color:#a080d0;font-size:0.85em;'>Level {s.get('level','?')} {s.get('school','')}</span><br><span style='color:#c8b8a0;'>{s.get('description','')}</span></div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ---- TAB 4: Personality ----
    with tabs[3]:
        p = c.get("personality", {})
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Personality Profile</div>', unsafe_allow_html=True)
        for icon, key, label in [("💬","trait","Personality Trait"),("⚡","ideal","Ideal"),("🔗","bond","Bond"),("💔","flaw","Flaw")]:
            st.markdown(f"""
            <div style='margin-bottom:14px;'>
                <div class='section-title' style='font-size:0.85rem;margin-bottom:4px;'>{icon} {label}</div>
                <div style='color:#e8dcc8;font-style:italic;'>{p.get(key,'...')}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- TAB 5: Backstory ----
    with tabs[4]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Backstory</div>', unsafe_allow_html=True)
        st.markdown(f"<div style='line-height:1.8;color:#e8dcc8;'>{c['story']}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- TAB 6: NPCs ----
    with tabs[5]:
        npcs = c.get("npcs", [])
        if not npcs:
            st.info("No NPCs generated.")
        else:
            for npc in npcs:
                st.markdown(f"""
                <div class="npc-card">
                    <div style='font-family:Cinzel,serif;color:#c9a44c;font-size:1.05rem;'>{npc.get('name','Unknown')}</div>
                    <div class='subtitle'>{npc.get('role','')} — {npc.get('relationship','')}</div>
                    <div style='color:#a89070;margin-top:6px;font-style:italic;'>🔒 Secret: {npc.get('secret','')}</div>
                </div>
                """, unsafe_allow_html=True)

    # ---- TAB 7: Quest Hook ----
    with tabs[6]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">⚔️ Your Adventure Begins...</div>', unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:1.1rem;line-height:1.9;color:#e8dcc8;font-style:italic;'>{c.get('quest_hook','No quest hook generated.')}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- TAB 8: Export ----
    with tabs[7]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Export & Share</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📄 Download PDF Sheet",
                make_pdf(c),
                file_name=f"{c['name'].replace(' ','_')}_character_sheet.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with col2:
            st.download_button(
                "💾 Download JSON",
                export_character(c),
                file_name=f"{c['name'].replace(' ','_')}.json",
                mime="application/json",
                use_container_width=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

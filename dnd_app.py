import streamlit as st
import anthropic
import base64
import random
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="AI D&D Character Creator", page_icon="🧙", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(rgba(0,0,0,.80), rgba(0,0,0,.88)),
        url("https://images.unsplash.com/photo-1511512578047-dfb367046420");
    background-size: cover;
    background-attachment: fixed;
    color: white;
}
.card {
    background: rgba(10,10,10,.82);
    border: 2px solid #c9a44c;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 18px;
    box-shadow: 0 0 15px rgba(0,0,0,.5);
}
.char-title { color: #f5d67b; font-size: 36px; font-weight: bold; }
.section-title { color: #f5d67b; font-size: 22px; font-weight: bold; margin-bottom: 10px; }
.stat-box {
    background: rgba(255,255,255,.06);
    border: 1px solid #c9a44c;
    border-radius: 12px;
    padding: 14px;
    text-align: center;
}
.gold { color: gold; font-weight: bold; }
.class-pill {
    display: inline-block;
    background: rgba(201,164,76,.25);
    border: 1px solid #c9a44c;
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 13px;
    margin: 2px 4px;
    color: #f5d67b;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────

POINT_COST = {8:0, 9:1, 10:2, 11:3, 12:4, 13:5, 14:7, 15:9}

ALL_CLASSES = [
    "Barbarian","Bard","Cleric","Druid","Fighter",
    "Monk","Paladin","Ranger","Rogue","Sorcerer","Warlock","Wizard"
]

CLASS_DATA = {
    "barbarian": {"hd":12, "pri":["STR","CON","DEX"], "armor":"Medium Armor", "weapon":"Greataxe",       "ac":14, "cast":False},
    "bard":      {"hd":8,  "pri":["CHA","DEX","CON"], "armor":"Light Armor",  "weapon":"Rapier",         "ac":13, "cast":True},
    "cleric":    {"hd":8,  "pri":["WIS","CON","STR"], "armor":"Medium Armor + Shield","weapon":"Mace",   "ac":15, "cast":True},
    "druid":     {"hd":8,  "pri":["WIS","CON","DEX"], "armor":"Medium Armor", "weapon":"Quarterstaff",   "ac":14, "cast":True},
    "fighter":   {"hd":10, "pri":["STR","CON","DEX"], "armor":"Heavy Armor",  "weapon":"Longsword + Shield","ac":16,"cast":False},
    "monk":      {"hd":8,  "pri":["DEX","WIS","CON"], "armor":"Unarmored",    "weapon":"Shortsword",     "ac":14, "cast":False},
    "paladin":   {"hd":10, "pri":["STR","CHA","CON"], "armor":"Heavy Armor",  "weapon":"Longsword + Shield","ac":17,"cast":True},
    "ranger":    {"hd":10, "pri":["DEX","WIS","CON"], "armor":"Medium Armor", "weapon":"Longbow",        "ac":14, "cast":True},
    "rogue":     {"hd":8,  "pri":["DEX","INT","CHA"], "armor":"Light Armor",  "weapon":"Daggers",        "ac":14, "cast":False},
    "sorcerer":  {"hd":6,  "pri":["CHA","CON","DEX"], "armor":"Robes",        "weapon":"Arcane Focus",   "ac":12, "cast":True},
    "warlock":   {"hd":8,  "pri":["CHA","CON","DEX"], "armor":"Light Armor",  "weapon":"Pact Weapon",    "ac":13, "cast":True},
    "wizard":    {"hd":6,  "pri":["INT","DEX","CON"], "armor":"Robes",        "weapon":"Quarterstaff",   "ac":12, "cast":True},
}

STATS = ["STR","DEX","CON","INT","WIS","CHA"]

ALIGNMENTS = [
    "Lawful Good","Neutral Good","Chaotic Good",
    "Lawful Neutral","True Neutral","Chaotic Neutral",
    "Lawful Evil","Neutral Evil","Chaotic Evil"
]

# ── Session state ──────────────────────────────────────────────────────────────

for k,v in {
    "page":"builder",
    "name":"",
    "character":None,
    "classes":[{"cls":"Fighter","level":1}],
    "portrait_bytes":None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_client():
    key = st.secrets.get("ANTHROPIC_API_KEY","")
    if not key:
        st.error("Add ANTHROPIC_API_KEY to your Streamlit secrets.")
        st.stop()
    return anthropic.Anthropic(api_key=key)

def stat_mod(score):
    return (score - 10) // 2

def prof_bonus(total_level):
    return 2 + ((total_level - 1) // 4)

def total_levels():
    return sum(c["level"] for c in st.session_state.classes)

def auto_stats(class_names):
    pri = []
    for c in class_names:
        for s in CLASS_DATA.get(c.lower(), {}).get("pri", []):
            if s not in pri:
                pri.append(s)
    order = pri + [s for s in STATS if s not in pri]
    stats = {s: 8 for s in STATS}
    points = 27
    changed = True
    while points > 0 and changed:
        changed = False
        for stat in order:
            if stats[stat] < 15:
                nxt = stats[stat] + 1
                cost = POINT_COST[nxt]
                if points >= cost:
                    stats[stat] = nxt
                    points -= cost
                    changed = True
    return stats

def get_equipment(class_names):
    gear = {"Backpack","Torch","Rations","Rope","Waterskin"}
    for c in class_names:
        d = CLASS_DATA.get(c.lower(), {})
        if d.get("weapon"): gear.add(d["weapon"])
        if d.get("armor"):  gear.add(d["armor"])
    return sorted(gear)

def best_ac(class_names, dex_mod):
    ac = 10 + dex_mod
    for c in class_names:
        d = CLASS_DATA.get(c.lower(), {})
        candidate = d.get("ac", 10) + dex_mod
        if candidate > ac:
            ac = candidate
    return ac

def calc_hp(class_names, levels, con_mod):
    hp = 0
    for cls, lvl in zip(class_names, levels):
        hd = CLASS_DATA.get(cls.lower(), {}).get("hd", 8)
        hp += hd * lvl
    hp += con_mod * sum(levels)
    return max(hp, 1)

# ── AI functions ───────────────────────────────────────────────────────────────

def generate_name(race):
    client = get_client()
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        messages=[{"role":"user","content":f"Create ONE fantasy D&D name for a {race}. Return only the name."}]
    )
    return msg.content[0].text.strip().split("\n")[0].strip()

def generate_backstory(name, race, background, alignment, class_desc):
    client = get_client()
    bg_note = f"Background: {background}\n" if background else ""
    prompt = (
        f"Write an immersive D&D backstory for:\n"
        f"Name: {name}\nRace: {race}\n{bg_note}"
        f"Alignment: {alignment}\nClasses: {class_desc}\n\n"
        f"Weave the multiclass combination naturally into the narrative. "
        f"Include: origin, how they came to train in multiple disciplines, "
        f"motivation, a flaw, a personality trait, and a plot hook. 3–4 paragraphs."
    )
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system="You are a creative D&D storyteller. Write vivid, specific backstories.",
        messages=[{"role":"user","content":prompt}]
    )
    return msg.content[0].text

def generate_spells(caster_entries):
    if not caster_entries:
        return []
    client = get_client()
    caster_desc = " / ".join(f"{e['cls']} (level {e['level']})" for e in caster_entries)
    prompt = (
        f"List 5 D&D 5e spells for a {caster_desc} character. "
        f"Pick spells appropriate to their class mix and levels. "
        f"Format each line exactly as:\nSpell Name [ClassName] - one sentence description\n"
        f"Return only those 5 lines, nothing else."
    )
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        system="You are a D&D 5e expert. Return only the list.",
        messages=[{"role":"user","content":prompt}]
    )
    spells = []
    for line in msg.content[0].text.strip().split("\n"):
        if " - " in line:
            import re
            m = re.match(r"^(.+?)\s*\[(.+?)\]\s*-\s*(.+)$", line)
            if m:
                spells.append({"name":m.group(1).strip(),"src":m.group(2).strip(),"desc":m.group(3).strip()})
            else:
                parts = line.split(" - ", 1)
                spells.append({"name":parts[0].strip(),"src":"","desc":parts[1].strip()})
    return spells[:5]

def generate_portrait(name, race, class_names, alignment):
    client = get_client()
    # Step 1: write a portrait prompt
    cls_str = " / ".join(class_names)
    prompt_msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=120,
        system="You write vivid, concise image prompts for fantasy character portraits. Return only the prompt, no preamble.",
        messages=[{"role":"user","content":(
            f"Write a concise image-generation prompt (under 70 words) for a fantasy portrait of:\n"
            f"Name: {name}, Race: {race}, Classes: {cls_str}, Alignment: {alignment}\n"
            f"Describe appearance, distinctive features blending class aesthetics, equipment, and mood. "
            f"Cinematic fantasy art style. No text in image."
        )}]
    )
    portrait_prompt = prompt_msg.content[0].text.strip()

    # Step 2: generate image
    img_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role":"user","content":[
            {"type":"text","text":(
                f"Generate a detailed fantasy RPG character portrait. "
                f"{portrait_prompt} "
                f"Square format, waist-up or bust shot, dramatic cinematic lighting, "
                f"highly detailed fantasy concept art style."
            )}
        ]}]
    )
    for block in img_response.content:
        if block.type == "image":
            return base64.b64decode(block.source.data)
    return None

# ── PDF export ─────────────────────────────────────────────────────────────────

def make_pdf(c):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf)
    styles = getSampleStyleSheet()
    elems = []

    elems.append(Paragraph(f"<b>{c['name']}</b>", styles["Title"]))
    cls_line = "  |  ".join(f"{e['cls']} {e['level']}" for e in c["classes"])
    elems.append(Paragraph(f"{c['race']} — {cls_line} — Level {c['total_level']}", styles["Normal"]))
    elems.append(Paragraph(f"{c['alignment']}  •  {c.get('background','')}", styles["Normal"]))
    elems.append(Spacer(1, 10))

    # Stats table
    data = [["Stat","Score","Modifier"]]
    for k,v in c["stats"].items():
        m = stat_mod(v)
        data.append([k, str(v), f"{'+' if m>=0 else ''}{m}"])
    t = Table(data)
    t.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
    ]))
    elems.append(t)
    elems.append(Spacer(1,10))

    elems.append(Paragraph(f"HP: {c['hp']}   |   AC: {c['ac']}   |   Initiative: {stat_mod(c['stats']['DEX']):+}   |   Proficiency: +{c['prof_bonus']}", styles["Normal"]))
    elems.append(Spacer(1,10))

    if c.get("portrait_bytes"):
        from reportlab.platypus import Image as RLImage
        from PIL import Image as PILImage
        img = PILImage.open(BytesIO(c["portrait_bytes"]))
        img_buf = BytesIO()
        img.save(img_buf, format="PNG")
        img_buf.seek(0)
        elems.append(RLImage(img_buf, width=200, height=200))
        elems.append(Spacer(1,10))

    elems.append(Paragraph("Equipment", styles["Heading2"]))
    for g in c["gear"]:
        elems.append(Paragraph(f"• {g}", styles["Normal"]))
    elems.append(Paragraph(f"Gold: {c['gold']} gp", styles["Normal"]))
    elems.append(Spacer(1,10))

    if c.get("spells"):
        elems.append(Paragraph("Spells", styles["Heading2"]))
        for s in c["spells"]:
            src = f" [{s['src']}]" if s.get("src") else ""
            elems.append(Paragraph(f"• {s['name']}{src} — {s['desc']}", styles["Normal"]))
        elems.append(Spacer(1,10))

    elems.append(Paragraph("Backstory", styles["Heading2"]))
    for para in c["story"].split("\n\n"):
        if para.strip():
            elems.append(Paragraph(para.strip(), styles["BodyText"]))
            elems.append(Spacer(1,6))

    doc.build(elems)
    buf.seek(0)
    return buf

# ── Nav ────────────────────────────────────────────────────────────────────────

col1, col2 = st.columns(2)
with col1:
    if st.button("🛠️ Builder", use_container_width=True):
        st.session_state.page = "builder"
with col2:
    if st.button("🎴 Character Sheet", use_container_width=True):
        st.session_state.page = "sheet"

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# BUILDER PAGE
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state.page == "builder":
    st.title("🧙 AI D&D Character Creator")
    st.caption("Multiclass support · AI backstory · AI portrait · PDF export")

    # ── Identity ──
    st.markdown('<div class="card"><div class="section-title">Identity</div>', unsafe_allow_html=True)
    col_r, col_b = st.columns(2)
    with col_r:
        race = st.text_input("Race", placeholder="e.g. Half-Elf, Tiefling, Dwarf…")
    with col_b:
        background = st.text_input("Background", placeholder="e.g. Soldier, Sage, Criminal…")

    alignment = st.selectbox("Alignment", ALIGNMENTS, index=4)

    col_name, col_btn = st.columns([3,1])
    with col_name:
        name = st.text_input("Character Name", value=st.session_state.name, placeholder="Enter or generate a name…")
        st.session_state.name = name
    with col_btn:
        st.write("")
        st.write("")
        if st.button("🎲 Generate Name"):
            if race:
                with st.spinner("Generating name…"):
                    st.session_state.name = generate_name(race)
                st.rerun()
            else:
                st.warning("Enter a race first.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Classes ──
    st.markdown('<div class="card"><div class="section-title">Classes</div>', unsafe_allow_html=True)

    tot = total_levels()
    st.caption(f"Total levels: **{tot} / 20**" + (" ⚠️ Over limit!" if tot > 20 else ""))

    for i, entry in enumerate(st.session_state.classes):
        used = [e["cls"] for j,e in enumerate(st.session_state.classes) if j != i]
        available = [c for c in ALL_CLASSES if c not in used]
        c1, c2, c3 = st.columns([3, 1, 0.4])
        with c1:
            idx = available.index(entry["cls"]) if entry["cls"] in available else 0
            new_cls = st.selectbox(f"Class {i+1}", available, index=idx, key=f"cls_{i}", label_visibility="collapsed")
            st.session_state.classes[i]["cls"] = new_cls
        with c2:
            others = sum(e["level"] for j,e in enumerate(st.session_state.classes) if j != i)
            max_lvl = max(1, 20 - others)
            new_lvl = st.number_input("Level", min_value=1, max_value=max_lvl,
                                       value=min(entry["level"], max_lvl),
                                       key=f"lvl_{i}", label_visibility="collapsed")
            st.session_state.classes[i]["level"] = int(new_lvl)
        with c3:
            st.write("")
            if len(st.session_state.classes) > 1:
                if st.button("✕", key=f"rem_{i}"):
                    st.session_state.classes.pop(i)
                    st.rerun()

    col_add, col_info = st.columns([1,3])
    with col_add:
        can_add = total_levels() < 20 and len(st.session_state.classes) < 12
        if st.button("➕ Add Class", disabled=not can_add):
            used = [e["cls"] for e in st.session_state.classes]
            new = next((c for c in ALL_CLASSES if c not in used), None)
            if new:
                st.session_state.classes.append({"cls": new, "level": 1})
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Stats ──
    st.markdown('<div class="card"><div class="section-title">Ability Scores</div>', unsafe_allow_html=True)
    stat_mode = st.radio("Generation method", ["Auto Optimized (27-point buy)", "Manual Point Buy"], horizontal=True)

    manual_stats = {}
    if "Manual" in stat_mode:
        total_cost = 0
        cols = st.columns(6)
        for i, stat in enumerate(STATS):
            with cols[i]:
                val = st.slider(stat, 8, 15, 8, key=f"pb_{stat}")
                manual_stats[stat] = val
                total_cost += POINT_COST[val]
        color = "red" if total_cost > 27 else "green"
        st.markdown(f"Points used: <span style='color:{color};font-weight:bold'>{total_cost}/27</span>", unsafe_allow_html=True)
        if total_cost > 27:
            st.error("Point buy exceeds 27 — reduce some stats.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Generate ──
    if st.button("📜 Generate Character", type="primary", use_container_width=True):
        name = st.session_state.name.strip()
        if not name or not race:
            st.error("Please fill in race and name.")
            st.stop()
        if total_levels() < 1 or total_levels() > 20:
            st.error("Total class levels must be between 1 and 20.")
            st.stop()
        if "Manual" in stat_mode:
            if total_cost > 27:
                st.error("Fix point buy before generating.")
                st.stop()
            stats = manual_stats
        else:
            stats = auto_stats([e["cls"] for e in st.session_state.classes])

        class_names  = [e["cls"] for e in st.session_state.classes]
        class_levels = [e["level"] for e in st.session_state.classes]
        total_lvl    = sum(class_levels)
        class_desc   = " / ".join(f"{c} {l}" for c,l in zip(class_names, class_levels))
        casters      = [e for e in st.session_state.classes if CLASS_DATA.get(e["cls"].lower(),{}).get("cast")]

        dm = stat_mod(stats["DEX"])
        cm = stat_mod(stats["CON"])

        with st.status("Generating your character…", expanded=True) as status:
            st.write("✍️ Writing backstory…")
            story = generate_backstory(name, race, background, alignment, class_desc)

            st.write("✨ Selecting spells…")
            spells = generate_spells(casters)

            st.write("🎨 Painting your portrait…")
            portrait_bytes = None
            try:
                portrait_bytes = generate_portrait(name, race, class_names, alignment)
            except Exception as e:
                st.warning(f"Portrait generation failed: {e}")

            status.update(label="Character ready!", state="complete")

        st.session_state.character = {
            "name":         name,
            "race":         race,
            "background":   background,
            "alignment":    alignment,
            "classes":      [dict(e) for e in st.session_state.classes],
            "total_level":  total_lvl,
            "stats":        stats,
            "hp":           calc_hp(class_names, class_levels, cm),
            "ac":           best_ac(class_names, dm),
            "gear":         get_equipment(class_names),
            "gold":         random.randint(20, 150),
            "spells":       spells,
            "story":        story,
            "prof_bonus":   prof_bonus(total_lvl),
            "portrait_bytes": portrait_bytes,
        }
        st.session_state.portrait_bytes = portrait_bytes
        st.session_state.page = "sheet"
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# SHEET PAGE
# ═══════════════════════════════════════════════════════════════════════════════

else:
    c = st.session_state.character
    if not c:
        st.warning("Generate a character first using the Builder.")
        st.stop()

    # Header
    cls_pills = "  ".join(
        f'<span class="class-pill">{e["cls"]} {e["level"]}</span>'
        for e in c["classes"]
    )
    bg_line = f" · {c['background']}" if c.get("background") else ""
    st.markdown(f"""
    <div class="card">
        <div class="char-title">{c['name']}</div>
        <div style="color:#bbb;font-size:15px;margin:4px 0 10px">
            {c['race']}{bg_line} · Level {c['total_level']} · {c['alignment']}
        </div>
        <div>{cls_pills}</div>
    </div>
    """, unsafe_allow_html=True)

    left_col, right_col = st.columns([1, 2])

    # Portrait
    with left_col:
        if c.get("portrait_bytes"):
            st.image(c["portrait_bytes"], use_container_width=True)
        else:
            st.markdown("""
            <div style="aspect-ratio:1;background:rgba(255,255,255,.05);border:1px solid #c9a44c;
                        border-radius:12px;display:flex;align-items:center;justify-content:center;
                        color:#888;font-size:14px">No portrait</div>
            """, unsafe_allow_html=True)

        # PDF download
        pdf_buf = make_pdf(c)
        st.download_button(
            "📄 Download PDF",
            pdf_buf,
            file_name=f"{c['name'].replace(' ','_')}_character_sheet.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    # Stats
    with right_col:
        st.markdown('<div class="card"><div class="section-title">Ability Scores</div>', unsafe_allow_html=True)
        scols = st.columns(6)
        for i, (stat, val) in enumerate(c["stats"].items()):
            m = stat_mod(val)
            with scols[i]:
                st.markdown(f"""
                <div class="stat-box">
                    <b>{stat}</b><br>
                    <span style="font-size:28px;font-weight:bold">{val}</span><br>
                    <span style="color:#aaa">{m:+}</span>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Combat
        st.markdown('<div class="card"><div class="section-title">Combat</div>', unsafe_allow_html=True)
        cc1, cc2, cc3, cc4 = st.columns(4)
        dm = stat_mod(c["stats"]["DEX"])
        cc1.metric("HP", c["hp"])
        cc2.metric("Armor Class", c["ac"])
        cc3.metric("Initiative", f"{dm:+}")
        cc4.metric("Proficiency", f"+{c['prof_bonus']}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Equipment
    st.markdown('<div class="card"><div class="section-title">Equipment</div>', unsafe_allow_html=True)
    gear_cols = st.columns(3)
    for i, item in enumerate(c["gear"]):
        gear_cols[i % 3].markdown(f"• {item}")
    st.markdown(f'<div class="gold">💰 Gold: {c["gold"]} gp</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Spells
    if c.get("spells"):
        st.markdown('<div class="card"><div class="section-title">Spells</div>', unsafe_allow_html=True)
        for s in c["spells"]:
            src = f" [{s['src']}]" if s.get("src") else ""
            st.markdown(f"✨ **{s['name']}**{src} — {s['desc']}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Backstory
    st.markdown('<div class="card"><div class="section-title">Backstory</div>', unsafe_allow_html=True)
    for para in c["story"].split("\n\n"):
        if para.strip():
            st.write(para.strip())
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# BUILDER
# -----------------------------
if st.session_state.page == "builder":

    st.title("🧙 Character Builder")

    race = st.text_input("Race")
    cls = st.text_input("Class")

    # 🎲 Name generator
    if st.button("🎲 Generate Name"):
        if race:
            st.session_state.name = generate_name(race)

    name = st.text_input("Name", key="name")
    lvl = st.slider("Level", 1, 20, 1)

    # 🎯 Mode select
    mode = st.radio(
        "Stat Generation Mode",
        ["Auto (Class Optimized)", "Manual (Point Buy)"]
    )

    manual_stats = {}
    total_cost = 0

    # 🎮 Manual UI
    if mode == "Manual (Point Buy)":

        st.markdown("### Assign Stats")

        for stat in ["STR","DEX","CON","INT","WIS","CHA"]:
            val = st.slider(stat, 8, 15, 8, key=f"stat_{stat}")
            manual_stats[stat] = val
            total_cost += POINT_COST[val]

        st.write(f"Points Used: {total_cost} / 27")

        if total_cost > 27:
            st.error("Too many points!")

    # 📜 GENERATE BUTTON (ONLY ONE PLACE)
    if st.button("📜 Generate Character"):

        char_name = st.session_state.name

        if not (char_name and race and cls):
            st.warning("Fill all fields")
            st.stop()

        # 🎯 Stats
        if mode == "Auto (Class Optimized)":
            stats = generate_stats(cls)
        else:
            if total_cost > 27:
                st.warning("Fix point allocation")
                st.stop()
            stats = manual_stats

        # ❤️ HP
        hp = hp_calc(cls, lvl, stats["CON"])

        # 🎒 Equipment (ADD THIS FUNCTION BELOW)
        gear, gold = equipment(cls)

        # 🎨 Portrait
        img = portrait(char_name, race, cls)

        # 📖 Story
        backstory = story(char_name, race, cls)

        # ✨ Character object
        st.session_state.character = {
            "name": char_name,
            "race": race,
            "class": cls,
            "level": lvl,
            "stats": stats,
            "hp": hp,
            "gear": gear,
            "gold": gold,
            "spells": spells(cls),
            "story": backstory,
            "image": img
        }

        st.success("Character Created → Sheet")

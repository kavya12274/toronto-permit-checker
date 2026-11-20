"""Every question the input form can ask (Build Plan step 2).

This list is the "contract" between the form and the checker:
  - the web form is drawn from it,
  - the checker reads answers by these keys,
  - later, the AI plan reader (step 20) will fill in the SAME keys and the user
    confirms each one. Nothing else needs to change to plug the AI in.

Every field is optional. A blank answer means "I don't know yet", and any rule
that needs it says NEED MORE INFO (golden rule 4), never PASS.

Field types:
  number  - a number (unit shown next to it)
  yesno   - Yes / No (blank = don't know)
  choice  - pick one from a list
  overlay - a number OR "none" (no value shown on the City's map)
  text    - free text
"""

# Short help text reused by the overlay questions
MAP_HELP = ("Find it on the City's Zoning By-law Interactive Map (toronto.ca/zoning): "
            "search your address, click your lot, and read the value in the pop-up. ")

SECTIONS = [
    ("project", "Project"),
    ("property", "Property and zone"),
    ("overlay", "Overlay values (from the zoning map)"),
    ("lot", "Lot"),
    ("house", "Existing house"),
    ("permit", "Permit questions"),
    ("main", "Main building measurements"),
    ("projections", "Things that stick out (porches, stairs, windows, eaves, AC)"),
    ("landscape", "Landscaping"),
    ("ancillary", "Shed / garage / accessory building"),
    ("deck", "Deck / porch / platform"),
    ("pool", "Pool"),
    ("driveway", "Driveway and parking"),
    ("solar", "Solar panels"),
    ("garden", "Garden suite"),
    ("laneway", "Laneway suite"),
    ("secondary", "Secondary suite"),
    ("multiplex", "Multiplex (2 to 4 units)"),
    ("code", "Building Code basics"),
    ("approvals", "Other approvals"),
]


def F(key, label, type_, section, unit="", help_="", choices=None):
    return {"key": key, "label": label, "type": type_, "section": section,
            "unit": unit, "help": help_, "choices": choices or []}


FIELDS = [
    # ---- Project
    F("project_type", "Project type", "choice", "project", choices=[]),  # filled from project_types.json
    F("description", "Short description of the project", "text", "project",
      help_="Plain words, with sizes if you know them. The AI box below can turn this into answers."),

    # ---- Property and zone
    F("address", "Address", "text", "property", help_="Used for address lookup. You can also fill everything in by hand."),
    F("zone", "Zone", "choice", "property", choices=["RD", "R", "RS", "RT", "RM", "Other"],
      help_="The letters at the start of your zone label, e.g. RD."),
    F("zone_label", "Full zone label", "text", "property",
      help_=MAP_HELP + "Copy the whole label, e.g. RD (f12.0; a370; d0.6) (x1234). "
            "The checker reads f, a, d, u and any exception number (x…) from it."),
    F("grey_property", "Is the property shown GREY on the zoning map (old pre-amalgamation by-law)?", "yesno", "property",
      help_="Grey areas are not covered by By-law 569-2013. The checker will stop and tell you to contact Toronto Building."),

    # ---- Overlay values
    F("ht", "Height overlay (HT)", "overlay", "overlay", "m",
      help_=MAP_HELP + "Turn on the 'Height Overlay' layer. Tick 'none' if no HT value shows."),
    F("st", "Storeys overlay (ST)", "overlay", "overlay", "storeys",
      help_=MAP_HELP + "Shown on the same Height Overlay layer as ST. Tick 'none' if there isn't one."),
    F("coverage_overlay", "Lot coverage overlay", "overlay", "overlay", "%",
      help_=MAP_HELP + "Turn on the 'Lot Coverage Overlay' layer. Tick 'none' if no value shows."),
    F("f", "Minimum frontage 'f' (from zone label)", "overlay", "overlay", "m",
      help_="The number after 'f' in the zone label. Filled in for you if you type the full label."),
    F("a", "Minimum lot area 'a' (from zone label)", "overlay", "overlay", "m²",
      help_="The number after 'a' in the zone label."),
    F("d", "Maximum density 'd' / FSI (from zone label)", "overlay", "overlay", "",
      help_="The number after 'd' in the zone label."),
    F("u", "Maximum units 'u' (from zone label)", "overlay", "overlay", "units",
      help_="The number after 'u' in the zone label."),
    F("exception", "Site-specific exception number (x…)", "text", "overlay",
      help_="If your zone label ends with (x123), type 123. This means extra site rules apply."),

    # ---- Lot
    F("lot_frontage", "Lot frontage (width along the street)", "number", "lot", "m"),
    F("lot_depth", "Lot depth", "number", "lot", "m"),
    F("lot_area", "Lot area", "number", "lot", "m²"),
    F("corner_lot", "Corner lot?", "yesno", "lot"),
    F("through_lot", "Through lot (street at front and back)?", "yesno", "lot"),
    F("lane", "Does the lot back onto (or side onto) a public lane?", "yesno", "lot"),
    F("lane_frontage", "Length of lot line touching the lane", "number", "lot", "m"),
    F("major_street", "Does the lot front onto a major street (on the Official Plan map)?", "yesno", "lot"),
    F("neighbour_fronts_flank", "Corner lot: does the neighbour behind face your side street?", "yesno", "lot"),

    # ---- Existing house
    F("building_type", "Building type (after the project)", "choice", "house",
      choices=["Detached house", "Semi-detached house", "Townhouse", "Detached houseplex",
               "Semi-detached houseplex", "Apartment building"]),
    F("house_storeys", "House storeys", "number", "house", "storeys"),
    F("existing_units", "Dwelling units now", "number", "house", "units"),
    F("proposed_units", "Dwelling units after the project", "number", "house", "units"),
    F("has_secondary_suite", "Does the house have (or will it have) a secondary suite?", "yesno", "house"),
    F("existing_tenants", "Are there tenants living in the house now?", "yesno", "house"),
    F("built_before_1953", "Was the house built before Oct 15, 1953?", "yesno", "house"),
    F("house_gfa", "House gross floor area", "number", "house", "m²"),

    # ---- Permit questions (P- rules)
    F("adds_structure", "Does the project add floor area or a new structure (storey, sunroom, porch, garage, deck)?", "yesno", "permit"),
    F("structural_work", "Structural changes, new or bigger window/door openings, or enclosing a deck/porch?", "yesno", "permit"),
    F("basement_work", "Basement work with structure, new plumbing/heating, underpinning, a basement entrance, or a second suite?", "yesno", "permit"),
    F("hvac_plumbing", "New heating/plumbing, chimney, wood stove, backwater valve or backflow device?", "yesno", "permit"),
    F("demolition", "Demolishing all or part of a building?", "yesno", "permit"),
    F("retaining_wall_height", "Retaining wall height (if any)", "number", "permit", "m"),
    F("retaining_wall_public", "Is the retaining wall next to public property, an entrance or a public area?", "yesno", "permit"),
    F("minor_work_only", "Is the work ONLY things like re-roofing, same-size window replacement, insulation, a new furnace, cabinets or a sump pump?", "yesno", "permit"),
    F("work_area", "Floor area of the new or renovated space", "number", "permit", "m²",
      help_="Used only for the rough permit fee estimate."),
    F("electrical_work", "Any electrical work?", "yesno", "permit"),
    F("gas_work", "Any gas appliance work?", "yesno", "permit"),

    # ---- Main building
    F("height", "Building height (from established grade to highest point)", "number", "main", "m"),
    F("main_wall_height", "Main wall height (side walls)", "number", "main", "m"),
    F("roof_type", "Roof type", "choice", "main", choices=["Pitched", "Flat or shallow (under 1:10)"]),
    F("roof_slope", "Roof slope above the 2nd storey (rise ÷ run)", "number", "main", "",
      help_="R zone only. Example: 5 up for every 3 across = 1.67."),
    F("entrance_height", "Main front entrance: height of its lowest point above grade", "number", "main", "m"),
    F("has_dormers", "Does it have dormers?", "yesno", "main"),
    F("dormer_width_pct", "Total dormer width as % of the wall below", "number", "main", "%"),
    F("storeys", "Storeys", "number", "main", "storeys"),
    F("building_length", "Building length", "number", "main", "m"),
    F("rd10_extension", "Is part of the length a one-storey rear extension ≤5.0 m high, ≤50% of the building width and ≥3.0 m from both side lot lines?", "yesno", "main"),
    F("building_depth", "Building depth (rear main wall measured from the required front setback line)", "number", "main", "m"),
    F("fsi", "Floor space index (FSI = total floor area ÷ lot area)", "number", "main", ""),
    F("lot_coverage", "Lot coverage (building footprint ÷ lot area)", "number", "main", "%"),
    F("front_setback", "Front yard setback", "number", "main", "m"),
    F("rear_setback", "Rear yard setback", "number", "main", "m"),
    F("side_setback", "Side yard setback (the smaller side)", "number", "main", "m"),
    F("side_setback_other", "Side yard setback (the other side)", "number", "main", "m"),
    F("side_wall_openings", "Does the wall on the smaller side have windows or doors?", "yesno", "main"),
    F("street_side_setback", "Corner lot: side setback on the street side", "number", "main", "m"),
    F("pre1953_addition_ok", "Pre-1953 house: is the addition at the rear, no closer to the side line than the existing wall, and any earlier addition 5+ years old?", "yesno", "main"),
    F("upper_platforms", "Number of balconies/decks at or above the 2nd storey", "number", "main"),
    F("upper_platform_area", "Largest of those balconies/decks", "number", "main", "m²"),
    F("upper_platforms_one_per_side", "At most one of those on each side of the house?", "yesno", "main"),
    F("residential_buildings", "Number of residential buildings on the lot (not counting garden/laneway suites)", "number", "main"),

    # ---- Projections
    F("rooftop_element", "Rooftop antenna/dish/parapet: how far above the max height?", "number", "projections", "m"),
    F("has_stairs_in_setback", "Exterior stairs inside a required setback?", "yesno", "projections"),
    F("stairs_width", "Exterior stairs width", "number", "projections", "m"),
    F("stairs_to_lot_line", "Exterior stairs distance to the lot line", "number", "projections", "m"),
    F("has_bay_window", "Bay or box windows sticking into a setback?", "yesno", "projections"),
    F("bay_location", "Bay window location", "choice", "projections", choices=["Front or rear", "Side"]),
    F("bay_projection", "Bay window projection", "number", "projections", "m"),
    F("bay_wall_pct", "Bay window width as % of the wall", "number", "projections", "%"),
    F("has_eaves", "Eaves sticking into a setback?", "yesno", "projections"),
    F("eaves_projection", "Eaves projection", "number", "projections", "m"),
    F("eaves_to_lot_line", "Eaves distance to the lot line", "number", "projections", "m"),
    F("has_ac", "Air conditioner / heat pump outside?", "yesno", "projections"),
    F("ac_location", "Where is it?", "choice", "projections",
      choices=["Rear yard", "Side yard (ground level)", "Side yard (above first storey)", "Front yard"]),
    F("ac_projection", "How far it sticks into the setback", "number", "projections", "m"),
    F("ac_to_front_line", "Front yard AC: distance to the front lot line", "number", "projections", "m"),

    # ---- Landscaping
    F("front_landscape_pct", "Front yard landscaped (not paved or parked on)", "number", "landscape", "%"),
    F("front_soft_pct", "Soft landscaping (grass, plants) as % of the front landscaping", "number", "landscape", "%"),
    F("rear_soft_pct", "Rear yard soft landscaping", "number", "landscape", "%"),
    F("street_side_landscape_pct", "Corner lot: street-side yard landscaped", "number", "landscape", "%"),

    # ---- Ancillary building (shed, garage)
    F("anc_area", "Floor area of the shed/garage", "number", "ancillary", "m²"),
    F("anc_storeys", "Storeys", "number", "ancillary", "storeys"),
    F("anc_attached", "Attached to the house?", "yesno", "ancillary"),
    F("anc_plumbing", "Has plumbing?", "yesno", "ancillary"),
    F("anc_storage_only", "Used only for storage?", "yesno", "ancillary"),
    F("anc_height", "Height", "number", "ancillary", "m"),
    F("anc_to_house", "Distance to the house", "number", "ancillary", "m"),
    F("anc_rear_setback", "Rear setback", "number", "ancillary", "m"),
    F("anc_side_setback", "Side setback", "number", "ancillary", "m"),
    F("anc_in_front_yard", "Is it in the front yard?", "yesno", "ancillary"),
    F("anc_in_side_yard", "Is it in a side yard (rather than the rear yard)?", "yesno", "ancillary"),
    F("anc_living", "Will anyone live or sleep in it?", "yesno", "ancillary"),
    F("anc_total_area", "Total floor area of ALL sheds/garages on the lot", "number", "ancillary", "m²"),
    F("anc_coverage", "All sheds/garages: % of lot area covered", "number", "ancillary", "%"),
    F("anc_parking", "Does it contain parking (garage/carport)?", "yesno", "ancillary"),
    F("anc_to_lane_line", "Distance to the lane (or flanking street) lot line", "number", "ancillary", "m"),
    F("anc_to_lane_centre", "Distance to the original centreline of the lane", "number", "ancillary", "m"),
    F("garage_door_width", "Total garage door width facing the street", "number", "ancillary", "m"),

    # ---- Deck / porch
    F("deck_height", "Deck/porch floor height above ground", "number", "deck", "m"),
    F("deck_is_exit", "Is the deck part of a required exit?", "yesno", "deck"),
    F("deck_level", "Deck level", "choice", "deck", choices=["First storey or below", "Second storey or above"]),
    F("deck_above_floor", "Upper deck: height above the floor it serves", "number", "deck", "m"),
    F("deck_location", "Deck location", "choice", "deck", choices=["Front yard", "Rear yard", "Side yard"]),
    F("deck_encroachment", "How far the deck sticks into the required setback", "number", "deck", "m"),
    F("deck_to_side_line", "Deck distance to the nearest side lot line", "number", "deck", "m"),
    F("deck_setback", "Deck distance to the nearest rear/side lot line", "number", "deck", "m"),

    # ---- Pool
    F("pool_rear_setback", "Pool rear setback", "number", "pool", "m"),
    F("pool_side_setback", "Pool side setback", "number", "pool", "m"),
    F("pool_street_side", "Is that side next to a street?", "yesno", "pool"),
    F("pool_area", "Pool water surface area", "number", "pool", "m²"),

    # ---- Driveway
    F("driveway_width", "Driveway width", "number", "driveway", "m"),
    F("parking_width_behind_wall", "Width of the parking space(s) behind the front wall (garage etc.)", "number", "driveway", "m"),
    F("all_parking_rear", "Is all parking in the rear yard?", "yesno", "driveway"),
    F("front_yard_parking", "Will cars park in the front yard outside a permitted driveway?", "yesno", "driveway"),
    F("rear_parking_spaces", "Outdoor parking spaces in the rear yard", "number", "driveway"),
    F("garage_in_front_wall", "Is there a garage door / vehicle entrance in the front main wall?", "yesno", "driveway"),
    F("parking_access", "Where do cars get onto the lot?", "choice", "driveway",
      choices=["From the front street", "From the flanking (side) street", "From the lane"]),
    F("new_curb_cut", "New curb cut or front yard parking pad?", "yesno", "driveway"),

    # ---- Solar
    F("solar_above_height", "Solar panels: how far above the max height?", "number", "solar", "m"),
    F("solar_in_front", "Are panels in the front yard or street-side yard?", "yesno", "solar"),

    # ---- Garden suite
    F("other_suite_building", "Is there already a garden suite or laneway suite on the lot?", "yesno", "garden"),
    F("gs_height", "Garden suite height", "number", "garden", "m"),
    F("gs_storeys", "Garden suite storeys", "number", "garden", "storeys"),
    F("gs_to_house", "Distance from the garden suite to the house", "number", "garden", "m"),
    F("gs_rear_setback", "Garden suite rear setback", "number", "garden", "m"),
    F("gs_rear_windows_high", "Rear windows above 4.0 m, with the rear line next to a residential lot?", "yesno", "garden"),
    F("gs_side_setback", "Garden suite side setback (smaller side)", "number", "garden", "m"),
    F("gs_side_openings", "Does that side wall have windows or doors?", "yesno", "garden"),
    F("gs_gfa", "Garden suite gross floor area", "number", "garden", "m²"),
    F("suite_roof_item", "Anything on the suite's roof that goes above its height limit?", "choice", "garden",
      choices=["Nothing", "Skylight", "Antenna or flagpole", "Rooftop equipment (e.g. heat pump)", "Solar panels"]),
    F("suite_roof_above", "How far above the suite's height limit?", "number", "garden", "m"),
    F("gs_deck_area", "Garden suite deck area (if any)", "number", "garden", "m²"),
    F("all_buildings_coverage", "All buildings together: % of lot covered", "number", "garden", "%"),
    F("bike_spaces", "Bicycle parking spaces", "number", "garden"),
    F("rear_soft_full_width_pct", "Rear yard soft landscaping (across the full lot width)", "number", "garden", "%"),

    # ---- Laneway suite
    F("ls_length", "Laneway suite length", "number", "laneway", "m"),
    F("ls_width", "Laneway suite width", "number", "laneway", "m"),
    F("ls_height", "Laneway suite height", "number", "laneway", "m"),
    F("ls_storeys", "Laneway suite storeys", "number", "laneway", "storeys"),
    F("ls_to_house", "Distance from the laneway suite to the house", "number", "laneway", "m"),
    F("ls_rear_setback", "Laneway suite rear setback", "number", "laneway", "m"),
    F("ls_side_setback", "Laneway suite side setback", "number", "laneway", "m"),
    F("ls_gfa", "Laneway suite floor area", "number", "laneway", "m²"),
    F("ls_between_soft_pct", "Soft landscaping between the house and suite", "number", "laneway", "%"),
    F("ls_lane_side_soft_pct", "Soft landscaping between the suite and the lane", "number", "laneway", "%"),
    F("ls_deck_area", "Laneway suite deck area (if any)", "number", "laneway", "m²"),
    F("ancillary_coverage_all", "All ancillary buildings: % of lot area", "number", "laneway", "%"),

    # ---- Secondary suite
    F("ss_count", "Number of secondary suites in the dwelling", "number", "secondary"),
    F("ss_floor_pct", "Secondary suite as % of the dwelling's interior floor area", "number", "secondary", "%"),
    F("ss_whole_basement", "Is the suite the whole basement?", "yesno", "secondary"),

    # ---- Multiplex
    F("max_bedrooms_per_unit", "Most bedrooms in any one unit (bachelor counts as 1)", "number", "multiplex"),
    F("within_existing_building", "Do the new units fit entirely inside the building as it already exists?", "yesno", "multiplex"),
    F("platforms_per_unit", "Balconies/decks at or above the 2nd storey, per unit", "number", "multiplex"),

    # ---- Building Code
    F("stair_run", "Stair run (tread depth)", "number", "code", "mm"),
    F("has_bedroom", "Is there a bedroom on a floor in this project?", "yesno", "code"),
    F("egress_window", "Does each bedroom floor have an outside window or door that opens from inside without tools?", "yesno", "code"),
    F("egress_sill", "Egress window sill height above the floor", "number", "code", "mm"),
    F("window_well", "Does the egress window open into a window well?", "yesno", "code"),
    F("window_well_clearance", "Clear space in front of the window in the well", "number", "code", "mm"),
    F("low_window_high_drop", "Any openable window with sill under 900 mm and a drop outside over 1.8 m?", "yesno", "code"),
    F("low_window_guarded", "If so, does it have a guard or opening limiter?", "yesno", "code"),

    # ---- Other approvals
    F("heritage_designated", "Is the property a designated heritage property (Part IV)?", "yesno", "approvals"),
    F("in_hcd", "Is it inside a Heritage Conservation District?", "yesno", "approvals"),
    F("trca", "Is it inside the TRCA regulated area?", "yesno", "approvals"),
    F("ravine", "Is it inside a ravine-protected area?", "yesno", "approvals"),
    F("trees_near_work", "Any City tree, or private tree 30 cm+ wide, near the work area?", "yesno", "approvals"),
    F("flightpath", "Is it inside the hospital helicopter flightpath area (near St. Michael's or SickKids)?", "yesno", "approvals"),
    F("near_highway", "Is the lot next to a provincial highway?", "yesno", "approvals"),
    F("former_commercial", "Was the property used for industry or commerce before?", "yesno", "approvals"),
]

FIELD_BY_KEY = {f["key"]: f for f in FIELDS}


def label(key):
    """Human label for a field key (used in NEED MORE INFO messages)."""
    f = FIELD_BY_KEY.get(key)
    return f["label"] if f else key


# ---------------------------------------------------------------- "Simple words" versions
# Shorter, everyday wording shown when the Simple words switch is on (English only).
# Questions not listed here are already plain and keep their normal wording.
SIMPLE = {
    "description": "In a few words, what are you building?",
    "zone": "Zone letters (like RD or R)",
    "zone_label": "Zone label from the City's map",
    "grey_property": "Is your lot grey on the City's zoning map?",
    "ht": "Height limit on the map (HT)",
    "st": "Storey limit on the map (ST)",
    "coverage_overlay": "Coverage limit on the map",
    "f": "Smallest lot width allowed (f)",
    "a": "Smallest lot size allowed (a)",
    "d": "Floor space limit (d)",
    "u": "Most homes allowed on the lot (u)",
    "exception": "Special rule number for your lot (x…)",
    "lot_frontage": "How wide is your lot at the street?",
    "lot_depth": "How deep is your lot, front to back?",
    "lot_area": "How big is your lot?",
    "lane": "Is there a lane behind or beside your lot?",
    "lane_frontage": "How long is the part of your lot touching the lane?",
    "major_street": "Is your street a major street?",
    "neighbour_fronts_flank": "Does the house behind you face your side street?",
    "building_type": "What kind of house will it be?",
    "existing_units": "How many homes are in the house now?",
    "proposed_units": "How many homes after the project?",
    "has_secondary_suite": "Will there be a second unit in the house?",
    "built_before_1953": "Was the house built before 1953?",
    "house_gfa": "Floor area of the whole house",
    "adds_structure": "Are you adding new space or a new structure?",
    "structural_work": "Are you changing walls, beams, windows or doors?",
    "basement_work": "Big basement work (plumbing, underpinning, new entrance, new unit)?",
    "hvac_plumbing": "New heating, plumbing, chimney or wood stove?",
    "minor_work_only": "Is it only small jobs (new roof shingles, same-size windows, insulation)?",
    "work_area": "How big is the new or renovated space?",
    "height": "How tall is the building, from the ground to the top?",
    "main_wall_height": "How tall are the side walls?",
    "roof_slope": "How steep is the roof above the 2nd floor?",
    "entrance_height": "How high is the front door above the ground?",
    "dormer_width_pct": "How wide are the dormers, compared with the wall?",
    "storeys": "How many floors?",
    "building_length": "How long is the house, front to back?",
    "rd10_extension": "Is part of it a small one-floor bump-out at the back?",
    "building_depth": "How far back does the house go from the front setback line?",
    "fsi": "Total floor area ÷ lot area (FSI)",
    "lot_coverage": "How much of the lot does the house cover?",
    "front_setback": "Space between the house and the front lot line",
    "rear_setback": "Space between the house and the back lot line",
    "side_setback": "Space to the side lot line (the narrower side)",
    "side_setback_other": "Space to the side lot line (the other side)",
    "side_wall_openings": "Does that narrow side have windows or doors?",
    "street_side_setback": "Corner lot: space to the side street",
    "pre1953_addition_ok": "Old house: is the addition at the back and in line with the old side wall?",
    "upper_platforms": "How many balconies or decks on the 2nd floor or higher?",
    "upper_platform_area": "Size of the biggest of those",
    "residential_buildings": "How many houses on the lot (not counting a garden or laneway suite)?",
    "anc_area": "Size of the shed or garage",
    "anc_to_house": "Distance from the shed or garage to the house",
    "anc_rear_setback": "Space to the back lot line",
    "anc_side_setback": "Space to the side lot line",
    "anc_total_area": "Size of ALL sheds and garages together",
    "anc_coverage": "How much of the lot do all sheds and garages cover?",
    "anc_to_lane_line": "Distance to the lane",
    "deck_height": "How high is the deck floor above the ground?",
    "deck_is_exit": "Do you need the deck to get out of the house?",
    "deck_encroachment": "How far does the deck stick into the setback space?",
    "deck_setback": "Distance from the deck to the nearest lot line",
    "pool_area": "Size of the water surface",
    "driveway_width": "How wide is the driveway?",
    "parking_width_behind_wall": "How wide is the garage or parking spot beside the house?",
    "gs_height": "How tall is the garden suite?",
    "gs_to_house": "Distance from the garden suite to the house",
    "gs_rear_setback": "Space to the back lot line",
    "gs_side_setback": "Space to the side lot line",
    "gs_gfa": "Floor area of the garden suite",
    "all_buildings_coverage": "How much of the lot do all buildings cover?",
    "ls_to_house": "Distance from the laneway suite to the house",
    "ss_floor_pct": "How much of the house will the second unit take up?",
    "max_bedrooms_per_unit": "Most bedrooms in any one home",
    "within_existing_building": "Do the new homes fit inside the house as it is now?",
    "stair_run": "How deep is each stair step?",
    "egress_window": "Can you climb out a window or door from every floor with a bedroom?",
    "egress_sill": "How high is the bottom of that window from the floor?",
    "window_well_clearance": "Space in front of the window inside the window well",
    "low_window_high_drop": "Any low window with a big drop outside?",
    "heritage_designated": "Is the house a protected heritage building?",
    "in_hcd": "Is it in a heritage district?",
    "trca": "Is it near a river, ravine or the lake (TRCA area)?",
    "ravine": "Is it in a ravine-protected area?",
    "trees_near_work": "Any big tree (30 cm wide or more) or City tree near the work?",
    "flightpath": "Is it near St. Michael's or SickKids (helicopter path)?",
    "former_commercial": "Was the land ever a factory, shop or gas station?",
}
for _f in FIELDS:
    _f["simple"] = SIMPLE.get(_f["key"], "")

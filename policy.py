from typing import Dict, List

POSITIVE = {"はい","Yes","OK","Proceed","Next","Continue","Enter","Investigate","Talk","Agree","Story","Start"}
NEGATIVE = {"No","いいえ","Cancel","Exit","Quit","Save","Load","Settings","Back","Title"}

def _choose_from_menu(options: List[str]) -> str:
    opts = [o.strip() for o in options if o.strip()]
    for o in opts:
        if o.startswith((">","▶")):
            return "ENTER"
    for o in opts:
        if any(k.lower() in o.lower() for k in POSITIVE):
            return "ENTER"
    for o in opts:
        if any(k.lower() in o.lower() for k in NEGATIVE):
            continue
        return "ENTER"
    return "ENTER"

def decide_action(state: Dict, last_actions: List[str]) -> Dict:
    dialog = state.get("dialog_text")
    menu = state.get("menu_options") or []
    blocked = float(state.get("blocked_seconds") or 0.0)
    hint = (state.get("map_hint") or "unknown").lower()

    if dialog:
        return {"action":"INTERACT", "reason":"advance dialogue"}
    if menu:
        return {"action": _choose_from_menu(menu), "reason":"choose progression option"}
    if blocked >= 8.0:
        return {"action":"MENU", "reason":"trigger unblock routine"}
    if hint == "door":
        return {"action":"UP", "reason":"move to door"}
    if hint == "stair":
        return {"action":"UP", "reason":"climb stair"}
    last = (last_actions[-1] if last_actions else "UP")
    cycle = {"UP":"RIGHT","RIGHT":"DOWN","DOWN":"LEFT","LEFT":"UP"}
    return {"action": cycle.get(last,"UP"), "reason":"explore map"}

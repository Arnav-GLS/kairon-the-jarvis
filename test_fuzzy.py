import difflib

wake_phrases = ["what's up buddy", "daddy's home", "how's going on", "jarvis", "hey jarvis"]
raw = "daddy's home"
raw_lower = raw.lower()

for wp in wake_phrases:
    exact = wp.lower() in raw_lower
    ratio = difflib.SequenceMatcher(None, wp.lower(), raw_lower).ratio()
    print(f"  {wp}: exact={exact}, ratio={ratio:.2f}")
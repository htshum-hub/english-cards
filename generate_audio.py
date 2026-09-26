#!/usr/bin/env python3
"""讀 scenes.json (v2)，用 Google Chirp3-HD 生成 MP3。
結構：scene["sets"][mode][level] = {"vocab":[...], "dialogue":[...]}
語音：女兒=en-US-Chirp3-HD-Kore、媽媽=en-US-Chirp3-HD-Gacrux。
Chirp3-HD 用標準 texttospeech API + API key，支援 speakingRate。"""
import os, json, base64, requests, time

API_KEY = os.environ["TTS_API_KEY"]
URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"

# Chirp3-HD 語音（用你揀嘅 Kore / Gacrux）
VOICE_NAME = {
    "Mama": "en-US-Chirp3-HD-Gacrux",
    "Girl": "en-US-Chirp3-HD-Kore",
}
SPEAKING_RATE = 0.9  # 慢少少方便女兒跟讀

with open("scenes.json", encoding="utf-8") as f:
    data = json.load(f)

LEVELS = data.get("levels", ["K3", "P1", "P2"])
MODES = data.get("modes", ["natural", "story"])

os.makedirs("audio", exist_ok=True)
manifest = {}

def synth(text, who):
    body = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": VOICE_NAME.get(who, VOICE_NAME["Mama"])},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": SPEAKING_RATE},
    }
    for attempt in range(4):
        r = requests.post(URL, json=body, timeout=90)
        if r.status_code == 200:
            return base64.b64decode(r.json()["audioContent"])
        if r.status_code in (429, 500, 503):
            time.sleep(3 * (attempt + 1)); continue
        raise RuntimeError(f"TTS {r.status_code}: {r.text[:300]}")
    raise RuntimeError("TTS failed after retries")

count = 0
for scene in data["scenes"]:
    sid = scene["id"]
    manifest[sid] = {}
    sets = scene.get("sets", {})
    for mode in MODES:
        if mode not in sets:
            continue
        manifest[sid][mode] = {}
        for lvl in LEVELS:
            if lvl not in sets[mode]:
                continue
            block = sets[mode][lvl]
            manifest[sid][mode][lvl] = {"vocab": [], "dialogue": []}
            for i, v in enumerate(block.get("vocab", [])):
                fn = f"audio/{sid}-{mode}-{lvl}-vocab-{i}.mp3"
                with open(fn, "wb") as out:
                    out.write(synth(v["en"], "Girl"))
                manifest[sid][mode][lvl]["vocab"].append(fn)
                count += 1
            for i, d in enumerate(block.get("dialogue", [])):
                fn = f"audio/{sid}-{mode}-{lvl}-line-{i}.mp3"
                with open(fn, "wb") as out:
                    out.write(synth(d["en"], d.get("who", "Mama")))
                manifest[sid][mode][lvl]["dialogue"].append(fn)
                count += 1
            print(f"[OK] {sid}/{mode}/{lvl}")

with open("manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print(f"Done. Generated {count} MP3 files.")

#!/usr/bin/env python3
"""讀 scenes.json，用 Google Gemini-TTS 為每個難度級別嘅對話同生字生成 MP3。
語音：女兒=Kore (energetic child)、媽媽=Gacrux (warm mummy)。
支援 3 級 (K3/P1/P2)。"""
import os, json, base64, requests

API_KEY = os.environ["TTS_API_KEY"]
URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"
MODEL = "gemini-3.1-flash-tts-preview"

# 語音設定（預選定）
VOICES = {
    "Mama": {"name": "Gacrux", "prompt": "Read aloud in a warm, gentle mummy tone."},
    "Girl": {"name": "Kore",   "prompt": "Read aloud in an energetic, cheerful young child girl tone."},
}

with open("scenes.json", encoding="utf-8") as f:
    data = json.load(f)

LEVELS = ["K3", "P1", "P2"]
os.makedirs("audio", exist_ok=True)
manifest = {}

def synth(text, who):
    v = VOICES.get(who, VOICES["Mama"])
    body = {
        "input": {"prompt": v["prompt"], "text": text},
        "voice": {"languageCode": "en-us", "name": v["name"], "model_name": MODEL},
        "audioConfig": {"audioEncoding": "MP3"},
    }
    r = requests.post(URL, json=body, timeout=60)
    r.raise_for_status()
    return base64.b64decode(r.json()["audioContent"])

count = 0
for scene in data["scenes"]:
    sid = scene["id"]
    manifest[sid] = {}
    # levels 結構：scene["levels"][lvl] = {"vocab":[...], "dialogue":[...]}
    levels = scene.get("levels")
    if not levels:
        # 舊格式後備：用 scene 本身做 K3
        levels = {"K3": {"vocab": scene.get("vocab",[]), "dialogue": scene.get("dialogue",[])}}
    for lvl in LEVELS:
        if lvl not in levels:
            continue
        block = levels[lvl]
        manifest[sid][lvl] = {"vocab": [], "dialogue": []}
        for i, v in enumerate(block.get("vocab", [])):
            fn = f"audio/{sid}-{lvl}-vocab-{i}.mp3"
            with open(fn, "wb") as out:
                out.write(synth(v["en"], "Girl"))
            manifest[sid][lvl]["vocab"].append(fn)
            count += 1
        for i, d in enumerate(block.get("dialogue", [])):
            fn = f"audio/{sid}-{lvl}-line-{i}.mp3"
            with open(fn, "wb") as out:
                out.write(synth(d["en"], d.get("who", "Mama")))
            manifest[sid][lvl]["dialogue"].append(fn)
            count += 1
        print(f"[OK] {sid}/{lvl}")

with open("manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print(f"Done. Generated {count} MP3 files.")

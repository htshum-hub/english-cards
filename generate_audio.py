#!/usr/bin/env python3
"""讀 scenes.json，為每句對話用 Google Cloud TTS 生成 MP3。"""
import os, json, base64, hashlib, requests

API_KEY = os.environ["TTS_API_KEY"]
TTS_URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"

with open("scenes.json", encoding="utf-8") as f:
    data = json.load(f)

voice_map = data.get("voice", {"Mama": "en-US-Neural2-F", "Girl": "en-US-Neural2-C", "rate": 0.85})
rate = voice_map.get("rate", 0.85)

os.makedirs("audio", exist_ok=True)
manifest = {}

def synth(text, voice_name):
    body = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": voice_name},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": rate},
    }
    r = requests.post(TTS_URL, json=body, timeout=30)
    r.raise_for_status()
    return base64.b64decode(r.json()["audioContent"])

count = 0
for scene in data["scenes"]:
    sid = scene["id"]
    manifest[sid] = {"vocab": [], "dialogue": []}
    # 生字語音
    for i, v in enumerate(scene["vocab"]):
        fn = f"audio/{sid}-vocab-{i}.mp3"
        with open(fn, "wb") as out:
            out.write(synth(v["en"], voice_map["Girl"]))
        manifest[sid]["vocab"].append(fn)
        count += 1
    # 對話語音（按角色揀聲）
    for i, d in enumerate(scene["dialogue"]):
        voice = voice_map.get(d["who"], voice_map["Mama"])
        fn = f"audio/{sid}-line-{i}.mp3"
        with open(fn, "wb") as out:
            out.write(synth(d["en"], voice))
        manifest[sid]["dialogue"].append(fn)
        count += 1
    print(f"[OK] {sid}: {len(scene['vocab'])} vocab + {len(scene['dialogue'])} lines")

with open("manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"\\nDone. Generated {count} MP3 files.")

#!/usr/bin/env python3
# build: chirp3-patch-6
"""PATCH MODE (Chirp3-HD): fill the 6 sentences Gemini persistently fails on.
Uses standard texttospeech API + API key (stable, no empty-parts).
Voices match: Girl=en-US-Chirp3-HD-Kore, Mama=en-US-Chirp3-HD-Leda.
Incremental: only generates missing .wav files."""
import os, json, base64, requests, time, struct

API_KEY = os.environ["TTS_API_KEY"]
URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"

VOICE_NAME = {
    "Mama": "en-US-Chirp3-HD-Leda",
    "Girl": "en-US-Chirp3-HD-Kore",
}
SPEAKING_RATE = 0.9

with open("scenes.json", encoding="utf-8") as f:
    data = json.load(f)
LEVELS = data.get("levels", ["K3", "P1", "P2"])
MODES = data.get("modes", ["natural", "story"])

os.makedirs("audio", exist_ok=True)

def pcm_to_wav_or_mp3(content_b64):
    return base64.b64decode(content_b64)

def synth(text, who):
    body = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": VOICE_NAME.get(who, VOICE_NAME["Girl"])},
        "audioConfig": {"audioEncoding": "LINEAR16", "speakingRate": SPEAKING_RATE},
    }
    for attempt in range(5):
        r = requests.post(URL, json=body, timeout=90)
        if r.status_code == 200:
            return base64.b64decode(r.json()["audioContent"])
        if r.status_code in (429, 500, 503):
            time.sleep(3 * (attempt + 1)); continue
        raise RuntimeError(f"TTS {r.status_code}: {r.text[:300]}")
    raise RuntimeError("failed after retries")

generated = 0
failed = []
missing = 0

def gen_file(fn, text, who):
    global generated, missing
    if os.path.exists(fn) and os.path.getsize(fn) > 1000:
        return
    try:
        wav = synth(text, who)
        with open(fn, "wb") as out:
            out.write(wav)
        generated += 1
        time.sleep(0.5)
    except Exception as e:
        failed.append((fn, str(e)[:100]))
        missing += 1

manifest = {}
total = 0
for scene in data["scenes"]:
    sid = scene["id"]
    manifest[sid] = {}
    for mode in MODES:
        if mode not in scene.get("sets", {}):
            continue
        manifest[sid][mode] = {}
        for lvl in LEVELS:
            if lvl not in scene["sets"][mode]:
                continue
            block = scene["sets"][mode][lvl]
            manifest[sid][mode][lvl] = {"vocab": [], "dialogue": []}
            for i, v in enumerate(block.get("vocab", [])):
                fn = f"audio/{sid}-{mode}-{lvl}-vocab-{i}.wav"
                gen_file(fn, v["en"], "Girl")
                manifest[sid][mode][lvl]["vocab"].append(fn)
                total += 1
            for i, d in enumerate(block.get("dialogue", [])):
                fn = f"audio/{sid}-{mode}-{lvl}-line-{i}.wav"
                gen_file(fn, d["en"], d.get("who", "Mama"))
                manifest[sid][mode][lvl]["dialogue"].append(fn)
                total += 1

with open("manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
with open("remaining.txt", "w") as f:
    f.write(str(missing))

print(f"This run generated {generated} new clips (Chirp3-HD). Failed: {len(failed)}. Still missing: {missing}")
for x in failed[:10]:
    print("  FAIL", x)
print(f"Total clips: {total}")
print("ALL DONE." if missing == 0 else f"{missing} still missing.")

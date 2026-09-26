#!/usr/bin/env python3
# build: batched-kore-leda-autochain-r2
"""BATCHED GENERATION: Gemini-TTS for all scenes/modes/levels.
Daughter=Kore (energetic child), Mama=Leda (warm young mother).
- Incremental: skips existing files (safe to re-run).
- Rate-limited: small pause between calls to avoid 429.
- Fault-tolerant: a failed clip is logged and skipped, never crashes the run.
- Batched: generates up to BATCH_LIMIT new clips per run, then commits.
- Writes remaining.txt (number of clips still missing) so the workflow can
  auto-chain the next batch until everything is done."""
import os, json, base64, requests, time, struct
from google.oauth2 import service_account
from google.auth.transport.requests import Request

PROJECT = "english-cards-tts"
REGION = "global"
MODEL = "gemini-2.5-flash-tts"
ENDPOINT = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/publishers/google/models/{MODEL}:generateContent"

BATCH_LIMIT = int(os.environ.get("BATCH_LIMIT", "200"))
PAUSE = float(os.environ.get("TTS_PAUSE", "1.2"))

sa_info = json.loads(os.environ["GCP_SA_KEY"])
creds = service_account.Credentials.from_service_account_info(
    sa_info, scopes=["https://www.googleapis.com/auth/cloud-platform"])
creds.refresh(Request())
TOKEN = creds.token
TOKEN_TS = time.time()

VOICES = {
    "Mama": {"name": "Leda", "prompt": "Read aloud in a warm, gentle, young-mother tone, soft and loving."},
    "Girl": {"name": "Kore", "prompt": "Read aloud in an energetic, cheerful, playful young child girl tone."},
}

with open("scenes.json", encoding="utf-8") as f:
    data = json.load(f)
LEVELS = data.get("levels", ["K3", "P1", "P2"])
MODES = data.get("modes", ["natural", "story"])

os.makedirs("audio", exist_ok=True)

def refresh_token():
    global TOKEN, TOKEN_TS
    if time.time() - TOKEN_TS > 2400:
        creds.refresh(Request())
        TOKEN = creds.token
        TOKEN_TS = time.time()

def pcm_to_wav(pcm, rate=24000):
    n = len(pcm)
    return b'RIFF' + struct.pack('<I', 36 + n) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16) + b'data' + struct.pack('<I', n) + pcm

def synth(text, who):
    refresh_token()
    v = VOICES.get(who, VOICES["Mama"])
    body = {
        "contents": [{"role": "user", "parts": [{"text": v["prompt"] + " " + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v["name"]}}},
        },
    }
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    for attempt in range(6):
        try:
            r = requests.post(ENDPOINT, json=body, headers=headers, timeout=90)
        except Exception:
            time.sleep(5 * (attempt + 1)); continue
        if r.status_code == 200:
            b64 = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            return base64.b64decode(b64)
        if r.status_code in (429, 500, 503):
            time.sleep(6 * (attempt + 1)); continue
        raise RuntimeError(f"TTS {r.status_code}: {r.text[:200]}")
    raise RuntimeError("rate-limited after retries")

generated = 0
failed = []
missing = 0
budget_left = BATCH_LIMIT

def gen_file(fn, text, who):
    global generated, budget_left, missing
    if os.path.exists(fn) and os.path.getsize(fn) > 1000:
        return  # already done
    if budget_left <= 0:
        missing += 1
        return
    try:
        pcm = synth(text, who)
        with open(fn, "wb") as out:
            out.write(pcm_to_wav(pcm))
        generated += 1
        budget_left -= 1
        time.sleep(PAUSE)
    except Exception as e:
        failed.append((fn, str(e)[:80]))
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

print(f"This run generated {generated} new clips. Failed: {len(failed)}. Still missing: {missing}")
for x in failed[:10]:
    print("  FAIL", x)
print(f"Total clips: {total}")
if missing == 0:
    print("ALL DONE.")
else:
    print(f"{missing} clips remain — workflow will auto-chain next batch.")

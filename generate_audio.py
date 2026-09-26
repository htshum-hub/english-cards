#!/usr/bin/env python3
"""SAMPLE MODE: 用 Vertex AI Gemini-TTS 生成「刷牙」場景樣本，試聽童聲效果。
語音：女兒=Kore(energetic child)、媽媽=Gacrux(warm mummy)，用語氣 prompt。
認證：Service Account JSON (GCP_SA_KEY) -> OAuth token。"""
import os, json, base64, requests, time
from google.oauth2 import service_account
from google.auth.transport.requests import Request

PROJECT = "english-cards-tts"
REGION = "global"
MODEL = "gemini-2.5-flash-tts"  # 用 GA 版(2.5)較穩定；preview(3.1)如需要可改
ENDPOINT = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/publishers/google/models/{MODEL}:generateContent"

# OAuth token from service account
sa_info = json.loads(os.environ["GCP_SA_KEY"])
creds = service_account.Credentials.from_service_account_info(
    sa_info, scopes=["https://www.googleapis.com/auth/cloud-platform"])
creds.refresh(Request())
TOKEN = creds.token

VOICES = {
    "Mama": {"name": "Gacrux", "prompt": "Read aloud in a warm, gentle mummy tone."},
    "Girl": {"name": "Kore",   "prompt": "Read aloud in an energetic, cheerful, playful young child girl tone."},
}

with open("scenes.json", encoding="utf-8") as f:
    data = json.load(f)

os.makedirs("audio", exist_ok=True)

def synth(text, who):
    v = VOICES.get(who, VOICES["Mama"])
    body = {
        "contents": [{"role": "user", "parts": [{"text": v["prompt"] + " " + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v["name"]}}
            },
        },
    }
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    for attempt in range(3):
        r = requests.post(ENDPOINT, json=body, headers=headers, timeout=90)
        if r.status_code == 200:
            j = r.json()
            b64 = j["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            return base64.b64decode(b64)
        if r.status_code in (429, 500, 503):
            time.sleep(3*(attempt+1)); continue
        raise RuntimeError(f"TTS {r.status_code}: {r.text[:400]}")
    raise RuntimeError("TTS failed after retries")

# 只生成 brushing-teeth / natural / K3 做樣本
scene = next(s for s in data["scenes"] if s["id"]=="brushing-teeth")
block = scene["sets"]["natural"]["K3"]
sample_manifest = {"brushing-teeth-sample": {"vocab": [], "dialogue": []}}
count = 0
# 輸出 raw PCM? Gemini 回傳係 PCM/L16。要轉 wav。但先睇能唔能生成。
# Gemini inlineData 通常係 audio/L16;24000 PCM -> 存 .wav
import struct
def pcm_to_wav(pcm, rate=24000):
    n = len(pcm)
    hdr = b'RIFF' + struct.pack('<I', 36+n) + b'WAVEfmt ' + struct.pack('<IHHIIHH',16,1,1,rate,rate*2,2,16) + b'data' + struct.pack('<I', n)
    return hdr + pcm

for i, d in enumerate(block["dialogue"]):
    pcm = synth(d["en"], d.get("who","Mama"))
    fn = f"audio/sample-{i}.wav"
    with open(fn, "wb") as out:
        out.write(pcm_to_wav(pcm))
    sample_manifest["brushing-teeth-sample"]["dialogue"].append(fn)
    count += 1
    print(f"[OK] sample-{i} ({d['who']}): {d['en']}")

with open("sample_manifest.json","w",encoding="utf-8") as f:
    json.dump(sample_manifest, f, ensure_ascii=False, indent=2)
print(f"Done. Generated {count} Gemini-TTS sample files (WAV).")

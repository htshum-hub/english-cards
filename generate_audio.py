#!/usr/bin/env python3
# build: mama-compare
"""MAMA VOICE COMPARISON: same mama line, 4 Gemini female voices, pick youngest/warmest."""
import os, json, base64, requests, time, struct
from google.oauth2 import service_account
from google.auth.transport.requests import Request

PROJECT = "english-cards-tts"
REGION = "global"
MODEL = "gemini-2.5-flash-tts"
ENDPOINT = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/publishers/google/models/{MODEL}:generateContent"

sa_info = json.loads(os.environ["GCP_SA_KEY"])
creds = service_account.Credentials.from_service_account_info(
    sa_info, scopes=["https://www.googleapis.com/auth/cloud-platform"])
creds.refresh(Request())
TOKEN = creds.token

MAMA_PROMPT = "Read aloud in a warm, gentle, young-mother tone, soft and loving."
MAMA_TEXT = "Come on, sweetie, it's time to brush your teeth."
CANDIDATES = ["Aoede", "Callirrhoe", "Leda", "Despina"]

os.makedirs("audio", exist_ok=True)

def synth(text, voice, prompt):
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt + " " + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    for attempt in range(3):
        r = requests.post(ENDPOINT, json=body, headers=headers, timeout=90)
        if r.status_code == 200:
            b64 = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            return base64.b64decode(b64)
        if r.status_code in (429, 500, 503):
            time.sleep(3 * (attempt + 1)); continue
        raise RuntimeError(f"TTS {r.status_code}: {r.text[:400]}")
    raise RuntimeError("failed")

def pcm_to_wav(pcm, rate=24000):
    n = len(pcm)
    return b'RIFF' + struct.pack('<I', 36 + n) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16) + b'data' + struct.pack('<I', n) + pcm

for v in CANDIDATES:
    pcm = synth(MAMA_TEXT, v, MAMA_PROMPT)
    fn = f"audio/mama-{v}.wav"
    with open(fn, "wb") as out:
        out.write(pcm_to_wav(pcm))
    print(f"[OK] mama-{v}.wav")
print("Done. 4 mama voice samples generated.")

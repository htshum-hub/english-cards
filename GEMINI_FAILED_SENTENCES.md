# Gemini TTS 持續失敗句子記錄（存案）

**日期**：2026-09-27
**現象**：以下句子用 Gemini TTS (`gemini-2.5-flash-tts`) 生成時持續回傳空 audio（`'parts'` missing / empty-parts），經 12 次 retry × 多次觸發仍失敗。並非偶發，屬 Gemini preview 模型對呢幾句特定文字嘅硬限制（睇唔出明顯敏感字）。

**處理**：暫時用 Chirp3-HD (Kore) 補齊，令平台 100% 有 Google 靚聲。

**日後改良**：當 Gemini TTS 模型更新（或轉用 `gemini-3.1-flash-tts` 正式版），可重試以下句子，若成功則用 Gemini 版覆蓋 Chirp3-HD 版，保持全平台語音一致。

## 失敗句子清單（全部為女兒 Girl 聲）

| 檔案 | 場景 | 級別 | 句子 |
|------|------|------|------|
| brushing-teeth-natural-P1-line-5 | 刷牙 | P1 | "Look at all the bubbles in my mouth!" |
| brushing-teeth-natural-P2-line-5 | 刷牙 | P2 | "My mouth is all foamy now, like a bubble bath!" |
| breakfast-story-P2-line-6 | 早餐 | P2 | "Okay, that does smell really tempting…" |
| breakfast-story-P2-line-8 | 早餐 | P2 | "Mmm! It's so soft and the sugar melts on my tongue!" |
| getting-dressed-natural-P1-line-11 | 著衫 | P1 | "I love getting dressed all by myself!" |
| bath-time-story-P1-line-2 | 沖涼 | P1 | "It gurgles and I might go down it!" |

## 已補回（之前 8 句中 2 句 Gemini 重試成功）
- brushing-teeth-natural-P1-line-6 (Mama) — Gemini 成功
- bedtime-story-K3-line-2 (Girl, "Maybe there's a monster under my bed!") — Gemini 成功

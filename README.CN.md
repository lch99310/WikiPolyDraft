# WikiPolyDraft

<h2 align="center">WikiPolyDraft —— AI 輔助維基百科翻譯草稿工具</h2>

![](pic.png)

<p align="center">
  <a href="README.md">English</a> | 中文
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-v0.3a-brightgreen">
  <img alt="License" src="https://img.shields.io/badge/licence-MIT-blue">
  <img alt="Audience" src="https://img.shields.io/badge/audience-維基百科編輯-orange">
  <img alt="Status" src="https://img.shields.io/badge/output-僅產出草稿-red">
</p>

> **一篇條目。兩種語言。一份尊重規則、也尊重審核者的草稿。**

WikiPolyDraft 把一個維基百科網址，轉成一份**可供審核的翻譯草稿** —— 附帶 CC BY-SA 授權標註、幻覺檢查清單，以及已預先放好的 `{{LLM-assisted translation}}` 模板。它**不會替你發佈**。這正是重點。

---

## ⚠️ 先讀這段

**本工具只產出「草稿」，不是「可直接發佈的條目」。**

- 維基百科政策要求：所有翻譯內容必須由**精通雙語的人類編輯**審核後才能發佈。**本工具不替代該審核流程。**
- 作者**並非**維基媒體基金會或任何維基百科社群的成員。
- 作者對任何透過本工具發佈的內容**不承擔任何責任**。使用者必須自行確認符合維基百科政策、著作權法、與 CC BY-SA 4.0 授權。
- 把未經審核的 AI 翻譯直接推進維基百科正式條目空間，**違反社群守則**（見 [Wikipedia:LLM-assisted translation](https://en.wikipedia.org/wiki/Wikipedia:LLM-assisted_translation)），可能導致帳號被處分。

如果你想找一鍵「翻譯+發佈」的機器人，這不是你要的工具 —— 而我們也不會做那種工具。

---

## 為什麼做這個

同一個主題的維基百科條目，在不同語言版本之間經常落差很大。英文版可能是 8000 字的精選條目；中文版可能只有三段、甚至根本沒有。志工自然會用自己的母語編輯，於是世界的知識在不同語言版本間分佈得很不平均。

LLM **可以**幫忙縮小這個落差 —— 但前提是：**人類編輯必須留在流程裡**，而且工具要讓他們審核更輕鬆，而不是更累。WikiPolyDraft 圍繞這個約束來設計：

- 每份草稿都帶有 **DRAFT 警示橫幅**與 `reviewed=no` 標記，讓它不會被誤認為已完成的內容。
- 每份草稿都附一份 **`review-notes.md`**，列出該優先檢查什麼 —— 疑似幻覺的段落、低信心的章節、HEAD 檢查失敗的引用網址。
- CLI **沒有 `--publish` 旗標**。它無法呼叫維基百科的編輯 API。

第一階段支援 **英文 ↔ 中文**。

---

## 你會得到什麼

| 它做什麼 | 你得到什麼 |
|--------|---------|
| **同時抓兩邊** | 來源條目的 wikitext + 已有的目標語言條目（如果存在），讓 LLM 看得到「對面已經寫了什麼」 |
| **逐章節翻譯** | 章節層級的提示詞讓上下文乾淨，方便你重新翻一個章節而不用整篇重來 |
| **與既有條目對齊** | 如果目標語言已有殘篇，會給你一份逐章節的合併計畫 —— 保留、取代、或合併 |
| **自動產生 CC BY-SA 文件** | 附來源 permalink 的編輯摘要 + 給討論頁用的 `{{Translated page}}`，授權需要的兩樣都備好 |
| **標示要檢查什麼** | `review-notes.md` 列出疑似幻覺、低信心章節，以及（可選）每個沒回 200 的引用網址 |
| **拒絕發佈** | 設計上就沒有 `--publish` 旗標、也沒有編輯 API 用戶端 |

---

## 快速上手

### 安裝

```bash
pip install -e .
# 或，如果要用 Anthropic 獨立模式：
pip install -e ".[anthropic]"
```

### 三步驟（Agent 驅動模式，建議）

在 Claude Code、Codex CLI 或任何能讀取提示檔、寫回結果的 agent host 內執行。

**1. Prepare —— 抓來源 + 目標，產生提示詞檔**

```bash
wiki-translate prepare https://en.wikipedia.org/wiki/Brett_Whiteley \
  --target zh --out ./wt-work
```

**2. Translate —— 你的 agent 讀 `./wt-work/prompts/*.txt`，把結果寫到 `./wt-work/translations/`**

對話裡跟它說：*「請翻譯 `./wt-work` 裡的提示檔」* 就行。

**3. Finalize —— 組裝草稿 + 授權標註 + 審核筆記**

```bash
wiki-translate finalize ./wt-work --out ./output
```

### 獨立模式（不需要 agent host，自備 API key）

```bash
export ANTHROPIC_API_KEY=sk-...
wiki-translate translate https://en.wikipedia.org/wiki/Brett_Whiteley \
  --target zh --out ./output
```

---

## `output/<title>/` 裡會有什麼

| 檔案 | 用途 |
|---|---|
| `<title>.wikitext` | 翻譯後的草稿，已加上 `{{LLM-assisted translation\|reviewed=no}}` 與 DRAFT 橫幅 |
| `edit-summary.txt` | 含來源 permalink、可直接複製貼上的編輯摘要（CC BY-SA 必備） |
| `talk-template.txt` | 給條目討論頁用的 `{{Translated page}}` 模板（CC BY-SA 必備） |
| `review-notes.md` | 疑似幻覺、低信心章節、來源驗證結果 |

**先打開 `review-notes.md`。** DRAFT 橫幅和 `reviewed=no` 是雙保險：如果哪天草稿不小心被丟進正式條目空間，維護分類至少能讓其他編輯看見它。

---

## 它是怎麼運作的

```
URL
  ↓
[prepare]   抓 wikitext + 語言連結 → 切章節 → 產生提示詞
  ↓
[translate] （agent 或 standalone LLM 讀提示詞、寫回逐章節草稿）
  ↓
[finalize]  組裝 → 加上 CC BY-SA 標註 + DRAFT 橫幅 →
            交叉檢查引用 → 寫入 review-notes.md
  ↓
人類編輯審核 → 人類編輯發佈
```

兩種 LLM 模式：

- **Agent 驅動（預設）。** CLI 產生提示詞檔；agent host（Claude Code、Codex 等）在對話中讀檔、翻譯、寫回結果。不需要 API key，可即時微調，人類自然留在流程裡。
- **獨立模式。** CLI 直接呼叫 LLM API。目前支援 Anthropic；OpenAI / Gemini 規劃中。需自備 API key。

### 當目標語言已經有殘篇時的章節對齊

如果來源條目有語言連結指向既有的目標語言條目，`prepare` 還會：

1. 把該目標條目也抓下來。
2. 寫一份覆蓋率報告骨架。
3. 產生 `_alignment.prompt.txt` 給 agent —— *來源的哪些章節對應到目標的哪些既有章節？*

翻譯結束後，`finalize` 會把對齊結果寫進覆蓋率報告，並產生**逐章節合併計畫**：保留既有目標文字、用翻譯取代、或合併。加上 `--check-urls` 還可以對每個引用網址做 HEAD 檢查，把失敗項丟進 `review-notes.md`。

---

## 實際成果 —— 巴蘭加魯（en → zh，已發佈）

一個用 WikiPolyDraft 從頭做到尾、已發佈到中文維基百科的真實案例：

- **來源條目**：[Barangaroo, New South Wales](https://en.wikipedia.org/wiki/Barangaroo,_New_South_Wales)（en.wikipedia.org）
- **發佈後的中文條目**：[巴蘭加魯 (新南威爾斯州)](https://zh.wikipedia.org/wiki/%E5%B7%B4%E8%98%AD%E5%8A%A0%E9%AD%AF_(%E6%96%B0%E5%8D%97%E5%A8%81%E7%88%BE%E6%96%AF%E5%B7%9E))（zh.wikipedia.org）

工具在這個案例裡幫忙處理掉的事：`{{Infobox Australian place}}` 的所有參數乾淨地翻譯成中文版、用對了 `{{langx|en|...}}` 而不是英文的 `{{lang-en|...}}`、逐章節合併計畫讓既有中文殘篇的 lead 被保留下來，其他章節則從英文版重新展開。CC BY-SA 編輯摘要 + 討論頁的 `{{Translated page}}` 都是自動產出的。

<br>
<div style="display: flex; flex-wrap: nowrap; justify-content: center; align-items: center; gap: 16px;">
  <img src="english.png" style="height: 250px; width: auto; max-width: 48%; object-fit: contain;">
  <img src="chinese.png" style="height: 250px; width: auto; max-width: 48%; object-fit: contain;">
</div>
<br>

---

## 維基百科政策合規

本工具圍繞 [Wikipedia:LLM-assisted translation](https://en.wikipedia.org/wiki/Wikipedia:LLM-assisted_translation) 設計：

1. 輸出是**草稿**；人類編輯必須精通雙語才能驗證。
2. 自動插入 `{{LLM-assisted translation}}` 模板。
3. `review-notes.md` 突顯編輯必須檢查的項目（幻覺、來源、引用）。
4. 自動產生 CC BY-SA 4.0 所需的授權標註 —— 編輯摘要 + 討論頁的 `{{Translated page}}`。
5. CLI **沒有 `--publish` 旗標**，也不呼叫維基百科編輯 API。

---

## 專案狀態

早期 —— v0.3a。流程已可端對端跑完，安全機制都到位，三個範例都能離線重現。對於落差極大的條目，章節對齊還會有粗糙的地方。歡迎提交 PR 來改進翻譯品質、擴充語言對、或強化審核輔助功能。

**不歡迎**：加入「自動發佈到維基百科」功能的 PR。詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 授權

MIT —— 見 [LICENSE](LICENSE)。翻譯後的條目內容繼承維基百科的 CC BY-SA 4.0 授權。

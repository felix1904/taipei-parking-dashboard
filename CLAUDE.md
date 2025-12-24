# 台北停車場分析儀表板

## 專案目的
這是一個 **Streamlit 儀表板**，用於視覺化呈現台北市停車場的歷史使用率資料。
**最終目標**：透過分析 5 年歷史資料，了解停車場營運績效，提升未來標案投標的財務預測準確度。

## 使用者背景
- 使用者是停車場營運承包商，管理約 300 個停車設施
- **沒有程式設計、資料分析、Google Cloud 經驗**
- 需要詳細的步驟說明，不要假設使用者知道任何技術細節

---

## 系統架構

### 資料來源（與本 Repo 無關）
- 資料收集是透過 **BigQuery 內建功能**（如 Scheduled Queries）執行
- 每 5 分鐘自動抓取台北市 706 個停車場的即時空位資料
- 資料儲存在 BigQuery 的 `taipei_parking` 資料集

### 本 Repo 的用途
- **只負責讀取和視覺化資料**，不負責資料收集
- 使用 Streamlit 建立互動式儀表板
- 部署在 Streamlit Cloud

---

## 技術架構

### 系統組成
| 元件 | 用途 |
|------|------|
| Streamlit Cloud | 部署儀表板 |
| BigQuery | 資料來源（只讀取，不寫入） |
| Plotly | 圖表視覺化 |

### BigQuery 資料表
- **專案 ID**: `parking-history-taipei`
- **資料集**: `taipei_parking`

### 資料表結構 (Schema)

#### parking_lots（停車場基本資料）
| 欄位 | 類型 | 說明 |
|------|------|------|
| parking_lot_id | STRING | 停車場代碼（如 TPE0410） |
| name | STRING | 停車場名稱 |
| area | STRING | 所在區域 |
| total_cars | INTEGER | 汽車總車位數 |
| total_motor | INTEGER | 機車總車位數 |

#### realtime_spots（即時車位快照）
| 欄位 | 類型 | 說明 |
|------|------|------|
| parking_lot_id | STRING | 停車場代碼 |
| available_cars | INTEGER | 汽車剩餘空位 |
| record_time | TIMESTAMP | 資料記錄時間（UTC） |

---

## 時區注意事項
- BigQuery 儲存的時間是 **UTC 時間**
- 台灣是 **UTC+8**
- 程式碼中使用 `DATETIME(record_time, 'Asia/Taipei')` 轉換

---

## 儀表板功能

1. **指標卡片**：平均剩餘車位、最高/最低剩餘、尖峰時段、週間vs週末比較
2. **趨勢圖**：可切換 5 分鐘 ~ 4 小時粒度
3. **時段分析**：各小時平均使用率長條圖
4. **每日比較**：每日使用率，週末用不同顏色標示
5. **熱力圖**：日期 × 時段的使用率矩陣
6. **週間 vs 週末曲線**：24 小時使用率對比

---

## 目前狀態

> 最後更新：2025-12-25 15:30

### 已完成功能
- ✅ Sidebar 表單化：使用 `st.form()` 包裝，需按「更新圖表」按鈕才觸發查詢
- ✅ 熱力圖改為「星期 × 時段」維度，顯示平均值
- ✅ 熱力圖可切換「使用率」與「剩餘車位」
- ✅ 缺失資料顯示灰色空白
- ✅ 週間 vs 週末曲線已優化（放大字體、白色文字、完整時段標籤）
- ✅ 修復 secrets.toml 格式問題（private_key 需用單行 + `\n` 格式）
- ✅ 更新 Streamlit Cloud 的 Secrets 設定
- ✅ 輪換 GCP 金鑰
- ✅ 圖表排版重構：統一使用 `st.subheader()` 標題、`st.container()` 分組
- ✅ X/Y 軸標籤放大、白色文字（size=16）
- ✅ Plotly 工具列設定一直顯示
- ✅ 側邊欄排版優化：統一字型、白色文字、按鈕漸層背景
- ✅ 指標卡片統一高度、備註字體放大

### 已知問題
- 無

### 待辦事項
- 無

### 交接文件
- 詳見 `docs/handoff/` 目錄

---

## 檔案說明

| 檔案 | 用途 |
|------|------|
| `app.py` | Streamlit 儀表板主程式 |
| `requirements.txt` | Python 套件清單 |
| `CLAUDE.md` | 給 Claude Code 看的專案說明 |
| `.cursorrules` | 給 Cursor 看的專案說明 |

---

## 部署資訊

### Streamlit Cloud 部署
- 儀表板部署在 Streamlit Cloud
- 需要在 Streamlit Cloud 設定 `secrets.toml`，包含 GCP 服務帳號憑證

### Secrets 設定格式
```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
# ... 其他欄位
```

---

## 回答規範

當使用者詢問或要求修改時：
1. 先解釋「為什麼」要這樣做
2. 提供完整的程式碼，不要只給片段
3. 用繁體中文加上註解
4. 如果有更簡單的方法，主動告知
5. 使用繁體中文，不要使用簡體中文

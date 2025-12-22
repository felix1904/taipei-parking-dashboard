# 台北停車場資料收集系統

## 專案目的
這是一個自動化資料收集系統，用於收集台北市停車場的即時車位資料。
**最終目標**：累積 5 年歷史資料，用於分析停車場營運績效，提升未來標案投標的財務預測準確度。

## 使用者背景
- 使用者是停車場營運承包商，管理約 300 個停車設施
- **沒有程式設計、資料分析、Google Cloud 經驗**
- 需要詳細的步驟說明，不要假設使用者知道任何技術細節
- 修改程式碼後，請提醒需要重新部署到 Cloud Functions

---

## 技術架構

### 系統組成
| 元件 | 用途 |
|------|------|
| Cloud Functions | 執行 app.py，抓取 API 資料 |
| Cloud Scheduler | 每 5 分鐘觸發 Cloud Function |
| BigQuery | 儲存所有歷史資料 |

### BigQuery 資料表
- **專案 ID**: 需要根據實際專案填入
- **資料集**: `taipei_parking`
- **資料表**: `realtime_spots`

### 資料表結構 (Schema)
```
id              STRING      停車場代碼（如 TPE0410）
availablecar    INTEGER     汽車剩餘空位
availablemotor  INTEGER     機車剩餘空位  
availablebus    INTEGER     大客車剩餘空位
fetched_at      TIMESTAMP   資料抓取時間（UTC 時間）
```

### 資料分區
- 使用 `fetched_at` 欄位做每日分區 (Daily Partitioning)
- 查詢時務必加上時間範圍條件，避免掃描全部資料

---

## 資料來源

### 即時車位 API
```
https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json
```
- 回傳 706 個停車場的即時空位資料
- 更新頻率：約每幾分鐘

### 停車場基本資料 API（尚未整合）
```
https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json
```
- 包含停車場名稱、地址、總車位數等靜態資料
- 計畫用於建立「停車場名稱對照表」

---

## 重要注意事項

### 時區問題
- API 回傳的時間是 **UTC 時間**
- 台灣是 **UTC+8**
- 查詢時需要轉換：`TIMESTAMP_ADD(fetched_at, INTERVAL 8 HOUR)`

### 資料品質
- `availablecar = -9` 表示該停車場目前無法提供資料（需過濾）
- 部分停車場可能只有汽車位或只有機車位

### 部署流程
修改 app.py 後，需要重新部署到 Cloud Functions：
```bash
gcloud functions deploy 函數名稱 \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --source .
```

---

## 已知問題與待辦事項

### 待完成
- [ ] 建立停車場名稱對照表（使用 TCMSV_alldesc.json）
- [ ] 時區轉換處理
- [ ] 錯誤通知機制（Cloud Monitoring）
- [ ] Power BI 儀表板連接

### 重點停車場
- **花木批發市場 (TPE0410)**：411 汽車位、352 機車位

---

## 回答規範

當使用者詢問或要求修改時：
1. 先解釋「為什麼」要這樣做
2. 提供完整的程式碼，不要只給片段
3. 用繁體中文加上註解
4. 說明修改後需要做什麼（例如重新部署）
5. 如果有更簡單的方法，主動告知

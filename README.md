# 台北停車場資料收集系統

## 這是什麼？

這個系統會自動收集台北市 706 個停車場的即時空位資料，每 5 分鐘抓一次，存到 Google BigQuery 資料庫。

## 為什麼要做這個？

累積 5 年的歷史資料，分析每個停車場的：

- 尖峰/離峰時段使用率
- 平日/假日差異
- 月營收趨勢

這些資料可以幫助我們在投標新停車場時，做出更準確的財務預測。

## 系統架構圖

```
┌─────────────────┐     每5分鐘觸發      ┌─────────────────┐
│ Cloud Scheduler │ ──────────────────► │ Cloud Function  │
└─────────────────┘                      │   (app.py)      │
                                         └────────┬────────┘
                                                  │
                                                  ▼ 抓取資料
                                         ┌─────────────────┐
                                         │  台北市停車API   │
                                         └────────┬────────┘
                                                  │
                                                  ▼ 儲存資料
                                         ┌─────────────────┐
                                         │    BigQuery     │
                                         │ taipei_parking  │
                                         └─────────────────┘
```

## 檔案說明

| 檔案               | 用途                        |
| ------------------ | --------------------------- |
| `app.py`           | Cloud Function 主程式       |
| `requirements.txt` | Python 套件清單             |
| `CLAUDE.md`        | 給 Claude Code 看的專案說明 |
| `.cursorrules`     | 給 Cursor 看的專案說明      |

## 如何修改程式？

1. 用 Cursor 或 Claude Code 開啟這個資料夾
2. AI 會自動讀取說明文件，了解專案背景
3. 告訴 AI 你想要修改什麼
4. 修改後記得重新部署到 Cloud Functions

## 重新部署指令

```bash
gcloud functions deploy 你的函數名稱 \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --source .
```

## 相關連結

- [BigQuery Console](https://console.cloud.google.com/bigquery)
- [Cloud Functions Console](https://console.cloud.google.com/functions)
- [Cloud Scheduler Console](https://console.cloud.google.com/cloudscheduler)# taipei-parking-dashboard

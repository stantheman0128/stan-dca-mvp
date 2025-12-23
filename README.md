# DCA Strategy Backtesting Tool
定期定額策略回測工具

## 簡介

本工具用於回測和分析不同的定期定額（Dollar-Cost Averaging, DCA）投資策略變化，並評估其在不同市場和時間條件下的穩健性。

## 功能特點

- ✅ 5 種 DCA 策略變化（純 DCA、跌深加碼、趨勢過濾、波動率調整、定期減碼）
- ✅ 20 年歷史數據回測（2005-2025）
- ✅ 跨市場測試（美股、台股、國際市場）
- ✅ 完整績效指標（報酬、風險、風險調整報酬）
- ✅ 互動式 Plotly 圖表
- ✅ 統計顯著性檢驗
- ✅ PDF/Excel 報告導出

## 快速開始

### 系統需求

- Python 3.8+
- 8GB RAM（推薦）
- 網路連線（用於下載數據）

### 安裝

```bash
# 克隆或下載本專案
git clone https://github.com/stantheman0128/stan-dca-mvp.git
cd stan-dca-mvp

# 安裝依賴
pip install -r requirements.txt
```

### 執行

```bash
# 啟動應用
streamlit run app.py
```

然後在瀏覽器開啟顯示的 URL（通常是 http://localhost:8501）

## 使用指南

### 基本使用流程

1. 在左側邊欄選擇標的資產（如 SPY）
2. 設定回測時間範圍
3. 選擇要測試的策略（可多選）
4. 調整策略參數（可選）
5. 點擊「開始回測」
6. 查看結果和圖表
7. 導出報告（PDF/Excel）

### 策略說明

| 策略 | 名稱 | 描述 |
|------|------|------|
| V0 | 純定期定額 | 每期固定投入，不考慮市場狀況（基準線） |
| V1 | 跌深加碼 | 價格大跌時增加投入 |
| V2 | 趨勢過濾 | 價格低於均線時加碼 |
| V3 | 波動率調整 | 高波動時加碼，低波動時減碼 |
| V5 | 定期減碼 | 獲利達標時部分獲利了結 |

## 專案結構

```
dca_backtest_tool/
├── app.py                     # 主應用入口
├── requirements.txt           # 依賴套件
├── config.yaml               # 配置文件
├── README.md                 # 專案說明
├── strategies/               # 策略模組
│   ├── base_strategy.py     # 基礎策略類
│   ├── dca_pure.py          # V0: 純 DCA
│   ├── dca_dip_buying.py    # V1: 跌深加碼
│   ├── dca_trend_filter.py  # V2: 趨勢過濾
│   ├── dca_volatility.py    # V3: 波動率調整
│   └── dca_profit_taking.py # V5: 定期減碼
├── core/                     # 核心功能
│   ├── data_loader.py       # 數據管理
│   ├── backtest_engine.py   # 回測引擎
│   ├── metrics.py           # 指標計算
│   ├── statistics.py        # 統計檢驗
│   └── visualizer.py        # 視覺化
├── utils/                    # 工具函數
│   └── report_generator.py  # 報告生成
└── tests/                    # 測試文件
```

## 技術架構

- **數據來源**: Yahoo Finance (yfinance)
- **數據處理**: pandas, numpy
- **視覺化**: Plotly（互動式圖表）
- **統計**: scipy（t檢驗等）
- **UI**: Streamlit
- **報告**: openpyxl (Excel), reportlab (PDF)

## 常見問題

### Q: 數據下載失敗怎麼辦？
A: 檢查網路連線，確認標的代碼正確。系統有自動重試機制和本地緩存。

### Q: 支援哪些市場？
A: 支援所有 Yahoo Finance 可查詢的市場，包括美股、台股、國際股市、ETF 等。

## 授權

MIT License

## 作者

Stan

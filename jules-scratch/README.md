# 統一截圖腳本

## 概覽

本目錄包含一個統一的截圖腳本 `screenshot_all.py`，整合了所有截圖功能，取代了原本四個獨立的腳本：

- ~~`screenshot_pages.py`~~ - 已整合到 `screenshot_all.py`
- ~~`screenshot_modals.py`~~ - 已整合到 `screenshot_all.py`  
- ~~`screenshot_by_role.py`~~ - 已整合到 `screenshot_all.py`
- ~~`create_gif.py`~~ - 已整合到 `screenshot_all.py`

## 安裝需求

```bash
pip install playwright
playwright install chromium
```

## 使用方式

### 執行所有截圖任務（推薦）
```bash
python screenshot_all.py
```

### 僅執行特定類型的截圖
```bash
python screenshot_all.py --pages-only     # 僅頁面截圖
python screenshot_all.py --modals-only    # 僅模態框截圖  
python screenshot_all.py --roles-only     # 僅角色權限截圖
python screenshot_all.py --gif-only       # 僅 GIF 幀捕獲
```

### 其他選項
```bash
python screenshot_all.py --show-browser      # 顯示瀏覽器視窗（用於調試）
python screenshot_all.py --width 1920 --height 1080  # 自定義視窗大小
python screenshot_all.py --help              # 查看所有選項
```

## 功能說明

### 1. 頁面截圖 (`--pages-only`)
- 截取所有主要頁面的完整畫面
- 包含特殊頁面的標籤切換（自動化執行日誌、設定通知標籤等）
- 輸出到：`screenshot_pages/`

### 2. 模態框截圖 (`--modals-only`)
- 截取各種模態框和彈出視窗
- 包含通知下拉選單、表單彈窗、確認對話框等
- 輸出到：`screenshot_modals/`

### 3. 角色權限截圖 (`--roles-only`)
- 以不同角色（admin、manager、member）登入
- 截取每個角色可見的頁面
- 驗證權限控制的正確性
- 輸出到：`screenshot_by_role/verification/`

### 4. GIF 幀捕獲 (`--gif-only`)
- 捕獲關鍵操作流程的截圖幀
- 可用於製作演示 GIF 動畫
- 輸出到：`gif_frames/`

## 如何更新 demo.gif

### 步驟一：產生畫面幀
```bash
python screenshot_all.py --gif-only
```

### 步驟二：合成 GIF 動畫

使用 ImageMagick 將幀合成為 GIF：

**安裝 ImageMagick**：
- **macOS (Homebrew)**: `brew install imagemagick`
- **Debian/Ubuntu**: `sudo apt-get install imagemagick`

**合成 GIF**：
```bash
convert -delay 80 -loop 0 jules-scratch/gif_frames/frame_*.png -resize 1440x900 demo.gif
```

## 優勢

✅ **統一管理**：一個腳本處理所有截圖需求  
✅ **無重複代碼**：共享通用函數和邏輯  
✅ **更好的錯誤處理**：統一的異常處理機制  
✅ **靈活執行**：可選擇執行特定類型的截圖  
✅ **更清晰的輸出**：結構化的日誌和進度提示  

## 輸出結構

執行完成後，將在以下目錄生成截圖：

```
jules-scratch/
├── screenshot_pages/           # 頁面截圖
├── screenshot_modals/          # 模態框截圖
├── screenshot_by_role/         # 角色權限截圖
│   └── verification/
└── gif_frames/                 # GIF 動畫幀
```

## 舊版腳本

舊版的獨立腳本仍然保留在目錄中，但建議使用新的統一腳本 `screenshot_all.py`：
- `screenshot_pages.py` 
- `screenshot_modals.py`
- `screenshot_by_role.py` 
- `create_gif.py`

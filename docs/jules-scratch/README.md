# 自動化截圖腳本說明

這個目錄包含了三個 Python 腳本，用於自動化截取 `demo-page.html` 的各個頁面和彈出視窗。

## 環境設定

在執行腳本之前，請確保您已經安裝了 Playwright。

```bash
pip install playwright
playwright install
```

## 腳本說明

### 步驟一：產生畫面幀

首先，執行 `screenshot.py` 腳本來產生所有動畫需要的畫面。

```bash
python3 docs/jules-scratch/screenshot.py
```

#### 步驟二：合成 GIF 動畫

產生完畫面後，需要使用 `ImageMagick` 工具來將所有 `.png` 圖片合成為一個 GIF 檔案。

**依賴工具**：請先確保您已安裝 ImageMagick。
- **macOS (Homebrew)**: `brew install imagemagick`
- **Debian/Ubuntu**: `sudo apt-get install imagemagick`

執行以下指令來合成 `demo.gif`，這個指令會將 `gif_frames` 目錄中的所有圖片打包成 `demo.gif` 並存放在專案根目錄。

```bash
convert -delay 80 -loop 0 docs/jules-scratch/gif_frames/frame_*.png -resize 1440x900 demo.gif
```

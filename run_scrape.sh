#!/bin/bash
cd ~/xiaohongshu-ops/MediaCrawler
export PATH="$HOME/.local/bin:$PATH"
export no_proxy="localhost,127.0.0.1"
export XHS_SOCKS_PROXY="socks5://127.0.0.1:1086"
uv run python main.py \
    --platform xhs \
    --type search \
    --lt qrcode \
    --keywords "作品集辅导,作品集机构,留学作品集,留学作品集辅导,艺术生留学,交互设计留学,数媒作品集,作品集排版,设计留学" \
    --save_data_option csv \
    --headless false \
    --get_comment false

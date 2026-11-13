# 神农本草经视频工作室

葛根 V7 的可复用基版。保留最终认可的精细黑白植物插画、少量红色重点、直接地图标注、节点脉冲/描线/流光、无旁白配乐和按内容安排的阅读时间。

## 先看成品

- [葛根 V7 完整成片（2分21秒）](reference-output/001-gegen-approved-v7.mp4)
- [地图动效预览（14秒）](reference-output/001-gegen-map-preview.mp4)
- [封面](episodes/001-gegen/assets/cover.png)
- [27镜头正文、参数及来源索引](episodes/001-gegen/episode.json)

## 快速开始

需要 Python 3.11+、FFmpeg/ffprobe。无需大模型 API、剪映账号或 macOS，即可用已有素材再次渲染。

```bash
# macOS: brew install ffmpeg
# Ubuntu/Debian: sudo apt-get install ffmpeg
# Windows: 从 FFmpeg 官方网站安装，并将 ffmpeg/ffprobe 加入 PATH
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/studio.py doctor episodes/001-gegen/episode.json --font-profile portable --check-hashes
python scripts/studio.py storyboard episodes/001-gegen/episode.json --font-profile portable --out build/gegen/storyboard.png
python scripts/studio.py render episodes/001-gegen/episode.json --font-profile portable --out build/gegen/film.mp4
```

只检查地图段，可用 `render ... --start 42.083333 --end 56 --out build/gegen/map.mp4`。也可安装 `pip install -e .` 后使用 `bencao` 命令。脚本以自身所在项目为根目录，输入素材不依赖调用者当前目录。

## 文件分工

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | 任意模型/agent 的入口，Claude/Gemini 入口指向它 |
| `skills/herbal-encyclopedia-video/` | 系列 skill、封面、分类编号和直接标注规则 |
| `episodes/001-gegen/episode.json` | 正文、时长、布局、地图路径、数字、原图裁切与资料索引 |
| `episodes/001-gegen/assets/` | 整株、四格插画和最终封面原始文件 |
| `assets/` | 完整地图、用户选定候选配乐、可分发 Noto 全量字体及许可证 |
| `src/shennong_studio/` | 数据驱动的原生帧合成、地图动效、音轨剪辑和导出 |
| `prompts/`、`docs/tools.md` | 换模型时的生成提示词、工具映射和操作方法 |
| `provenance/assets.json` | 文件 SHA-256、来源和素材范围 |
| `reference-output/` | 用户认可的基准成片，便于跨 agent 对照 |

## 下一味药

```bash
python scripts/studio.py new 菖蒲 --slug 002-changpu
```

新目录默认 `draft`，不会把葛根事实直接改名套用。按 [新一期流程](docs/next-episode.md) 核对底本、生成当期插画、填来源和布局参数，再设置 `ready`。现有布局不是完整中药事实库；遇到新知识结构可增加布局，不能硬套葛根专属的根/葛粉逻辑。

## 字体与复现范围

本仓库带 Noto CJK 全量开源字体。`portable` 可跨平台离线渲染；`auto` 在有相同 macOS 系统字体时使用原片字体，否则用 Noto。已确认的 V7 MP4 是视觉基准；不同字体和 FFmpeg 版本会有字宽或编码差异，不承诺逐字节一致。macOS 专有字体没有拷入仓库。

## 素材和发布

仓库现已公开。[素材与权限](docs/assets-and-rights.md) 分别说明 AI 插画、官方供图、开源字体、配乐和成片。候选配乐的公开/商业使用权限未核实，不能因仓库可复制便推定所有素材都可公开再分发。原始地图完整保留，画面下方没有另加来源行；资料出处仍在随附文件中。新专题标注层未取得独立公开审图认可。

不设置定时任务，不自动发布到短视频平台。知识内容保留古籍、现代规范与研究证据的区别。

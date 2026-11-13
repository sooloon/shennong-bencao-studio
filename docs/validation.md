# 验证入口

```bash
python scripts/studio.py doctor episodes/001-gegen/episode.json --font-profile portable --check-hashes
python -m unittest discover -s tests -v
python scripts/studio.py storyboard episodes/001-gegen/episode.json --font-profile portable --out build/check.png
python scripts/studio.py render episodes/001-gegen/episode.json --font-profile portable --start 42.083333 --end 56 --out build/map-check.mp4
```

看原片时关注封面、古籍定位、当前资料版本、单位与比例、地图完整性、标注与对象关系、文字裁切、节奏、音轨。对新一期必须逐项核对自己的资料；测试通过不等于医学审查或已获公开地图审核。

基版的实际验证结果另记 `provenance/validation.json`。不将静态抽帧检查说成真人受众测试。

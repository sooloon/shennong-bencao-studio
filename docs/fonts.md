# 字体

`portable` 使用随项目分发的 NotoSerifCJKsc-Black.otf 与 NotoSansCJKsc-Medium.otf，许可证与来源在同目录。全量字体避免后续药名的缺字问题。字体内部名称未修改。

`auto` 若同时存在原片使用的 macOS Songti 和 Heiti，则使用系统字体；否则使用 portable。macOS 字体不会进入仓库。需要指定其他已安装字体时，可通过 `SHENNONG_FONT_SERIF`、`SHENNONG_FONT_SANS` 指定本机路径；变量值不应提交。

doctor 会检查 portable 下场景文本所用字形；不同字体的宽度可能不同，仍须看分镜图。参考成片不是跨平台逐像素或逐字节一致的承诺。

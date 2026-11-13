# 布局参数

布局坐标以720×1280为基准，当前导出24fps。已有每种布局的完整 payload 可在 `episodes/001-gegen/episode.json` 中直接查找。

| layout | 用途与 data |
|---|---|
| cover | 显示本期封面原图 |
| art_text / zoom / cloth / end | 插画与正文；由 asset 选图 |
| parts | 插画两个部位标注，labels 两项；坐标当前是葛根范例，换结构应改布局 |
| wordpop | words 四项：两个主词及各自解释 |
| leafcount | points、summary；仅用于有依据的结构数量 |
| bookindex | volume、category、entries（三行）、active |
| bookquote | book、entry、quote、alias_prefix、alias、source_note |
| oldterm / boundary | left、right 的非等同关系 |
| oldmodern | old_label、old、new_label、new、note |
| mapplaces | locations 的 label、label_position、path；summary、scope |
| mapcultivation | path、label_position、label、year、quantity_label、value、unit |
| toslice | from_asset、to_asset、label |
| plainpop | lines 两项；asset 选主体 |
| carousel | cards 三项，每项为 [asset,文字] |
| origins | columns 两项，每项为 [横坐标,名称,来源] |
| namecompare / twoPowders | left_asset、right_asset、columns 两项 [名称,说明] |
| steps | steps 四步；不要为适应布局编造加工步骤 |
| counter | value、prefix、suffix、decimals、note |
| grid | quantity（0–100）、unit、prefix、note、part_note；百格表示100个单位 |
| compound | columns 三项 [名称,类别] |
| pack | fields 三项 [名称,横坐标]、active |
| recap | steps 三项、active |
| measure | measurements 最多两项，每项 label、value、unit，图上尺寸需有来源 |

这是葛根效果的可编辑布局库，不是任意长文本自适应排版系统。字数变长或改物种后，需要用实际预览检查遮挡和字形，必要时改坐标/布局。百格是量化单元；普通标签不因此再加边框。

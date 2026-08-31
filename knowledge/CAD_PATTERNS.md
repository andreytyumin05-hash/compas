# Паттерны построения

- Сплошной контур → extrude; пунктир → отверстие/скрытое, не стенка.
- Одинаковые отверстия по кругу → `pattern_holes_circular`.
- Ступени вала/пробки → несколько `circle` + `extrude`.
- Карман/шестигранник → `polygon`/`pocket` + `cut(depth=)`.
- Цековка → `counterbore`; канавка → `ring_groove`.
- Кромки в конце: `get_edges` + fillet/chamfer.

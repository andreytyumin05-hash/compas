# Patterns (text-first parametric)

## Штуцер / ступенчатый вал
part.param D1,L1,D2,L2,D3,L3,D_inner — каждая ступень: circle(p(Di)/2)+extrude(p(Li)); hole; groove; chamfer.

## Втулка
D_outer, D_inner, L → extrude + hole

## Лопасть
sk.spline([...]) on xz; loft later when real API exists.

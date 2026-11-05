import json, sys, uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
ttf, out = sys.argv[1:3]
TEXT, SIZE, TRACK = "elliott.yaga.sh", 16.0, -0.16
f = TTFont(ttf); gs = f.getGlyphSet(); order = f.getGlyphOrder(); upem = f['head'].unitsPerEm
face = hb.Face(hb.Blob.from_file_path(ttf)); font = hb.Font(face)
buf = hb.Buffer(); buf.add_str(TEXT); buf.guess_segment_properties(); hb.shape(font, buf, {"kern": True})
k = SIZE / upem; x = 0.0; parts = []
def fmt(v): return f"{v:.2f}".rstrip('0').rstrip('.')
for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
    pen = SVGPathPen(gs, ntos=fmt)
    gs[order[info.codepoint]].draw(TransformPen(pen, (k, 0, 0, -k, x + pos.x_offset * k, 0)))
    parts.append(pen.getCommands()); x += pos.x_advance * k + TRACK
os2 = f['OS/2']
json.dump({"d": "".join(parts), "width": round(x - TRACK, 2), "x_height": round(os2.sxHeight * k, 2), "cap": round(os2.sCapHeight * k, 2)}, open(out, 'w'))
print(round(x, 2), os2.sxHeight * k, f['name'].getDebugName(4), len("".join(parts)))

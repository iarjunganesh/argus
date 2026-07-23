"""Augments the ARGUS architecture SVG with traveling pulse dots along
edges to simulate request/response flow, for GIF capture."""
import re

SVG_PATH = "assets/argus-architecture.svg"
OUT_HTML = "assets/argus-architecture-animated.html"

CYCLE = 8.8  # seconds, full loop

# (edge_id, start_s, end_s, color)
STAGES = [
    ("my-svg-L_Human_ORC_0", 0.0, 1.0, "#F97316"),
    ("my-svg-L_ORC_IDA_0", 1.0, 2.2, "#F97316"),
    ("my-svg-L_ORC_SCA_0", 1.0, 2.2, "#F97316"),
    ("my-svg-L_ORC_CIA_0", 1.0, 2.2, "#F97316"),
    ("my-svg-L_ORC_TIA_0", 1.0, 2.2, "#F97316"),
    ("my-svg-L_SCA_T2_0", 1.8, 2.6, "#8b5cf6"),
    ("my-svg-L_T2_FIQ_0", 2.6, 3.4, "#8b5cf6"),
    ("my-svg-L_IDA_ORC_0", 2.2, 3.4, "#22c55e"),
    ("my-svg-L_SCA_ORC_0", 2.2, 3.4, "#22c55e"),
    ("my-svg-L_CIA_ORC_0", 2.2, 3.4, "#22c55e"),
    ("my-svg-L_TIA_ORC_0", 2.2, 3.4, "#22c55e"),
    ("my-svg-L_ORC_CRA_0", 3.4, 4.4, "#F97316"),
    ("my-svg-L_CRA_T4_0", 4.0, 4.8, "#8b5cf6"),
    ("my-svg-L_T4_FIQ_0", 4.8, 5.6, "#8b5cf6"),
    ("my-svg-L_CRA_ORC_0", 4.4, 5.6, "#22c55e"),
    ("my-svg-L_ORC_Human_0", 5.6, 6.8, "#0078D4"),
]


def build():
    svg = open(SVG_PATH, encoding="utf-8").read()

    dots = []
    for edge_id, start, end, color in STAGES:
        if f'id="{edge_id}"' not in svg:
            print("WARNING missing edge id:", edge_id)
            continue
        t0 = max(0.0, start / CYCLE - 0.003)
        t1 = start / CYCLE
        t2 = end / CYCLE
        t3 = min(1.0, end / CYCLE + 0.003)
        dots.append(f'''
  <circle r="9" fill="{color}" stroke="white" stroke-width="2" opacity="0">
    <animateMotion dur="{CYCLE}s" repeatCount="indefinite"
      keyPoints="0;0;1;1" keyTimes="0;{t1:.5f};{t2:.5f};1" calcMode="linear">
      <mpath href="#{edge_id}"/>
    </animateMotion>
    <animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite"
      values="0;0;1;1;0;0" keyTimes="0;{t0:.5f};{t1:.5f};{t2:.5f};{t3:.5f};1"/>
  </circle>''')

    injected = svg.replace("</svg>", "\n".join(dots) + "\n</svg>")

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:#ffffff;}}</style>
</head><body>{injected}</body></html>"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", OUT_HTML, "with", len(dots), "pulse dots")


if __name__ == "__main__":
    build()

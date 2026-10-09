"""Static SVG preview of the coverage x pressure xComp grid for the README. Pure Python."""
import json, os
HERE=os.path.dirname(__file__)
P=json.load(open(os.path.join(HERE,"xcomp_outputs.json")))

def color(rate):
    stops=[(0.40,(192,57,43)),(0.60,(217,179,16)),(0.75,(27,120,60))]
    if rate<=stops[0][0]: c=stops[0][1]
    elif rate>=stops[-1][0]: c=stops[-1][1]
    else:
        c=stops[-1][1]
        for i in range(len(stops)-1):
            x0,c0=stops[i]; x1,c1=stops[i+1]
            if x0<=rate<=x1:
                t=(rate-x0)/(x1-x0); c=tuple(round(c0[k]+t*(c1[k]-c0[k])) for k in range(3)); break
    return f"rgb({c[0]},{c[1]},{c[2]})"

byCov={}
for r in P["grid"]:
    byCov.setdefault(r["coverage"],{})[r["press"]]=r
order=sorted(byCov, key=lambda c:(byCov[c].get(0) or byCov[c].get(1))["xcomp"])

rowh=34; x0=160; cw=120; y0=70
W=x0+cw*3+20; H=y0+rowh*len(order)+30
s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Arial" style="background:#0e1116">']
s.append(f'<text x="20" y="30" fill="#e6edf3" font-size="18" font-weight="bold">Expected Completion by Coverage × Pressure</text>')
s.append(f'<text x="20" y="50" fill="#8b949e" font-size="12">mean xComp · clean vs pressured · 2021 (NGS + PFF)</text>')
for j,lab in enumerate(["Clean","Pressured","Δ pressure"]):
    s.append(f'<text x="{x0+cw*j+cw/2}" y="{y0-8}" fill="#8b949e" font-size="12" text-anchor="middle">{lab}</text>')
for i,cov in enumerate(order):
    cy=y0+rowh*i
    s.append(f'<text x="{x0-12}" y="{cy+rowh/2+4}" fill="#e6edf3" font-size="13" text-anchor="end" font-weight="bold">{cov}</text>')
    clean=byCov[cov].get(0); pres=byCov[cov].get(1)
    for j,r in enumerate([clean,pres]):
        cx=x0+cw*j
        if not r:
            s.append(f'<rect x="{cx}" y="{cy}" width="{cw-4}" height="{rowh-4}" fill="#161b22"/>'); continue
        s.append(f'<rect x="{cx}" y="{cy}" width="{cw-4}" height="{rowh-4}" fill="{color(r["xcomp"])}"/>')
        s.append(f'<text x="{cx+(cw-4)/2}" y="{cy+rowh/2+4}" fill="#06240f" font-size="14" font-weight="bold" text-anchor="middle">{r["xcomp"]*100:.0f}%</text>')
    cx=x0+cw*2
    if clean and pres:
        drop=(clean["xcomp"]-pres["xcomp"])*100
        s.append(f'<text x="{cx+(cw-4)/2}" y="{cy+rowh/2+4}" fill="#ff7b72" font-size="13" font-weight="bold" text-anchor="middle">-{drop:.0f} pp</text>')
s.append('</svg>')
os.makedirs(os.path.join(HERE,"docs"),exist_ok=True)
out=os.path.join(HERE,"docs","screenshot.svg")
open(out,"w").write("\n".join(s))
print("wrote",out)

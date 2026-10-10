"""Download featured images from de-ware-wereld.com and compress them below a size limit."""
import csv, io, json, os, sys, urllib.request
from PIL import Image

SITE = "https://de-ware-wereld.com"
LIMIT = 200 * 1024        # alleen afbeeldingen groter dan dit aanpakken
TARGET = 190 * 1024       # doelgrootte na verkleinen
MAX_W = 1200
OUT = "geoptimaliseerd"
UA = {"User-Agent": "Mozilla/5.0 (DeWareWereld media optimizer)"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def compress(data):
    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    if img.width > MAX_W:
        img = img.resize((MAX_W, round(img.height * MAX_W / img.width)), Image.LANCZOS)
    for q in range(82, 49, -4):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= TARGET:
            break
    return buf.getvalue(), q, img.size

def main():
    # Regel: "<media_id>" of "<media_id> <source_url>" (URL nodig als het bericht nog niet gepubliceerd is)
    entries = {}
    for l in open("ids.txt"):
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        parts = l.split()
        entries[parts[0]] = parts[1] if len(parts) > 1 else None
    ids = list(entries)
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for mid in ids:
        try:
            if entries[mid]:
                src = entries[mid]
                meta = {"slug": os.path.splitext(os.path.basename(src))[0]}
                title = meta["slug"]
            else:
                meta = json.loads(get(f"{SITE}/wp-json/wp/v2/media/{mid}"))
                src = meta["source_url"]
                title = meta.get("title", {}).get("rendered", "")
            data = get(src)
            size = len(data)
            if size <= LIMIT:
                rows.append([mid, title, src, size, "", "", "overgeslagen (al klein genoeg)"])
                continue
            new, q, dims = compress(data)
            slug = meta.get("slug") or str(mid)
            name = f"{mid}-{slug}"[:80] + ".jpg"
            with open(os.path.join(OUT, name), "wb") as f:
                f.write(new)
            rows.append([mid, title, src, size, len(new), name, f"verkleind q{q} {dims[0]}x{dims[1]}"])
        except Exception as e:
            rows.append([mid, "", "", "", "", "", f"fout: {e}"])
        print(rows[-1], flush=True)
    with open("rapport.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["media_id", "titel", "origineel", "oud_bytes", "nieuw_bytes", "bestand", "status"])
        w.writerows(rows)

if __name__ == "__main__":
    main()

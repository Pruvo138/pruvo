#!/usr/bin/env python3
"""
Pruvo R2 görsel yükleyici.
Kimlik bilgileri repo kökündeki gitignore'lu .r2-credentials.json dosyasından okunur
(bu betiğin içinde SIR YOKTUR — public repo'ya güvenle commit edilebilir).

Kullanım:
    python3 tools/r2-upload.py <yerel_dosya> <r2_anahtari>
Örnek:
    python3 tools/r2-upload.py /tmp/x.jpg urunler/audi-parca-1.jpg
    -> https://media.pruvo3d.com/urunler/audi-parca-1.jpg

Birden fazla dosya için çift çift ver:
    python3 tools/r2-upload.py a.jpg urunler/a.jpg b.jpg urunler/b.jpg
"""
import sys, os, json, boto3

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", ".r2-credentials.json")

def main():
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2 != 0:
        print("Kullanim: r2-upload.py <yerel_dosya> <r2_anahtari> [<yerel> <anahtar> ...]")
        sys.exit(1)
    cfg = json.load(open(CFG_PATH))
    s3 = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret"],
        region_name="auto",
    )
    for i in range(0, len(args), 2):
        local, key = args[i], args[i + 1]
        with open(local, "rb") as f:
            s3.put_object(Bucket=cfg["bucket"], Key=key, Body=f.read(), ContentType="image/jpeg")
        print(cfg["public_base"] + "/" + key)

if __name__ == "__main__":
    main()

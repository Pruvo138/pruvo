# pruvo-onizleme derleyici imaji — Cloudflare Containers hedefi.
# KURAL: imaj PRIVATE registry'de kalir (icinde GIZLI paket var: eslem + .scad).
# Derleme CI'da: .github/workflows/onizleme-imaj.yml paketi gizli R2'den indirip
# paket-ozel/ dizinine acar, sonra bu Dockerfile'i build eder. paket-ozel/
# gitignore'ludur — imaj baglami disinda repoya girmez.
#
# Imaj kucuk tutulur (soguk baslatma!): debian-slim + yalniz openscad (nightly degil,
# depo surumu) + BOSL2 (sabit commit) + server.py. Gereksiz hicbir sey yok.

FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends openscad python3 ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# BOSL2 — sabitlenmis surum (uyelik uretecleri BOSL2 include eder).
# Takma ad ("latest") KULLANMA kurali geregi commit'e sabitlenir.
ARG BOSL2_SURUM=2.0.716
RUN mkdir -p /root/.local/share/OpenSCAD/libraries \
 && curl -sSL "https://github.com/BelfrySCAD/BOSL2/archive/refs/tags/v${BOSL2_SURUM}.tar.gz" \
    | tar -xz -C /root/.local/share/OpenSCAD/libraries \
 && mv "/root/.local/share/OpenSCAD/libraries/BOSL2-${BOSL2_SURUM}" \
       /root/.local/share/OpenSCAD/libraries/BOSL2

WORKDIR /srv
COPY server.py /srv/server.py
# GIZLI paket: CI R2'den indirir, buraya acar (eslem-ozel.json + *.scad).
COPY paket-ozel/ /srv/paket/

EXPOSE 8080
# Container icinde disariya acik generic HTTP; Worker binding uzerinden konusur.
CMD ["python3", "/srv/server.py", "--paket", "/srv/paket", "--port", "8080", "--adres", "0.0.0.0"]

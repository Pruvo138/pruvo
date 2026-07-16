# pruvo-onizleme derleyici imaji — Cloudflare Containers hedefi.
# KURAL: imaj PRIVATE registry'de kalir (icinde GIZLI paket var: eslem + .scad).
# Derleme CI'da: .github/workflows/onizleme-imaj.yml paketi gizli R2'den/secret'tan
# indirip paket-ozel/ dizinine acar, sonra bu Dockerfile'i build eder. paket-ozel/
# gitignore'ludur — imaj baglami disinda repoya girmez.
#
# OPENSCAD: resmi NIGHTLY AppImage, surume SABIT. Debian deposundaki openscad
# (2021.01) uretecleri DERLEYEMIYOR — 16 Tem canli olcum: o-ring derlendi, profil
# ailesi "derleme-hatasi" verdi; yerel kalibrasyon 2026 snapshot ile yapilmisti.
# Takma ad ("latest") KULLANMA kurali geregi dosya adiyla sabitlenir.

FROM debian:bookworm-slim

# AppImage'in (Qt tabanli, headless kosulur) calisma zamani kutuphaneleri.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 ca-certificates curl \
      libgl1 libglu1-mesa libglib2.0-0 libfontconfig1 libfreetype6 \
      libx11-6 libxext1 libxrender1 libxcb1 libxkbcommon0 libdbus-1-3 libegl1 \
      libharfbuzz0b libdouble-conversion3 libzstd1 \
 && rm -rf /var/lib/apt/lists/*

ARG OPENSCAD_DOSYA=OpenSCAD-2026.01.02.ai30348-x86_64.AppImage
RUN curl -sSL -o /tmp/openscad.AppImage "https://files.openscad.org/snapshots/${OPENSCAD_DOSYA}" \
 && chmod +x /tmp/openscad.AppImage \
 && cd /opt && /tmp/openscad.AppImage --appimage-extract > /dev/null \
 && rm /tmp/openscad.AppImage \
 && ln -s /opt/squashfs-root/AppRun /usr/local/bin/openscad

# Headless: GUI/soket yok, yazilim render.
ENV QT_QPA_PLATFORM=offscreen
ENV LIBGL_ALWAYS_SOFTWARE=1

# Kurulum dogrulamasi (build aninda patlasin, calisma aninda degil).
RUN openscad --version

# BOSL2 — sabitlenmis surum (uyelik uretecleri BOSL2 include eder).
# v2.0.747 = bu Mac'teki yerel kutuphaneyle AYNI surum (kalibrasyon 16 Tem bununla olculdu).
ARG BOSL2_SURUM=2.0.747
RUN mkdir -p /root/.local/share/OpenSCAD/libraries \
 && curl -sSL "https://github.com/BelfrySCAD/BOSL2/archive/refs/tags/v${BOSL2_SURUM}.tar.gz" \
    | tar -xz -C /root/.local/share/OpenSCAD/libraries \
 && mv "/root/.local/share/OpenSCAD/libraries/BOSL2-${BOSL2_SURUM}" \
       /root/.local/share/OpenSCAD/libraries/BOSL2

WORKDIR /srv
COPY server.py /srv/server.py
# GIZLI paket: CI R2'den/secret'tan indirir, buraya acar (eslem-ozel.json + *.scad).
COPY paket-ozel/ /srv/paket/

EXPOSE 8080
# Container icinde generic HTTP; Worker binding uzerinden konusur.
CMD ["python3", "/srv/server.py", "--paket", "/srv/paket", "--port", "8080", "--adres", "0.0.0.0"]

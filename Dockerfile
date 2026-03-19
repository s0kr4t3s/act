# 1. Base Image: openSUSE Tumbleweed
FROM opensuse/tumbleweed:latest

# 2. Systempakete installieren (Ohne SSH!)
RUN zypper refresh && \
    zypper --non-interactive install --no-recommends \
    python3 \
    python3-devel \
    python3-pip \
    gcc \
    gcc-c++ \
    make \
    git \
    curl \
    && zypper clean -a

# ==========================================
# SICHERHEITS-SETUP: Non-Root User anlegen
# ==========================================
# Wir erstellen einen Benutzer namens "user" mit der UID 1000 (Hugging Face Standard)
RUN useradd -m -u 1000 user

# Wir setzen das Arbeitsverzeichnis auf das Home-Verzeichnis des neuen Users
WORKDIR /home/user/app

# Wir übergeben die Besitzrechte des Ordners an den neuen User
RUN chown -R user:user /home/user/app

# Ab hier läuft alles als unprivilegierter User ab!
USER user

# 5. Python-Pakete sicher in den User-Space installieren
COPY --chown=user:user requirements.txt .
RUN python3 -m pip install --no-cache-dir --upgrade pip --break-system-packages && \
    python3 -m pip install --no-cache-dir --user -r requirements.txt --break-system-packages

# 6. Deinen restlichen Projektcode kopieren
COPY --chown=user:user . .

# Den Pfad anpassen, damit Linux die installierten Python-Programme (wie streamlit) findet
ENV PATH="/home/user/.local/bin:${PATH}"

# 7. Port freigeben
EXPOSE 7860

# Prüft alle 30s, ob die App auf Port 7860 reagiert. 
# Wenn 3-mal hintereinander keine Antwort kommt, gilt der Container als "unhealthy".
# Intervall auf 60 Sekunden erhöht
HEALTHCHECK --interval=60s --timeout=3s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:7860/_stcore/health || exit 1

# 8. Startbefehl ausführen (Direkter Aufruf, keine start.sh mehr nötig)
CMD ["python3", "-m", "streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
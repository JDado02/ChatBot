# Setup su un nuovo PC (per testare Ollama)

Guida per portare **tutto il progetto** su un altro computer — tipicamente più
potente, per far girare il modello LLM con **Ollama**. Il progetto vive su GitHub,
quindi "trasportarlo" significa **clonare il repo** e avviarlo: nessun file va
copiato a mano.

> ⏱️ Percorso rapido: installa i prerequisiti → clona → lancia lo script di setup.
> Chi usa Claude Code sul nuovo PC può far fare tutto a lui: vedi §6.

---

## 1. Requisiti hardware (per Ollama)

- **`bge-m3`** (embedding, ~1.2 GB) + **`llama3` 8B** (chat, ~4.7 GB) da scaricare.
- **RAM**: almeno **16 GB** consigliati per llama3 8B su CPU (8 GB è il minimo, lento).
- **GPU** (opzionale ma consigliata): una scheda con **≥6–8 GB di VRAM** rende la
  chat molto più veloce. Ollama usa la GPU in automatico se disponibile.
- **Disco**: ~10 GB liberi (immagini Docker + modelli).

---

## 2. Prerequisiti software

Servono: **Git**, **Docker Desktop**, **Python 3.11+**, **Ollama**.

**Windows (PowerShell, con winget):**
```powershell
winget install -e --id Git.Git
winget install -e --id Docker.DockerDesktop
winget install -e --id Python.Python.3.12
winget install -e --id Ollama.Ollama
```

**macOS (Homebrew):**
```bash
brew install git python@3.12
brew install --cask docker ollama
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt update && sudo apt install -y git python3 python3-pip docker.io docker-compose-plugin
curl -fsSL https://ollama.com/install.sh | sh
```

> Dopo aver installato Docker Desktop, **avvialo** e attendi che sia "running".
> Su Windows serve WSL2 attivo (Docker Desktop lo configura da solo).

---

## 3. Clonare il repository (è privato)

Il repo `JDado02/ChatBot` è **privato**: serve autenticarsi. Il modo più semplice
è il **GitHub CLI**:
```bash
# opzione A: GitHub CLI
gh auth login          # segui le istruzioni (browser)
gh repo clone JDado02/ChatBot
```
Oppure con HTTPS (ti verrà chiesto utente + un **Personal Access Token** come
password — crealo su github.com/settings/tokens, scope "repo"):
```bash
git clone https://github.com/JDado02/ChatBot.git
```
Poi entra nella cartella: `cd ChatBot`.

---

## 4. Setup automatico (consigliato)

Dalla radice del progetto:

**Windows:**
```powershell
.\scripts\setup.ps1 -WithOllama
# se bloccato dai criteri: powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -WithOllama
```
**Linux/macOS/Git-Bash:**
```bash
./scripts/setup.sh --with-ollama
```

Lo script: crea `.env`, avvia i container, attende Postgres "healthy", esegue il
**test isolamento RLS** (atteso 4× PASS), installa le dipendenze del backend e
lancia i **98 test**, e — con `--with-ollama`/`-WithOllama` — scarica i modelli e
genera gli embedding reali. Salta Ollama se non è installato (te lo segnala).

### Oppure: passi manuali
```bash
cp .env.example .env
docker compose up -d && docker compose ps          # attendi "healthy"
./db/test/run_isolation_test.sh                     # 4x PASS
cd backend && pip install -r requirements.txt && pytest   # 98 passed
ollama pull bge-m3 && ollama pull llama3
python scripts/generate_embeddings.py hotel_alpha hotel_beta
```

---

## 5. Avviare e provare (con l'AI vera)

```bash
# 1) API (terminale 1)
cd backend && uvicorn app.api.main:app --reload      # http://localhost:8000/docs

# 2) Widget (terminale 2)
python -m http.server 5500 --directory widget        # http://localhost:5500
```

- **Widget in modalità LIVE**: apri **http://localhost:5500/?mode=live** e chatta.
  Con Ollama attivo ora risponde davvero (es. "A che ora è la colazione?").
- **API diretta**: da `/docs` prova `/api/session` (`X-API-Key: pk_alpha_dev_0001`)
  → token → `/api/search`, `/api/chat`.

Se qualcosa non torna, vedi la [guida test](GUIDA_TEST_E_PROSSIMI_PASSI.md).

---

## 6. Per Claude Code (setup automatico)

Sul nuovo PC, apri Claude Code nella cartella del progetto e incolla:

> «Leggi `CLAUDE.md` e `docs/SETUP_NUOVO_PC.md`. Poi esegui il **setup automatico**:
> avvia Docker Desktop se non è attivo, lancia `./scripts/setup.sh --with-ollama`
> (o `.\scripts\setup.ps1 -WithOllama` su Windows) e risolvi eventuali errori.
> Se mancano Docker/Python/Ollama installali (winget/brew/apt). Alla fine
> **verifica** che: il test isolamento dia 4× PASS, i 98 test passino, l'API
> risponda su `/health`, e `ollama list` mostri `bge-m3` e `llama3`. Infine
> genera gli embedding reali e dimmi come provare il widget in `?mode=live`.»

Claude farà i passi in autonomia e ti dirà se qualcosa richiede la tua conferma
(es. installazioni di sistema).

---

## Note

- **GDPR/privacy**: tutto resta locale (Ollama gira sulla tua macchina); nessun
  dato esce verso servizi esterni.
- **Segreti**: `.env` non è nel repo (è in `.gitignore`); lo ricrei dal template.
  In produzione cambia `SESSION_SECRET` e le password.
- **Multi-computer**: a inizio sessione fai sempre `git pull`, a fine `git push`
  (la fonte di verità è GitHub).

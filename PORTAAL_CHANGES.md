# Portaal-kant: aanpassingen

## 1. Database-migratie

```bash
ssh streamlit@vps
cd /home/streamlit/apps/login
sqlite3 schoolapp.db < portaal_migratie.sql
```

## 2. `database.py` — tegel-query voor docenten uitbreiden

Zoek de functie die tegels voor een docent ophaalt (waarschijnlijk
`get_tegels_voor_docent` of vergelijkbaar). De query was iets als:

```sql
SELECT t.* FROM tegels t
JOIN docent_tegels dt ON dt.tegel_id = t.id
WHERE dt.eckid = ?
```

Maak er een UNION van zodat ook de `is_docent_default = 1` tegels meekomen:

```python
def get_tegels_voor_docent(eckid: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT t.* FROM tegels t
        JOIN docent_tegels dt ON dt.tegel_id = t.id
        WHERE dt.eckid = ?
        UNION
        SELECT t.* FROM tegels t
        WHERE t.is_docent_default = 1
        ORDER BY naam
        """,
        (eckid,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

(als de huidige query er anders uitziet: laat me 'm zien, dan pas ik 'm aan)

## 3. Restart

```bash
sudo systemctl restart streamlit-login
```

## 4. Subapp deployen

Op de VPS, naast de andere subapps:

```bash
cd /home/streamlit/apps
git clone <jouw-fork-url> doorstroom
cd doorstroom
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# .env aanmaken — PORTAAL_JWT_SECRET MOET identiek zijn aan die van portaal
cp .env.example .env
nano .env
```

Nieuwe systemd-unit `/etc/systemd/system/streamlit-doorstroom.service`:

```ini
[Unit]
Description=Streamlit Doorstroomanalyse
After=network.target

[Service]
User=streamlit
WorkingDirectory=/home/streamlit/apps/doorstroom
EnvironmentFile=/home/streamlit/apps/doorstroom/.env
ExecStart=/home/streamlit/apps/doorstroom/venv/bin/streamlit run Start.py \
    --server.port=8503 \
    --server.address=127.0.0.1 \
    --server.headless=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Plus een nginx-blok dat `doorstroom.bovenbouwsucces.nl` naar `127.0.0.1:8503` proxy't,
zoals voor de andere subapps. Daarna:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now streamlit-doorstroom
sudo systemctl status streamlit-doorstroom
```

# Progetto Basi di Dati - Noleggio Veicoli

Applicazione web Django per la gestione di un servizio di noleggio veicoli. Il progetto include area cliente, area amministratore e gestione staff, con database SQLite gia popolato e documentazione del modello dati.

## Funzionalita principali

- Registrazione e login degli utenti.
- Catalogo dei veicoli disponibili con filtri per tipo, cambio e cabrio.
- Prenotazione di auto, scooter, barche e bici elettriche.
- Visualizzazione e annullamento delle prenotazioni del cliente.
- Dashboard amministratore con statistiche, rientri e incassi.
- Gestione veicoli, clienti, prenotazioni, pagamenti e contratti.
- Accesso staff alla sezione contratti.
- Pagina `/docs/` con descrizione del modello concettuale e logico.

## Tecnologie usate

- Python
- Django
- SQLite
- HTML template Django
- CSS personalizzato

## Struttura del progetto

```text
.
|-- manage.py
|-- noleggio.db
|-- noleggio_dump.sql
|-- noleggio_project/
|   |-- settings.py
|   |-- urls.py
|   |-- asgi.py
|   `-- wsgi.py
|-- rental/
|   |-- models.py
|   |-- views.py
|   |-- utils.py
|   |-- migrations/
|   `-- templatetags/
|-- static/
|   `-- style.css
|-- templates/
|-- Noleggio_Veicoli_DB.pptx
`-- RELAZIONE PROGETTO DI BASI DI DATI.docx
```

## Avvio in locale

1. Clonare il repository:

```bash
git clone https://github.com/vincenzocennamo1/Progetto_Basi_dati_Noleggio.git
cd Progetto_Basi_dati_Noleggio
```

2. Creare e attivare un ambiente virtuale:

```bash
python -m venv .venv
```

Su Windows:

```bash
.venv\Scripts\activate
```

Su macOS/Linux:

```bash
source .venv/bin/activate
```

3. Installare Django:

```bash
pip install Django
```

4. Applicare le migration:

```bash
python manage.py migrate
```

5. Avviare il server:

```bash
python manage.py runserver
```

6. Aprire il browser su:

```text
http://127.0.0.1:8000/
```

## Database

Il progetto usa il database SQLite `noleggio.db`, gia incluso nel repository. Il file contiene dati di esempio per utenti, veicoli, prenotazioni, contratti e pagamenti.

E' incluso anche `noleggio_dump.sql`, utile per consultare o ricreare lo schema e i dati iniziali.

Le tabelle principali sono:

- `Utente`
- `Staff`
- `Veicolo`
- `Prenotazione`
- `Contratto`

## Ruoli applicativi

L'applicazione gestisce tre ruoli:

- `cliente`: consulta i veicoli, effettua prenotazioni e controlla lo stato delle proprie richieste.
- `admin`: gestisce veicoli, clienti, prenotazioni, pagamenti e riepiloghi.
- `staff`: gestisce la stipula dei contratti assegnati.

Gli utenti di esempio sono gia presenti nel database. Le password sono salvate come hash PBKDF2 nella tabella `Utente`.

## Materiali del progetto

Nel repository sono presenti anche:

- `RELAZIONE PROGETTO DI BASI DI DATI.docx`: relazione del progetto.
- `Noleggio_Veicoli_DB.pptx`: presentazione del progetto.
- `noleggio_dump.sql`: dump SQL del database.

## Note

I modelli Django dell'app `rental` usano tabelle gia esistenti nel database SQLite. Per questo motivo le classi in `rental/models.py` sono impostate con `managed = False`: Django legge e usa le tabelle, ma non le ricrea automaticamente.

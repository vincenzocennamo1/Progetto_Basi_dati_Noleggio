from django.db import models


class Utente(models.Model):
    id_utente = models.AutoField(db_column="idUtente", primary_key=True)
    nome = models.TextField()
    cognome = models.TextField(blank=True, null=True)
    mail = models.TextField(unique=True, blank=True, null=True)
    telefono = models.TextField(blank=True, null=True)
    password_hash = models.TextField(blank=True, null=True)
    tipo = models.TextField()

    class Meta:
        managed = False
        db_table = "Utente"


class Veicolo(models.Model):
    id_veicolo = models.AutoField(db_column="idVeicolo", primary_key=True)
    marca = models.TextField()
    modello = models.TextField()
    colore = models.TextField()
    prezzo_giornaliero = models.FloatField()
    stato = models.TextField()
    tipo = models.TextField()
    cambio = models.TextField(blank=True, null=True)
    cabrio = models.IntegerField()
    targa = models.TextField(blank=True, null=True)
    cilindrata = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Veicolo"


class Prenotazione(models.Model):
    id_prenotazione = models.AutoField(db_column="idPrenotazione", primary_key=True)
    utente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="idUtente")
    veicolo = models.ForeignKey(Veicolo, models.DO_NOTHING, db_column="idVeicolo")
    tipo_ritiro = models.TextField()
    indirizzo_ritiro = models.TextField()
    data_inizio = models.TextField()
    data_fine = models.TextField()
    stato = models.TextField()
    costo_previsto = models.FloatField()
    cauzione_richiesta = models.FloatField()
    note = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Prenotazione"


class Staff(models.Model):
    id_staff = models.AutoField(db_column="idStaff", primary_key=True)
    utente = models.OneToOneField(Utente, models.DO_NOTHING, db_column="idUtente")
    ruolo = models.TextField()
    stipendio = models.FloatField()

    class Meta:
        managed = False
        db_table = "Staff"


class Contratto(models.Model):
    id_contratto = models.AutoField(db_column="idContratto", primary_key=True)
    prenotazione = models.ForeignKey(Prenotazione, models.DO_NOTHING, db_column="idPrenotazione")
    veicolo = models.ForeignKey(Veicolo, models.DO_NOTHING, db_column="idVeicolo")
    staff = models.ForeignKey(Staff, models.DO_NOTHING, db_column="idStaff", blank=True, null=True)
    data_stipula = models.TextField(blank=True, null=True)
    costo_totale = models.FloatField()
    cauzione_importo = models.FloatField()
    cauzione_stato = models.TextField()
    cauzione_data_pagamento = models.TextField(blank=True, null=True)
    saldo_importo = models.FloatField()
    saldo_stato = models.TextField()
    saldo_data_pagamento = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Contratto"

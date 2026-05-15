from django.db import models


class Utente(models.Model):
    id_utente = models.AutoField(db_column="idUtente", primary_key=True)
    password = models.TextField()
    nome_utente = models.TextField(unique=True)

    class Meta:
        managed = False
        db_table = "Utente"


class Cliente(models.Model):
    id_cliente = models.AutoField(db_column="idCliente", primary_key=True)
    nome = models.TextField()
    cognome = models.TextField()
    mail = models.TextField(unique=True)
    telefono = models.TextField()
    password_hash = models.TextField(blank=True, null=True)
    utente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="idUtente", blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Cliente"


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


class Ritiro(models.Model):
    id_ritiro = models.AutoField(db_column="idRitiro", primary_key=True)
    tipo = models.TextField()
    indirizzo = models.TextField()

    class Meta:
        managed = False
        db_table = "Ritiro"


class Prenotazione(models.Model):
    id_prenotazione = models.AutoField(db_column="idPrenotazione", primary_key=True)
    cliente = models.ForeignKey(Cliente, models.DO_NOTHING, db_column="idCliente")
    veicolo = models.ForeignKey(Veicolo, models.DO_NOTHING, db_column="idVeicolo")
    ritiro = models.ForeignKey(Ritiro, models.DO_NOTHING, db_column="idRitiro")
    data_inizio = models.TextField()
    data_fine = models.TextField()
    stato = models.TextField()
    costo_previsto = models.FloatField()
    cauzione_richiesta = models.FloatField()
    note = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Prenotazione"


class Pagamento(models.Model):
    id_pagamento = models.AutoField(db_column="idPagamento", primary_key=True)
    prenotazione = models.ForeignKey(Prenotazione, models.DO_NOTHING, db_column="idPrenotazione")
    tipo = models.TextField()
    importo = models.FloatField()
    stato = models.TextField()
    data_pagamento = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Pagamento"


class AdminAccount(models.Model):
    id_admin = models.AutoField(db_column="idAdmin", primary_key=True)
    nome = models.TextField()
    mail = models.TextField(unique=True)
    password_hash = models.TextField()

    class Meta:
        managed = False
        db_table = "Admin"

from __future__ import annotations

from datetime import date

from django.db import IntegrityError, connection, transaction
from django.http import FileResponse, HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings

from rental.models import AdminAccount, Cliente, Pagamento, Prenotazione, Ritiro, Utente, Veicolo
from rental.utils import adjusted_price, compute_cost, hash_password, money, scooter_engine, verify_password, vehicle_specs


def static_style(request: HttpRequest) -> HttpResponse:
    path = settings.BASE_DIR / "static" / "style.css"
    if not path.exists():
        return HttpResponseNotFound("CSS non trovato")
    return FileResponse(path.open("rb"), content_type="text/css; charset=utf-8")


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def html_options(values: list[str], current: str | None) -> str:
    labels = {"": "-", "0": "No", "1": "Si"}
    current = "" if current is None else str(current)
    return "".join(
        f'<option value="{escape(v)}" {"selected" if v == current else ""}>{escape(labels.get(v, v))}</option>'
        for v in values
    )


def csrf_input(request: HttpRequest) -> str:
    return f'<input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">'


def require_role(request: HttpRequest, role: str):
    if request.session.get("role") != role:
        return redirect("/login/")
    return None


def home(request: HttpRequest) -> HttpResponse:
    role = request.session.get("role")
    if role == "admin":
        return redirect("/admin/")
    if role == "cliente":
        return redirect("/veicoli/")
    return redirect("/login/")


def docs(request: HttpRequest) -> HttpResponse:
    return render(request, "docs.html", {"title": "Modello dati"})


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        identity = request.POST.get("identificativo", "").strip()
        password = request.POST.get("password", "")
        admin = AdminAccount.objects.filter(mail=identity).first()
        if admin and verify_password(password, admin.password_hash):
            request.session["role"] = "admin"
            request.session["id"] = admin.id_admin
            return redirect("/admin/")
        user = (
            Cliente.objects.select_related("utente")
            .filter(utente__nome_utente=identity)
            .first()
        )
        if user and user.utente and verify_password(password, user.utente.password):
            request.session["role"] = "cliente"
            request.session["id"] = user.id_cliente
            return redirect("/veicoli/")
        return redirect("/login/?errore=1")
    return render(request, "login.html", {"title": "Accesso al sistema", "action": "/login/"})


def admin_login_redirect(request: HttpRequest) -> HttpResponse:
    return redirect("/login/")


def logout_view(request: HttpRequest) -> HttpResponse:
    request.session.flush()
    return redirect("/")


@require_http_methods(["GET", "POST"])
def register(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        try:
            with transaction.atomic():
                utente = Utente.objects.create(
                    nome_utente=request.POST["nome_utente"],
                    password=hash_password(request.POST["password"]),
                )
                cliente = Cliente.objects.create(
                    nome=request.POST["nome"],
                    cognome=request.POST["cognome"],
                    mail=request.POST["mail"],
                    telefono=request.POST["telefono"],
                    utente=utente,
                )
            request.session["role"] = "cliente"
            request.session["id"] = cliente.id_cliente
            return redirect("/veicoli/")
        except IntegrityError:
            return redirect("/register/?errore=duplicato")
    return render(request, "register.html", {"title": "Registrazione"})


def vehicles(request: HttpRequest) -> HttpResponse:
    rows = Veicolo.objects.filter(stato="disponibile")
    tipo = request.GET.get("tipo", "")
    cambio = request.GET.get("cambio", "")
    cabrio = request.GET.get("cabrio", "")
    if tipo:
        rows = rows.filter(tipo=tipo)
    if cambio:
        rows = rows.filter(tipo="auto", cambio=cambio)
    if cabrio:
        rows = rows.filter(tipo="auto", cabrio=1 if cabrio == "si" else 0)
    return render(
        request,
        "veicoli.html",
        {
            "title": "Veicoli disponibili",
            "vehicles": rows.order_by("tipo", "marca", "modello"),
            "tipo": tipo,
            "cambio": cambio,
            "cabrio": cabrio,
        },
    )


@require_http_methods(["GET", "POST"])
def book(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "cliente")
    if blocked:
        return blocked
    if request.method == "POST":
        veicolo = get_object_or_404(Veicolo, pk=request.POST["idVeicolo"])
        try:
            days, total = compute_cost(request.POST["data_inizio"], request.POST["data_fine"], veicolo.prezzo_giornaliero)
            deposit = round(total * 0.35, 2) if days >= 3 else 0
            address = request.POST.get("indirizzo") or "Ritiro in sede"
            with transaction.atomic():
                ritiro = Ritiro.objects.create(tipo=request.POST["tipo_ritiro"], indirizzo=address)
                prenotazione = Prenotazione.objects.create(
                    cliente_id=request.session["id"],
                    veicolo=veicolo,
                    ritiro=ritiro,
                    data_inizio=request.POST["data_inizio"],
                    data_fine=request.POST["data_fine"],
                    stato="in_attesa",
                    costo_previsto=total,
                    cauzione_richiesta=deposit,
                    note=request.POST.get("note", ""),
                )
                Pagamento.objects.create(prenotazione=prenotazione, tipo="cauzione", importo=deposit, stato="richiesto")
                Pagamento.objects.create(prenotazione=prenotazione, tipo="saldo", importo=max(total - deposit, 0), stato="richiesto")
            return redirect("/prenotazioni/")
        except (ValueError, IntegrityError) as exc:
            return HttpResponseBadRequest(str(exc))
    veicolo = get_object_or_404(Veicolo, pk=request.GET.get("idVeicolo"))
    return render(request, "prenota.html", {"title": "Prenota", "veicolo": veicolo})


def my_reservations(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "cliente")
    if blocked:
        return blocked
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.*, v.marca, v.modello, v.tipo,
                   SUM(CASE WHEN pay.tipo='cauzione' AND pay.stato='pagato' THEN pay.importo ELSE 0 END) cauzione_pagata,
                   SUM(CASE WHEN pay.tipo='saldo' AND pay.stato='pagato' THEN pay.importo ELSE 0 END) saldo_pagato
            FROM Prenotazione p
            JOIN Veicolo v ON v.idVeicolo = p.idVeicolo
            LEFT JOIN Pagamento pay ON pay.idPrenotazione = p.idPrenotazione
            WHERE p.idCliente = ?
            GROUP BY p.idPrenotazione
            ORDER BY p.data_inizio DESC
            """,
            [request.session["id"]],
        )
        rows = dictfetchall(cursor)
    return render(request, "prenotazioni.html", {"title": "Le mie prenotazioni", "rows": rows})


@require_POST
def cancel_reservation(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "cliente")
    if blocked:
        return blocked
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE Prenotazione
            SET stato = 'rifiutata',
                note = COALESCE(note || char(10), '') || 'Prenotazione annullata dal cliente'
            WHERE idPrenotazione = ?
              AND idCliente = ?
              AND stato IN ('in_attesa', 'accettata')
            """,
            [request.POST["idPrenotazione"], request.session["id"]],
        )
        cursor.execute(
            """
            UPDATE Pagamento
            SET stato = CASE WHEN stato = 'pagato' THEN 'rimborsato' ELSE stato END
            WHERE idPrenotazione = ?
            """,
            [request.POST["idPrenotazione"]],
        )
    return redirect("/prenotazioni/")


def admin_dashboard(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    selected_date = request.GET.get("rientro", date.today().isoformat())
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM Prenotazione WHERE stato='in_attesa') attesa,
                (SELECT COUNT(*) FROM Veicolo) veicoli,
                (SELECT COUNT(*) FROM Cliente) clienti,
                (SELECT COALESCE(SUM(importo), 0) FROM Pagamento WHERE stato='pagato') incassi
            """
        )
        stats = dictfetchall(cursor)[0]
        cursor.execute(
            """
            SELECT pay.tipo, pay.importo, pay.data_pagamento,
                   p.idPrenotazione, p.stato,
                   c.nome, c.cognome,
                   v.marca, v.modello
            FROM Pagamento pay
            JOIN Prenotazione p ON p.idPrenotazione = pay.idPrenotazione
            JOIN Cliente c ON c.idCliente = p.idCliente
            JOIN Veicolo v ON v.idVeicolo = p.idVeicolo
            WHERE pay.stato = 'pagato'
            ORDER BY COALESCE(pay.data_pagamento, '' ) DESC, p.idPrenotazione DESC, pay.tipo
            """
        )
        credited = dictfetchall(cursor)
        cursor.execute(
            """
            SELECT p.idPrenotazione, p.data_inizio, p.data_fine, p.stato,
                   p.costo_previsto, c.nome, c.cognome, c.mail, c.telefono,
                   v.marca, v.modello, v.tipo, v.targa, v.cilindrata, r.tipo AS tipo_ritiro, r.indirizzo
            FROM Prenotazione p
            JOIN Cliente c ON c.idCliente = p.idCliente
            JOIN Veicolo v ON v.idVeicolo = p.idVeicolo
            JOIN Ritiro r ON r.idRitiro = p.idRitiro
            WHERE p.data_fine = ?
              AND p.stato <> 'rifiutata'
            ORDER BY v.tipo, v.marca, v.modello
            """,
            [selected_date],
        )
        returns = dictfetchall(cursor)
    return render(
        request,
        "admin.html",
        {"title": "Admin", "stats": stats, "credited": credited, "returns": returns, "rientro": selected_date},
    )


def admin_vehicles(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    rows = Veicolo.objects.all()
    tipo = request.GET.get("tipo", "")
    stato = request.GET.get("stato", "")
    if tipo:
        rows = rows.filter(tipo=tipo)
    if stato:
        rows = rows.filter(stato=stato)
    return render(
        request,
        "admin_veicoli.html",
        {"title": "Gestione veicoli", "vehicles": rows.order_by("-id_veicolo"), "tipo_filter": tipo, "stato_filter": stato},
    )


@require_POST
def admin_vehicle_add(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    veicolo = Veicolo.objects.create(
        marca=request.POST["marca"],
        modello=request.POST["modello"],
        colore=request.POST["colore"],
        prezzo_giornaliero=adjusted_price(request.POST),
        stato=request.POST["stato"],
        tipo=request.POST["tipo"],
        targa=request.POST.get("targa") or None,
        cilindrata=scooter_engine(request.POST),
        cambio=request.POST.get("cambio") or None,
        cabrio=int(request.POST.get("cabrio", "0")),
    )
    veicolo.save()
    return redirect("/admin/veicoli/")


@require_POST
def admin_vehicle_update(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    current = get_object_or_404(Veicolo, pk=request.POST["idVeicolo"])
    current.targa = request.POST.get("targa") or None
    current.marca = request.POST["marca"]
    current.modello = request.POST["modello"]
    current.colore = request.POST["colore"]
    current.prezzo_giornaliero = adjusted_price(request.POST, current)
    current.stato = request.POST["stato"]
    current.tipo = request.POST["tipo"]
    current.cambio = request.POST.get("cambio") or None
    current.cabrio = int(request.POST.get("cabrio", "0"))
    current.cilindrata = scooter_engine(request.POST)
    current.save()
    return redirect("/admin/veicoli/")


@require_POST
def admin_vehicle_delete(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    try:
        Veicolo.objects.filter(pk=request.POST["idVeicolo"]).delete()
    except IntegrityError:
        pass
    return redirect("/admin/veicoli/")


def admin_reservations(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    rows = Prenotazione.objects.select_related("cliente", "veicolo", "ritiro").order_by("-id_prenotazione")
    return render(request, "admin_prenotazioni.html", {"title": "Gestione prenotazioni", "reservations": rows})


@require_POST
def admin_reservation_update(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    deposit = float(request.POST["cauzione_richiesta"])
    payment_date = date.today().isoformat() if request.POST["stato"] == "accettata" else None
    reservation = get_object_or_404(Prenotazione, pk=request.POST["idPrenotazione"])
    balance = max(float(reservation.costo_previsto) - deposit, 0)
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE Prenotazione SET stato = ?, cauzione_richiesta = ? WHERE idPrenotazione = ?",
            [request.POST["stato"], deposit, request.POST["idPrenotazione"]],
        )
        cursor.execute(
            "UPDATE Pagamento SET importo = ? WHERE idPrenotazione = ? AND tipo = 'cauzione'",
            [deposit, request.POST["idPrenotazione"]],
        )
        cursor.execute(
            "UPDATE Pagamento SET importo = ? WHERE idPrenotazione = ? AND tipo = 'saldo'",
            [balance, request.POST["idPrenotazione"]],
        )
        if request.POST["stato"] == "accettata":
            cursor.execute(
                """
                UPDATE Pagamento
                SET stato = 'pagato',
                    data_pagamento = COALESCE(data_pagamento, ?)
                WHERE idPrenotazione = ?
                  AND tipo = 'saldo'
                """,
                [payment_date, request.POST["idPrenotazione"]],
            )
    return redirect("/admin/prenotazioni/")


def admin_payments(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    pren_id = request.GET.get("idPrenotazione", "")
    rows = Pagamento.objects.filter(prenotazione_id=pren_id).order_by("tipo")
    return render(request, "admin_pagamenti.html", {"title": "Pagamenti", "payments": rows, "id": pren_id})


@require_POST
def admin_payment_update(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    data = date.today().isoformat() if request.POST["stato"] == "pagato" else None
    Pagamento.objects.filter(pk=request.POST["idPagamento"]).update(stato=request.POST["stato"], data_pagamento=data)
    return redirect("/admin/prenotazioni/")


def admin_customers(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.*, COUNT(p.idPrenotazione) prenotazioni, COALESCE(SUM(p.costo_previsto), 0) totale
            FROM Cliente c
            LEFT JOIN Prenotazione p ON p.idCliente = c.idCliente
            GROUP BY c.idCliente
            ORDER BY c.cognome, c.nome
            """
        )
        rows = dictfetchall(cursor)
    return render(request, "admin_clienti.html", {"title": "Clienti", "customers": rows})

from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from django.db import IntegrityError, connection, transaction
from django.http import FileResponse, HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings

from rental.models import Contratto, Prenotazione, Staff, Utente, Veicolo
from rental.utils import adjusted_price, boat_length, compute_cost, ebike_battery, hash_password, money, scooter_engine, verify_password, vehicle_specs


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


def require_role(request: HttpRequest, role: str | set[str]):
    allowed_roles = {role} if isinstance(role, str) else role
    if request.session.get("role") not in allowed_roles:
        query = urlencode({"next": request.get_full_path()})
        return redirect(f"/login/?{query}")
    return None


def home(request: HttpRequest) -> HttpResponse:
    role = request.session.get("role")
    if role == "admin":
        return redirect("/admin/")
    if role == "cliente":
        return redirect("/veicoli/")
    if role == "staff":
        return redirect("/admin/contratti/")
    return redirect("/login/")


def docs(request: HttpRequest) -> HttpResponse:
    return render(request, "docs.html", {"title": "Modello dati"})


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if request.method == "POST":
        identity = request.POST.get("identificativo", "").strip()
        password = request.POST.get("password", "")
        user = Utente.objects.filter(mail=identity, tipo__in=["admin", "cliente", "staff"]).first()
        if user and user.password_hash and verify_password(password, user.password_hash):
            request.session["role"] = user.tipo
            request.session["id"] = user.id_utente
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                if user.tipo == "cliente" and not next_url.startswith("/admin/"):
                    return redirect(next_url)
                if user.tipo == "admin" and next_url.startswith("/admin/"):
                    return redirect(next_url)
                if user.tipo == "staff" and next_url.startswith("/admin/contratti/"):
                    return redirect(next_url)
            if user.tipo == "admin":
                return redirect("/admin/")
            if user.tipo == "staff":
                return redirect("/admin/contratti/")
            return redirect("/veicoli/")
        return redirect("/login/?errore=1")
    return render(request, "login.html", {"title": "Accesso al sistema", "action": "/login/", "next": next_url})


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
                    nome=request.POST["nome"],
                    cognome=request.POST["cognome"],
                    mail=request.POST["mail"],
                    telefono=request.POST["telefono"],
                    password_hash=hash_password(request.POST["password"]),
                    tipo="cliente",
                )
            request.session["role"] = "cliente"
            request.session["id"] = utente.id_utente
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
                prenotazione = Prenotazione.objects.create(
                    utente_id=request.session["id"],
                    veicolo=veicolo,
                    tipo_ritiro=request.POST["tipo_ritiro"],
                    indirizzo_ritiro=address,
                    data_inizio=request.POST["data_inizio"],
                    data_fine=request.POST["data_fine"],
                    stato="in_attesa",
                    costo_previsto=total,
                    cauzione_richiesta=deposit,
                    note=request.POST.get("note", ""),
                )
                Contratto.objects.create(
                    prenotazione=prenotazione,
                    veicolo=veicolo,
                    data_stipula=None,
                    costo_totale=total,
                    cauzione_importo=deposit,
                    cauzione_stato="richiesto",
                    saldo_importo=max(total - deposit, 0),
                    saldo_stato="richiesto",
                )
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
                   CASE WHEN co.cauzione_stato = 'pagato' THEN co.cauzione_importo ELSE 0 END cauzione_pagata,
                   CASE WHEN co.saldo_stato = 'pagato' THEN co.saldo_importo ELSE 0 END saldo_pagato
            FROM Prenotazione p
            JOIN Veicolo v ON v.idVeicolo = p.idVeicolo
            LEFT JOIN Contratto co ON co.idPrenotazione = p.idPrenotazione
            WHERE p.idUtente = %s
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
            WHERE idPrenotazione = %s
              AND idUtente = %s
              AND stato IN ('in_attesa', 'accettata')
            """,
            [request.POST["idPrenotazione"], request.session["id"]],
        )
        cursor.execute(
            """
            UPDATE Contratto
            SET cauzione_stato = CASE WHEN cauzione_stato = 'pagato' THEN 'rimborsato' ELSE cauzione_stato END,
                saldo_stato = CASE WHEN saldo_stato = 'pagato' THEN 'rimborsato' ELSE saldo_stato END
            WHERE idPrenotazione = %s
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
                (SELECT COUNT(*) FROM Utente WHERE tipo = 'cliente') clienti,
                (SELECT COALESCE(SUM(
                    CASE WHEN cauzione_stato='pagato' THEN cauzione_importo ELSE 0 END +
                    CASE WHEN saldo_stato='pagato' THEN saldo_importo ELSE 0 END
                ), 0) FROM Contratto) incassi
            """
        )
        stats = dictfetchall(cursor)[0]
        cursor.execute(
            """
            SELECT 'cauzione' AS tipo, co.cauzione_importo AS importo, co.cauzione_data_pagamento AS data_pagamento,
                   p.idPrenotazione, p.stato,
                   c.nome, c.cognome,
                   v.marca, v.modello
            FROM Contratto co
            JOIN Prenotazione p ON p.idPrenotazione = co.idPrenotazione
            JOIN Utente c ON c.idUtente = p.idUtente
            JOIN Veicolo v ON v.idVeicolo = p.idVeicolo
            WHERE co.cauzione_stato = 'pagato'
            UNION ALL
            SELECT 'saldo' AS tipo, co.saldo_importo AS importo, co.saldo_data_pagamento AS data_pagamento,
                   p.idPrenotazione, p.stato,
                   c.nome, c.cognome,
                   v.marca, v.modello
            FROM Contratto co
            JOIN Prenotazione p ON p.idPrenotazione = co.idPrenotazione
            JOIN Utente c ON c.idUtente = p.idUtente
            JOIN Veicolo v ON v.idVeicolo = p.idVeicolo
            WHERE co.saldo_stato = 'pagato'
            ORDER BY data_pagamento DESC, 4 DESC, tipo
            """
        )
        credited = dictfetchall(cursor)
        cursor.execute(
            """
            SELECT p.idPrenotazione, p.data_inizio, p.data_fine, p.stato,
                   p.costo_previsto, c.nome, c.cognome, c.mail, c.telefono,
                   v.marca, v.modello, v.tipo, v.targa, v.cilindrata,
                   p.tipo_ritiro, p.indirizzo_ritiro
            FROM Prenotazione p
            JOIN Utente c ON c.idUtente = p.idUtente
            JOIN Veicolo v ON v.idVeicolo = p.idVeicolo
            WHERE p.data_fine = %s
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
        batteria_watt=ebike_battery(request.POST),
        lunghezza=boat_length(request.POST),
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
    current.batteria_watt = ebike_battery(request.POST)
    current.lunghezza = boat_length(request.POST)
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
    rows = Prenotazione.objects.select_related("utente", "veicolo").order_by("-id_prenotazione")
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
            "UPDATE Prenotazione SET stato = %s, cauzione_richiesta = %s WHERE idPrenotazione = %s",
            [request.POST["stato"], deposit, request.POST["idPrenotazione"]],
        )
        cursor.execute(
            """
            UPDATE Contratto
            SET cauzione_importo = %s,
                saldo_importo = %s,
                costo_totale = %s
            WHERE idPrenotazione = %s
            """,
            [deposit, balance, float(reservation.costo_previsto), request.POST["idPrenotazione"]],
        )
        if request.POST["stato"] == "accettata":
            cursor.execute(
                """
                UPDATE Contratto
                SET saldo_stato = 'pagato',
                    saldo_data_pagamento = COALESCE(saldo_data_pagamento, %s)
                WHERE idPrenotazione = %s
                """,
                [payment_date, request.POST["idPrenotazione"]],
            )
    return redirect("/admin/prenotazioni/")


def admin_payments(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    pren_id = request.GET.get("idPrenotazione", "")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT idPrenotazione, 'cauzione' AS tipo, cauzione_importo AS importo,
                   cauzione_stato AS stato, cauzione_data_pagamento AS data_pagamento
            FROM Contratto
            WHERE idPrenotazione = %s
            UNION ALL
            SELECT idPrenotazione, 'saldo' AS tipo, saldo_importo AS importo,
                   saldo_stato AS stato, saldo_data_pagamento AS data_pagamento
            FROM Contratto
            WHERE idPrenotazione = %s
            ORDER BY tipo
            """,
            [pren_id, pren_id],
        )
        rows = dictfetchall(cursor)
    return render(request, "admin_pagamenti.html", {"title": "Pagamenti", "payments": rows, "id": pren_id})


@require_POST
def admin_payment_update(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    data = date.today().isoformat() if request.POST["stato"] == "pagato" else None
    tipo = request.POST["tipo"]
    if tipo not in {"cauzione", "saldo"}:
        return HttpResponseBadRequest("Tipo pagamento non valido.")
    stato_column = f"{tipo}_stato"
    data_column = f"{tipo}_data_pagamento"
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE Contratto SET {stato_column} = %s, {data_column} = %s WHERE idPrenotazione = %s",
            [request.POST["stato"], data, request.POST["idPrenotazione"]],
        )
    return redirect("/admin/prenotazioni/")


def admin_contracts(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, {"admin", "staff"})
    if blocked:
        return blocked
    staff_id = request.GET.get("idStaff", "").strip()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.idPrenotazione, p.idVeicolo, p.data_inizio, p.data_fine, p.costo_previsto,
                   c.nome, c.cognome, v.marca, v.modello
            FROM Prenotazione p
            JOIN Utente c ON c.idUtente = p.idUtente
            JOIN Veicolo v ON v.idVeicolo = p.idVeicolo
            JOIN Contratto co ON co.idPrenotazione = p.idPrenotazione
            WHERE p.stato = 'accettata'
              AND co.data_stipula IS NULL
            ORDER BY p.idPrenotazione DESC
            """
        )
        available_reservations = dictfetchall(cursor)
        cursor.execute(
            """
            SELECT co.idContratto, co.data_stipula, co.costo_totale,
                   p.idPrenotazione, p.data_inizio, p.data_fine,
                   c.nome AS cliente_nome, c.cognome AS cliente_cognome,
                   v.marca, v.modello,
                   s.idStaff, su.nome AS staff_nome, s.ruolo
            FROM Contratto co
            JOIN Staff s ON s.idStaff = co.idStaff
            JOIN Utente su ON su.idUtente = s.idUtente
            JOIN Prenotazione p ON p.idPrenotazione = co.idPrenotazione
            JOIN Utente c ON c.idUtente = p.idUtente
            JOIN Veicolo v ON v.idVeicolo = co.idVeicolo
            WHERE co.data_stipula IS NOT NULL
              AND co.idStaff IS NOT NULL
              AND (%s = '' OR s.idStaff = %s)
            ORDER BY co.data_stipula DESC, co.idContratto DESC
            """,
            [staff_id, staff_id],
        )
        contracts = dictfetchall(cursor)
    return render(
        request,
        "admin_contratti.html",
        {
            "title": "Contratti",
            "staff": Staff.objects.select_related("utente").all().order_by("id_staff"),
            "available_reservations": available_reservations,
            "contracts": contracts,
            "id_staff": staff_id,
            "today": date.today().isoformat(),
        },
    )


@require_POST
def admin_contract_add(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, {"admin", "staff"})
    if blocked:
        return blocked
    reservation = get_object_or_404(Prenotazione, pk=request.POST["idPrenotazione"])
    staff = get_object_or_404(Staff, pk=request.POST["idStaff"])
    if reservation.stato != "accettata":
        return HttpResponseBadRequest("Il contratto puo essere stipulato solo per prenotazioni accettate.")
    try:
        with transaction.atomic():
            contract = get_object_or_404(Contratto, prenotazione=reservation)
            contract.data_stipula = request.POST["data_stipula"]
            contract.costo_totale = float(request.POST["costo_totale"])
            contract.veicolo = reservation.veicolo
            contract.staff = staff
            contract.save(update_fields=["data_stipula", "costo_totale", "veicolo", "staff"])
    except (IntegrityError, ValueError) as exc:
        return HttpResponseBadRequest(str(exc))
    return redirect(f"/admin/contratti/?idStaff={staff.id_staff}")


def admin_customers(request: HttpRequest) -> HttpResponse:
    blocked = require_role(request, "admin")
    if blocked:
        return blocked
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.*, COUNT(p.idPrenotazione) prenotazioni, COALESCE(SUM(p.costo_previsto), 0) totale
            FROM Utente c
            LEFT JOIN Prenotazione p ON p.idUtente = c.idUtente
            WHERE c.tipo = 'cliente'
            GROUP BY c.idUtente
            ORDER BY c.cognome, c.nome
            """
        )
        rows = dictfetchall(cursor)
    return render(request, "admin_clienti.html", {"title": "Clienti", "customers": rows})

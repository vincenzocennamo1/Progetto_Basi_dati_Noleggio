from django.urls import reverse


def navigation(request):
    role = request.session.get("role")
    if role == "admin":
        links = [
            ("Dashboard", reverse("admin_dashboard")),
            ("Veicoli", reverse("admin_vehicles")),
            ("Prenotazioni", reverse("admin_reservations")),
            ("Contratti", reverse("admin_contracts")),
            ("Clienti", reverse("admin_customers")),
            ("Esci", reverse("logout")),
        ]
    elif role == "cliente":
        links = [
            ("Veicoli", reverse("vehicles")),
            ("Le mie prenotazioni", reverse("my_reservations")),
            ("Esci", reverse("logout")),
        ]
    elif role == "staff":
        links = [
            ("Contratti", reverse("admin_contracts")),
            ("Esci", reverse("logout")),
        ]
    else:
        links = [("Veicoli", reverse("vehicles")), ("Login", reverse("login")), ("Registrati", reverse("register"))]
    return {"nav_links": links}

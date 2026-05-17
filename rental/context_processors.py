def navigation(request):
    role = request.session.get("role")
    if role == "admin":
        links = [
            ("Dashboard", "/admin/"),
            ("Veicoli", "/admin/veicoli/"),
            ("Prenotazioni", "/admin/prenotazioni/"),
            ("Contratti", "/admin/contratti/"),
            ("Clienti", "/admin/clienti/"),
            ("Esci", "/logout/"),
        ]
    elif role == "cliente":
        links = [
            ("Veicoli", "/veicoli/"),
            ("Le mie prenotazioni", "/prenotazioni/"),
            ("Esci", "/logout/"),
        ]
    else:
        links = [("Veicoli", "/veicoli/"), ("Login", "/login/"), ("Registrati", "/register/")]
    return {"nav_links": links}

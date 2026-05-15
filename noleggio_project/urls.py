from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from rental import views


urlpatterns = [
    path("", views.home, name="home"),
    path("static/style.css", views.static_style, name="static_style"),
    path("docs", views.docs, name="docs"),
    path("docs/", views.docs, name="docs_slash"),
    path("login", views.login_view, name="login"),
    path("login/", views.login_view, name="login_slash"),
    path("admin/login", views.admin_login_redirect, name="admin_login"),
    path("admin/login/", views.admin_login_redirect, name="admin_login_slash"),
    path("logout", views.logout_view, name="logout"),
    path("logout/", views.logout_view, name="logout_slash"),
    path("register", views.register, name="register"),
    path("register/", views.register, name="register_slash"),
    path("veicoli", views.vehicles, name="vehicles"),
    path("veicoli/", views.vehicles, name="vehicles_slash"),
    path("prenota", views.book, name="book"),
    path("prenota/", views.book, name="book_slash"),
    path("prenotazioni", views.my_reservations, name="my_reservations"),
    path("prenotazioni/", views.my_reservations, name="my_reservations_slash"),
    path("prenotazione/annulla", views.cancel_reservation, name="cancel_reservation"),
    path("prenotazione/annulla/", views.cancel_reservation, name="cancel_reservation_slash"),
    path("admin", views.admin_dashboard, name="admin_dashboard"),
    path("admin/", views.admin_dashboard, name="admin_dashboard_slash"),
    path("admin/veicoli", views.admin_vehicles, name="admin_vehicles"),
    path("admin/veicoli/", views.admin_vehicles, name="admin_vehicles_slash"),
    path("admin/veicolo/add", views.admin_vehicle_add, name="admin_vehicle_add"),
    path("admin/veicolo/add/", views.admin_vehicle_add, name="admin_vehicle_add_slash"),
    path("admin/veicolo/update", views.admin_vehicle_update, name="admin_vehicle_update"),
    path("admin/veicolo/update/", views.admin_vehicle_update, name="admin_vehicle_update_slash"),
    path("admin/veicolo/delete", views.admin_vehicle_delete, name="admin_vehicle_delete"),
    path("admin/veicolo/delete/", views.admin_vehicle_delete, name="admin_vehicle_delete_slash"),
    path("admin/prenotazioni", views.admin_reservations, name="admin_reservations"),
    path("admin/prenotazioni/", views.admin_reservations, name="admin_reservations_slash"),
    path("admin/prenotazione/update", views.admin_reservation_update, name="admin_reservation_update"),
    path("admin/prenotazione/update/", views.admin_reservation_update, name="admin_reservation_update_slash"),
    path("admin/pagamenti", views.admin_payments, name="admin_payments"),
    path("admin/pagamenti/", views.admin_payments, name="admin_payments_slash"),
    path("admin/pagamento/update", views.admin_payment_update, name="admin_payment_update"),
    path("admin/pagamento/update/", views.admin_payment_update, name="admin_payment_update_slash"),
    path("admin/clienti", views.admin_customers, name="admin_customers"),
    path("admin/clienti/", views.admin_customers, name="admin_customers_slash"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")

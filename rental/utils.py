from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import date
from typing import Any


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return "pbkdf2_sha256$120000$%s$%s" % (
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    iterations = int(parts[1])
    salt = base64.b64decode(parts[2])
    expected = base64.b64decode(parts[3])
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(digest, expected)


def money(value: float | int | None) -> str:
    return f"{float(value or 0):.2f} euro"


def compute_cost(start: str, end: str, daily_price: float) -> tuple[int, float]:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    days = (end_date - start_date).days
    if days <= 0:
        raise ValueError("La data fine deve essere successiva alla data inizio")
    return days, round(days * float(daily_price), 2)


def attr(row: Any, name: str) -> Any:
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name)


def vehicle_specs(row: Any, show_plate: bool = True) -> str:
    tipo = attr(row, "tipo")
    targa = ""
    if show_plate:
        plate = attr(row, "targa")
        targa = f", targa {plate}" if plate else ", targa non inserita"
    if tipo != "auto":
        cilindrata = attr(row, "cilindrata")
        if tipo == "scooter" and cilindrata:
            return f"scooter {cilindrata} cc{targa}"
        batteria_watt = attr(row, "batteria_watt")
        if tipo == "bici elettrica" and batteria_watt:
            return f"bici elettrica {batteria_watt}W{targa}"
        lunghezza = attr(row, "lunghezza")
        if tipo == "barca" and lunghezza:
            return f"barca {float(lunghezza):g} m{targa}"
        return f"{tipo}{targa}"
    cambio = attr(row, "cambio") or "manuale"
    cabrio = "cabrio" if attr(row, "cabrio") else "non cabrio"
    return f"auto {cambio}, {cabrio}{targa}"


def adjusted_price(form: dict, current=None) -> float:
    price = float(form["prezzo_giornaliero"])
    if current and current.tipo == "auto":
        if current.cambio == "automatica":
            price -= 10
        if current.cabrio:
            price -= 20
    if form.get("tipo") == "auto":
        if form.get("cambio") == "automatica":
            price += 10
        if form.get("cabrio") == "1":
            price += 20
    return round(price, 2)


def scooter_engine(form: dict) -> int | None:
    if form.get("tipo") != "scooter":
        return None
    return int(form.get("cilindrata") or "125")


def ebike_battery(form: dict) -> int | None:
    if form.get("tipo") != "bici elettrica":
        return None
    return int(form.get("batteria_watt") or "250")


def boat_length(form: dict) -> float | None:
    if form.get("tipo") != "barca" or not form.get("lunghezza"):
        return None
    return float(form["lunghezza"])

"""
Invio email alla reception (adapter intercambiabile).

- `StubEmailSender`: NON invia nulla, registra i messaggi in memoria. Per dev/test.
- `SmtpEmailSender`: invio reale via SMTP (in produzione: servizio email EU).

`format_booking_email` costruisce oggetto+corpo a partire dalla richiesta.
"""
from __future__ import annotations

from typing import List, Protocol, Tuple

from .booking import BookingInput
from .calc import nights_between


class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class StubEmailSender:
    """Non invia: accumula le email in `sent` (per test/dev)."""

    def __init__(self) -> None:
        self.sent: List[dict] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})


class SmtpEmailSender:
    def __init__(self, host: str, port: int, user: str, password: str, sender: str) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender

    def send(self, to: str, subject: str, body: str) -> None:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            if self.user:
                server.login(self.user, self.password)
            server.send_message(msg)


def format_booking_email(hotel_name: str, b: BookingInput, booking_id: int) -> Tuple[str, str]:
    nights = nights_between(b.check_in, b.check_out)
    subject = f"[{hotel_name}] Nuova richiesta di prenotazione #{booking_id}"
    body = (
        f"Nuova richiesta di prenotazione (#{booking_id}) — stato: in attesa.\n\n"
        f"Ospite: {b.guest_name}\n"
        f"Email: {b.guest_email}\n"
        f"Telefono: {b.guest_phone or '-'}\n"
        f"Tipo stanza: {b.room_type or '-'}\n"
        f"Check-in: {b.check_in}\n"
        f"Check-out: {b.check_out}\n"
        f"Notti: {nights}\n"
        f"Ospiti: {b.num_guests}\n"
        f"Note: {b.notes or '-'}\n\n"
        f"Rispondere direttamente all'ospite per confermare o proporre alternative."
    )
    return subject, body

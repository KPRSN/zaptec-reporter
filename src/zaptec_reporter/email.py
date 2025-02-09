import jinja2 as jinja
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from enum import StrEnum


class EmailEncryption(StrEnum):
    DISABLED = "disabled"
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"


class Email:
    def __init__(
        self,
        server_address,
        server_port,
        encryption,
        username,
        password,
        subject,
        from_email,
        text=None,
        html=None,
        filename=None,
        to=list(),
        cc=list(),
        bcc=list(),
    ):
        self.server_address = server_address
        self.server_port = server_port
        self.encryption = encryption
        self.username = username
        self.password = password
        self.from_email = from_email
        self.subject = subject
        self.text = text
        self.html = html
        self.filename = filename
        self.to = to
        self.cc = cc
        self.bcc = bcc

    def send(self, values, buffer):
        msg = EmailMessage()
        msg["Subject"] = jinja.Template(self.subject).render(values)
        msg["From"] = formataddr(self.from_email)

        # Add recipients.
        if len(self.to) > 0:
            msg["To"] = ", ".join(self.to)

        if len(self.cc) > 0:
            msg["Cc"] = ", ".join(self.cc)

        if len(self.bcc) > 0:
            msg["Bcc"] = ", ".join(self.bcc)

        # Add body.
        if self.text is not None:
            msg.set_content(jinja.Template(self.text).render(values))

        if self.html is not None:
            msg.add_alternative(jinja.Template(self.html).render(values), subtype="html")

        # Add charge report attachment.
        if self.filename is not None:
            msg.add_attachment(
                buffer.getbuffer().tobytes(),
                maintype="application",
                subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=jinja.Template(self.filename).render(values),
            )

        # Send using the perfect level of encryption.
        logging.info(f"Sending email to {len(self.to) + len(self.cc) + len(self.bcc)} recipients.")
        if self.encryption == EmailEncryption.IMPLICIT:
            with smtplib.SMTP_SSL(host=self.server_address, port=self.server_port) as server:
                server.login(self.username, self.password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host=self.server_address, port=self.server_port) as server:
                if self.encryption == EmailEncryption.EXPLICIT:
                    server.starttls()

                server.login(self.username, self.password)
                server.send_message(msg)

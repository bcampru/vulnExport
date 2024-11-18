import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


class EmailSender:
    def __init__(self, smtp_user, smtp_password):
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587

    def _create_message(self, from_email, to_emails, subject, body, body_type='plain'):
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = ", ".join(to_emails)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, body_type))
        return msg

    def send_file_email(self, from_email, to_emails, subject, body, file, file_name):
        msg = self._create_message(
            from_email, to_emails, subject, body, 'html')

        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(file)
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              f'attachment; filename={file_name}')
        msg.attach(attachment)

        self._send_email(from_email, to_emails, msg)

    def send_html_email(self, from_email, to_emails, subject, html_body):
        msg = self._create_message(
            from_email, to_emails, subject, html_body, 'html')
        self._send_email(from_email, to_emails, msg)

    def _send_email(self, from_email, to_emails, msg):
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(from_email, to_emails, msg.as_string())
            print("Email sent successfully")
        except Exception as e:
            print(f"Failed to send email: {e}")

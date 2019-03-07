#!/usr/bin/python3

import argparse
import email
import io
import smtplib
import socket
import sys
import xml.etree.ElementTree as ET
import zipfile

from collections import defaultdict
from email.mime.multipart import MIMEMultipart, MIMEBase
from email.mime.text import MIMEText


def eprint(*args, **kwargs):
    """ Utility function to print to stderr
    """
    print(*args, **kwargs, file=sys.stderr)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward-passing", help="Also forward reports that only contain passing mails.",
                        action="store_true")
    parser.add_argument("--destination", "-d", help="Email to forward reports to. Defaults to postmaster.",
                        default="postmaster")
    parser.add_argument("email", nargs="?", help="Email file to read. Defaults to stdin.", type=argparse.FileType("r"),
                        default=sys.stdin)

    return parser.parse_args()


def get_report(msg):
    payload = get_zippart(msg)
    if payload is None:
        eprint("Message does not contain a zip file")
        return None

    # Triple nested "with". This could be better.
    with io.BytesIO(payload.get_payload(decode=True)) as zipdata:
        with zipfile.ZipFile(zipdata) as archive:
            xmlname = archive.namelist()[0]
            with archive.open(xmlname) as reportfile:
                return ET.parse(reportfile)


def get_zippart(msg):
    if msg.get_content_type() == 'application/zip':
        return msg

    elif msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'application/zip':
                return part

    return None


def parse_results(report):
    passes = defaultdict(int)
    failures = defaultdict(int)

    for row in report.iter("row"):
        dkim = False
        spf = False
        count = 0
        source = None

        for elem in row:
            if elem.tag == "count":
                count = int(elem.text)
            elif elem.tag == "source_ip":
                source = elem.text
            elif elem.tag == "policy_evaluated":
                for policy in elem.iter():
                    if policy.tag == "dkim":
                        dkim = policy.text == "pass"
                    elif policy.tag == "spf":
                        spf = policy.text == "pass"

        if dkim or spf:
            passes[source] += count
        else:
            failures[source] += count

    return passes, failures


def patch_email(addr):
    if addr.find('@') == -1:
        return addr + '@' + socket.gethostname()

    return addr


def send_report(from_addr, to_addr, msg, passes, failures):
    to_send = MIMEMultipart()
    to_send['From'] = "DMARC forwarder bot <%s>" % patch_email(from_addr)
    to_send['To'] = patch_email(to_addr)
    to_send['Subject'] = msg['Subject']

    bodytext = "Received %u correct emails.\n" % sum(passes.values())
    for host in failures:
        hostname, _, _ = socket.gethostbyaddr(host)
        bodytext += "Received %u failures from %s (%s)" % (failures[host], host, hostname)
        if host in passes:
            bodytext += " (also received %u correct ones)" % passes[host]

        bodytext += "\n"

    to_send.attach(MIMEText(bodytext, "plain"))

    zippart = get_zippart(msg)
    attachment = MIMEBase('application', 'zip')
    attachment.set_payload(zippart.get_payload(decode=True))
    email.encoders.encode_base64(attachment)
    attachment.add_header('Content-disposition', 'attachment', filename=zippart.get_filename())
    to_send.attach(attachment)

    with smtplib.SMTP('localhost') as s:
        s.send_message(to_send)


def main():
    args = get_args()
    msg = email.message_from_file(args.email)

    report = get_report(msg)
    if report is None:
        exit(1)

    passed, failed = parse_results(report)

    if failed or args.forward_passing:
        send_report('dmarc-forwarder', args.destination, msg, passed, failed)
    else:
        eprint("Not forwarding report with only passes.")


if __name__ == '__main__':
    main()

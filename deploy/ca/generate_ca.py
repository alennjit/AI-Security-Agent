"""Generate a per-client, NAME-CONSTRAINED inspection CA for the AI Security Agent proxy.

Why name-constrained: a normal inspection CA can mint a valid certificate for ANY website, so
a stolen key would be catastrophic. This CA carries a critical X.509 Name Constraints extension
that permits only the AI-service hostnames in the proxy's registry. Clients that honor the
extension (Windows CryptoAPI, Chrome, Edge, Firefox, OpenSSL) reject anything this CA signs for
another site. It is also short-lived (default 2 years) and path-length 0 (cannot create sub-CAs).

Output (in --out, which must not already contain a CA):
  mitmproxy-ca.pem        PRIVATE KEY + certificate — mitmproxy reads this from its confdir.
                          Keep it on the proxy host only. Never distribute or commit it.
  mitmproxy-ca-cert.pem   certificate only (PEM)
  ca-cert.cer             certificate only (DER) — this is what gets deployed to clients

Usage (from the repo root):
  python deploy/ca/generate_ca.py --client-name "Acme Corp" --out /srv/aisa/acme-ca
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import logging
import os
import subprocess
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "proxy"))

from ai_security_agent.domains import KNOWN_ENDPOINTS  # noqa: E402

logger = logging.getLogger("aisa.ca")

KEY_FILE = "mitmproxy-ca.pem"
CERT_PEM_FILE = "mitmproxy-ca-cert.pem"
CERT_DER_FILE = "ca-cert.cer"


def permitted_hosts() -> list[str]:
    """Hostnames the CA may sign for (each also permits its subdomains, per RFC 5280)."""
    return sorted({endpoint.host for endpoint in KNOWN_ENDPOINTS})


def build_ca(client_name: str, days: int) -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    """Create the key pair and the self-signed, name-constrained CA certificate."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, client_name),
        x509.NameAttribute(NameOID.COMMON_NAME, f"AI Security Agent Inspection CA ({client_name})"),
    ])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                content_commitment=False, key_encipherment=False, data_encipherment=False,
                key_agreement=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.NameConstraints(
                permitted_subtrees=[x509.DNSName(host) for host in permitted_hosts()],
                excluded_subtrees=None,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    return key, cert


def restrict_permissions(path: Path) -> None:
    """Best effort: make the private key readable by the current user only."""
    if os.name == "nt":
        user = os.environ.get("USERNAME", "")
        if user:
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
                check=False, capture_output=True, shell=False,
            )
    else:
        path.chmod(0o600)


def write_ca(out: Path, key: rsa.RSAPrivateKey, cert: x509.Certificate) -> None:
    key_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    out.mkdir(parents=True, exist_ok=True)
    (out / KEY_FILE).write_bytes(key_pem + cert_pem)
    restrict_permissions(out / KEY_FILE)
    (out / CERT_PEM_FILE).write_bytes(cert_pem)
    (out / CERT_DER_FILE).write_bytes(cert.public_bytes(serialization.Encoding.DER))


def thumbprints(cert: x509.Certificate) -> dict[str, str]:
    der = cert.public_bytes(serialization.Encoding.DER)
    return {
        "sha1 (Windows thumbprint)": hashlib.sha1(der).hexdigest().upper(),  # noqa: S324 - identifier only
        "sha256": hashlib.sha256(der).hexdigest().upper(),
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--client-name", required=True, help="Organisation this CA is for (one CA per client)")
    parser.add_argument("--out", required=True, type=Path, help="Directory for the generated files")
    parser.add_argument("--days", type=int, default=730, help="Validity in days (default 730)")
    args = parser.parse_args()

    if (args.out / KEY_FILE).exists():
        logger.error("Refusing to overwrite an existing CA at %s", args.out)
        return 1

    key, cert = build_ca(args.client_name, args.days)
    write_ca(args.out, key, cert)

    logger.info("CA written to %s", args.out)
    logger.info("Permitted names (%d): %s", len(permitted_hosts()), ", ".join(permitted_hosts()))
    for label, value in thumbprints(cert).items():
        logger.info("%s: %s", label, value)
    logger.info("Deploy ONLY %s to clients. Keep %s on the proxy host.", CERT_DER_FILE, KEY_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

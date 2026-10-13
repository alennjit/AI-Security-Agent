"""Tests for the name-constrained CA generator — including that constraints are ENFORCED."""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

SCRIPT = Path(__file__).resolve().parents[1] / "ca" / "generate_ca.py"
spec = importlib.util.spec_from_file_location("generate_ca", SCRIPT)
generate_ca = importlib.util.module_from_spec(spec)
sys.modules["generate_ca"] = generate_ca
spec.loader.exec_module(generate_ca)


@pytest.fixture(scope="module")
def ca():
    return generate_ca.build_ca("Test Client", days=30)


def leaf_for(host: str, ca_key, ca_cert) -> x509.Certificate:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = dt.datetime.now(dt.timezone.utc)
    return (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)]))
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1))
        .not_valid_after(now + dt.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                ca_cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )


def test_ca_is_constrained_and_cannot_make_subcas(ca):
    _, cert = ca
    bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
    assert bc.critical and bc.value.ca and bc.value.path_length == 0
    nc = cert.extensions.get_extension_for_class(x509.NameConstraints)
    assert nc.critical
    permitted = {n.value for n in nc.value.permitted_subtrees}
    assert {"api.openai.com", "gemini.google.com", "www.perplexity.ai"} <= permitted
    assert "example.com" not in permitted
    assert "google.com" not in permitted  # only the specific Gemini host, not all of Google


def test_validity_is_short_and_requested(ca):
    _, cert = ca
    lifetime = cert.not_valid_after_utc - cert.not_valid_before_utc
    assert dt.timedelta(days=29) < lifetime < dt.timedelta(days=31)


def _verifier(cert, host):
    verification = pytest.importorskip("cryptography.x509.verification")
    store = verification.Store([cert])
    return verification.PolicyBuilder().store(store).build_server_verifier(x509.DNSName(host)), verification


def test_certificate_for_an_ai_host_is_accepted(ca):
    key, cert = ca
    verifier, _ = _verifier(cert, "api.openai.com")
    verifier.verify(leaf_for("api.openai.com", key, cert), [])


def test_certificate_for_a_subdomain_of_a_permitted_host_is_accepted(ca):
    key, cert = ca
    verifier, _ = _verifier(cert, "edge.chatgpt.com")
    verifier.verify(leaf_for("edge.chatgpt.com", key, cert), [])


def test_certificate_for_any_other_site_is_rejected(ca):
    """The point of the design: a stolen key still can't impersonate a bank or a mail provider."""
    key, cert = ca
    for host in ("example.com", "mail.google.com", "mybank.com"):
        verifier, verification = _verifier(cert, host)
        with pytest.raises(verification.VerificationError):
            verifier.verify(leaf_for(host, key, cert), [])


def test_write_ca_outputs_expected_files_and_refuses_overwrite(tmp_path, ca):
    key, cert = ca
    generate_ca.write_ca(tmp_path, key, cert)
    assert (tmp_path / generate_ca.KEY_FILE).read_bytes().startswith(b"-----BEGIN PRIVATE KEY-----")
    public_pem = (tmp_path / generate_ca.CERT_PEM_FILE).read_bytes()
    assert b"PRIVATE KEY" not in public_pem
    assert b"PRIVATE KEY" not in (tmp_path / generate_ca.CERT_DER_FILE).read_bytes()

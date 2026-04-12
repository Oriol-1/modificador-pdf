"""Tests para core.digital_signature — Firma digital de PDFs."""

import os
import pytest
from unittest.mock import patch, MagicMock

from core.digital_signature import (
    SignatureStatus,
    SignatureLevel,
    CertificateInfo,
    SignatureInfo,
    SigningConfig,
    SignResult,
    VerifyResult,
    is_available,
    get_signature_count,
    sign_pdf,
    verify_signatures,
    load_certificate_info,
    HAS_PYHANKO,
    HAS_FITZ,
)


# ━━━ Enums ━━━


class TestEnums:
    """Tests para enums."""

    def test_signature_status_values(self):
        assert SignatureStatus.VALID.value == "valid"
        assert SignatureStatus.INVALID.value == "invalid"
        assert SignatureStatus.UNKNOWN.value == "unknown"
        assert SignatureStatus.UNSIGNED.value == "unsigned"
        assert SignatureStatus.ERROR.value == "error"

    def test_signature_level_values(self):
        assert SignatureLevel.BASIC.value == "B-B"
        assert SignatureLevel.TIMESTAMP.value == "B-T"
        assert SignatureLevel.LONG_TERM.value == "B-LT"


# ━━━ CertificateInfo ━━━


class TestCertificateInfo:
    """Tests para CertificateInfo."""

    def test_defaults(self):
        info = CertificateInfo()
        assert info.subject == ""
        assert info.issuer == ""
        assert info.is_expired is False

    def test_to_dict(self):
        info = CertificateInfo(
            subject="CN=Test",
            issuer="CN=CA",
            serial_number="123",
            not_before="2024-01-01",
            not_after="2025-01-01",
            is_expired=False,
        )
        d = info.to_dict()
        assert d["subject"] == "CN=Test"
        assert d["issuer"] == "CN=CA"
        assert d["serial_number"] == "123"

    def test_from_dict(self):
        data = {
            "subject": "CN=Test",
            "issuer": "CN=CA",
            "serial_number": "456",
            "not_before": "2024-01-01",
            "not_after": "2025-01-01",
            "is_expired": True,
        }
        info = CertificateInfo.from_dict(data)
        assert info.subject == "CN=Test"
        assert info.is_expired is True

    def test_roundtrip(self):
        original = CertificateInfo(
            subject="CN=Alice",
            issuer="CN=Root CA",
            serial_number="789",
            not_before="2024-06-01",
            not_after="2026-06-01",
            is_expired=False,
        )
        restored = CertificateInfo.from_dict(original.to_dict())
        assert restored.subject == original.subject
        assert restored.serial_number == original.serial_number


# ━━━ SignatureInfo ━━━


class TestSignatureInfo:
    """Tests para SignatureInfo."""

    def test_defaults(self):
        info = SignatureInfo()
        assert info.signer_name == ""
        assert info.status == SignatureStatus.UNKNOWN
        assert info.certificate is None

    def test_to_dict_without_cert(self):
        info = SignatureInfo(signer_name="Alice", status=SignatureStatus.VALID)
        d = info.to_dict()
        assert d["signer_name"] == "Alice"
        assert d["status"] == "valid"
        assert d["certificate"] is None

    def test_to_dict_with_cert(self):
        cert = CertificateInfo(subject="CN=Alice")
        info = SignatureInfo(
            signer_name="Alice",
            status=SignatureStatus.VALID,
            certificate=cert,
        )
        d = info.to_dict()
        assert d["certificate"]["subject"] == "CN=Alice"

    def test_from_dict(self):
        data = {
            "signer_name": "Bob",
            "signing_time": "2024-01-01T12:00:00",
            "status": "invalid",
            "certificate": {"subject": "CN=Bob"},
            "reason": "Aprobación",
            "location": "Madrid",
            "field_name": "Sig1",
        }
        info = SignatureInfo.from_dict(data)
        assert info.signer_name == "Bob"
        assert info.status == SignatureStatus.INVALID
        assert info.certificate.subject == "CN=Bob"
        assert info.reason == "Aprobación"

    def test_from_dict_no_cert(self):
        data = {"signer_name": "Carol", "status": "unknown"}
        info = SignatureInfo.from_dict(data)
        assert info.certificate is None


# ━━━ SigningConfig ━━━


class TestSigningConfig:
    """Tests para SigningConfig."""

    def test_defaults(self):
        cfg = SigningConfig()
        assert cfg.pfx_path == ""
        assert cfg.pfx_password == ""
        assert cfg.field_name == "Signature1"
        assert cfg.visible is False
        assert cfg.page == 0

    def test_custom(self):
        cfg = SigningConfig(
            pfx_path="/tmp/cert.pfx",
            pfx_password="secret",
            reason="Aprobación",
            visible=True,
            page=2,
        )
        assert cfg.pfx_path == "/tmp/cert.pfx"
        assert cfg.visible is True
        assert cfg.page == 2


# ━━━ SignResult ━━━


class TestSignResult:
    """Tests para SignResult."""

    def test_defaults(self):
        r = SignResult(success=True)
        assert r.output_path == ""
        assert r.message == ""
        assert r.signer_name == ""

    def test_full(self):
        r = SignResult(
            success=False,
            message="Error",
            output_path="/tmp/out.pdf",
            signer_name="Alice",
        )
        assert r.success is False
        assert r.signer_name == "Alice"


# ━━━ VerifyResult ━━━


class TestVerifyResult:
    """Tests para VerifyResult."""

    def test_defaults(self):
        r = VerifyResult()
        assert r.has_signatures is False
        assert r.signatures == []
        assert r.all_valid is False

    def test_with_signatures(self):
        sigs = [
            SignatureInfo(signer_name="Alice", status=SignatureStatus.VALID),
            SignatureInfo(signer_name="Bob", status=SignatureStatus.INVALID),
        ]
        r = VerifyResult(
            has_signatures=True,
            signatures=sigs,
            all_valid=False,
            message="1 de 2 válidas",
        )
        assert len(r.signatures) == 2
        assert r.all_valid is False


# ━━━ is_available ━━━


class TestIsAvailable:
    """Tests para is_available."""

    def test_returns_bool(self):
        result = is_available()
        assert isinstance(result, bool)


# ━━━ sign_pdf sin pyhanko ━━━


class TestSignPdfNoPyhanko:
    """Tests para sign_pdf cuando pyhanko no está instalado."""

    @patch("core.digital_signature.HAS_PYHANKO", False)
    def test_returns_error(self, tmp_path):
        result = sign_pdf(
            str(tmp_path / "in.pdf"),
            str(tmp_path / "out.pdf"),
            SigningConfig(),
        )
        assert result.success is False
        assert "pyhanko" in result.message.lower()

    def test_missing_input(self, tmp_path):
        if not HAS_PYHANKO:
            pytest.skip("pyhanko no instalado")
        result = sign_pdf(
            str(tmp_path / "nonexistent.pdf"),
            str(tmp_path / "out.pdf"),
            SigningConfig(pfx_path="/tmp/cert.pfx"),
        )
        assert result.success is False

    def test_missing_cert(self, tmp_path):
        if not HAS_PYHANKO:
            pytest.skip("pyhanko no instalado")

        import fitz
        pdf = str(tmp_path / "test.pdf")
        doc = fitz.open()
        doc.new_page()
        doc.save(pdf)
        doc.close()

        result = sign_pdf(
            pdf,
            str(tmp_path / "out.pdf"),
            SigningConfig(pfx_path=str(tmp_path / "nocert.pfx")),
        )
        assert result.success is False
        assert "no encontrado" in result.message.lower()


# ━━━ load_certificate_info ━━━


class TestLoadCertificateInfo:
    """Tests para load_certificate_info."""

    @patch("core.digital_signature.HAS_PYHANKO", False)
    def test_no_pyhanko(self):
        result = load_certificate_info("/tmp/cert.pfx", "pass")
        assert result is None

    def test_nonexistent_file(self):
        if not HAS_PYHANKO:
            pytest.skip("pyhanko no instalado")
        result = load_certificate_info("/nonexistent.pfx", "pass")
        assert result is None


# ━━━ get_signature_count ━━━


class TestGetSignatureCount:
    """Tests para get_signature_count."""

    def test_unsigned_pdf(self, tmp_path):
        if not HAS_FITZ:
            pytest.skip("fitz no disponible")

        import fitz
        pdf = str(tmp_path / "unsigned.pdf")
        doc = fitz.open()
        doc.new_page()
        doc.save(pdf)
        doc.close()

        count = get_signature_count(pdf)
        assert count == 0

    def test_nonexistent(self, tmp_path):
        count = get_signature_count(str(tmp_path / "nope.pdf"))
        assert count == 0

    @patch("core.digital_signature.HAS_FITZ", False)
    def test_no_fitz(self):
        count = get_signature_count("/tmp/test.pdf")
        assert count == 0


# ━━━ verify_signatures ━━━


class TestVerifySignatures:
    """Tests para verify_signatures."""

    def test_unsigned_pdf(self, tmp_path):
        import fitz
        pdf = str(tmp_path / "unsigned.pdf")
        doc = fitz.open()
        doc.new_page()
        doc.save(pdf)
        doc.close()

        result = verify_signatures(pdf)
        assert result.has_signatures is False

    @patch("core.digital_signature.HAS_PYHANKO", False)
    def test_fallback_no_pyhanko(self, tmp_path):
        import fitz
        pdf = str(tmp_path / "unsigned.pdf")
        doc = fitz.open()
        doc.new_page()
        doc.save(pdf)
        doc.close()

        result = verify_signatures(pdf)
        assert result.has_signatures is False
        assert "no se encontraron" in result.message.lower()

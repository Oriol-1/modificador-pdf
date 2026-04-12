"""Motor de firmas digitales para documentos PDF.

Provee funciones para firmar PDFs con certificados X.509
y verificar firmas existentes, usando pyhanko para firmas
PAdES compatibles.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from pyhanko.sign import signers, fields as sig_fields
    from pyhanko.sign.general import load_cert_list_from_pemder
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko import stamp
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography import x509 as crypto_x509
    HAS_PYHANKO = True
except ImportError:
    HAS_PYHANKO = False

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


class SignatureStatus(Enum):
    """Estado de una firma digital."""
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"
    UNSIGNED = "unsigned"
    ERROR = "error"


class SignatureLevel(Enum):
    """Nivel de firma PAdES."""
    BASIC = "B-B"
    TIMESTAMP = "B-T"
    LONG_TERM = "B-LT"


@dataclass
class CertificateInfo:
    """Información de un certificado X.509.

    Attributes:
        subject: Nombre del titular.
        issuer: Emisor del certificado.
        serial_number: Número de serie.
        not_before: Fecha de inicio de validez.
        not_after: Fecha de expiración.
        is_expired: Si el certificado ha expirado.
    """
    subject: str = ""
    issuer: str = ""
    serial_number: str = ""
    not_before: str = ""
    not_after: str = ""
    is_expired: bool = False

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "subject": self.subject,
            "issuer": self.issuer,
            "serial_number": self.serial_number,
            "not_before": self.not_before,
            "not_after": self.not_after,
            "is_expired": self.is_expired,
        }

    @staticmethod
    def from_dict(data: dict) -> 'CertificateInfo':
        """Deserializa desde diccionario."""
        return CertificateInfo(
            subject=data.get("subject", ""),
            issuer=data.get("issuer", ""),
            serial_number=data.get("serial_number", ""),
            not_before=data.get("not_before", ""),
            not_after=data.get("not_after", ""),
            is_expired=data.get("is_expired", False),
        )


@dataclass
class SignatureInfo:
    """Información de una firma en un PDF.

    Attributes:
        signer_name: Nombre del firmante.
        signing_time: Fecha y hora de la firma.
        status: Estado de validación.
        certificate: Info del certificado.
        reason: Motivo de la firma.
        location: Ubicación del firmante.
        field_name: Nombre del campo de firma.
    """
    signer_name: str = ""
    signing_time: str = ""
    status: SignatureStatus = SignatureStatus.UNKNOWN
    certificate: Optional[CertificateInfo] = None
    reason: str = ""
    location: str = ""
    field_name: str = ""

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "signer_name": self.signer_name,
            "signing_time": self.signing_time,
            "status": self.status.value,
            "certificate": self.certificate.to_dict() if self.certificate else None,
            "reason": self.reason,
            "location": self.location,
            "field_name": self.field_name,
        }

    @staticmethod
    def from_dict(data: dict) -> 'SignatureInfo':
        """Deserializa desde diccionario."""
        cert = None
        if data.get("certificate"):
            cert = CertificateInfo.from_dict(data["certificate"])
        return SignatureInfo(
            signer_name=data.get("signer_name", ""),
            signing_time=data.get("signing_time", ""),
            status=SignatureStatus(data.get("status", "unknown")),
            certificate=cert,
            reason=data.get("reason", ""),
            location=data.get("location", ""),
            field_name=data.get("field_name", ""),
        )


@dataclass
class SigningConfig:
    """Configuración para firmar un PDF.

    Attributes:
        pfx_path: Ruta al archivo PFX/P12 del certificado.
        pfx_password: Contraseña del PFX.
        reason: Motivo de la firma.
        location: Ubicación del firmante.
        contact_info: Información de contacto.
        field_name: Nombre del campo de firma.
        visible: Si la firma debe ser visible.
        page: Página donde mostrar la firma visible (0-based).
        position: Posición (x, y, width, height) de la firma visible.
    """
    pfx_path: str = ""
    pfx_password: str = ""
    reason: str = ""
    location: str = ""
    contact_info: str = ""
    field_name: str = "Signature1"
    visible: bool = False
    page: int = 0
    position: Tuple[float, float, float, float] = (72, 72, 200, 60)


@dataclass
class SignResult:
    """Resultado de una operación de firma.

    Attributes:
        success: Si la operación fue exitosa.
        output_path: Ruta del PDF firmado.
        message: Mensaje descriptivo.
        signer_name: Nombre del firmante.
    """
    success: bool
    output_path: str = ""
    message: str = ""
    signer_name: str = ""


@dataclass
class VerifyResult:
    """Resultado de verificación de firmas.

    Attributes:
        has_signatures: Si el PDF tiene firmas.
        signatures: Lista de firmas encontradas.
        all_valid: Si todas las firmas son válidas.
        message: Mensaje descriptivo.
    """
    has_signatures: bool = False
    signatures: List[SignatureInfo] = field(default_factory=list)
    all_valid: bool = False
    message: str = ""


def is_available() -> bool:
    """Verifica si pyhanko está disponible."""
    return HAS_PYHANKO


def load_certificate_info(pfx_path: str, password: str) -> Optional[CertificateInfo]:
    """Carga información de un certificado PFX/P12.

    Args:
        pfx_path: Ruta al archivo PFX.
        password: Contraseña del PFX.

    Returns:
        CertificateInfo o None si falla.
    """
    if not HAS_PYHANKO:
        logger.warning("pyhanko no disponible para cargar certificado")
        return None

    try:
        with open(pfx_path, 'rb') as f:
            pfx_data = f.read()

        private_key, cert, chain = pkcs12.load_key_and_certificates(
            pfx_data, password.encode('utf-8') if password else None
        )

        if cert is None:
            return None

        from datetime import datetime, timezone

        subject = cert.subject.rfc4514_string()
        issuer = cert.issuer.rfc4514_string()
        not_before = cert.not_valid_before_utc.isoformat()
        not_after = cert.not_valid_after_utc.isoformat()
        is_expired = datetime.now(timezone.utc) > cert.not_valid_after_utc

        return CertificateInfo(
            subject=subject,
            issuer=issuer,
            serial_number=str(cert.serial_number),
            not_before=not_before,
            not_after=not_after,
            is_expired=is_expired,
        )

    except Exception as e:
        logger.error(f"Error al cargar certificado: {e}")
        return None


def sign_pdf(
    input_path: str,
    output_path: str,
    config: SigningConfig,
) -> SignResult:
    """Firma un PDF con un certificado X.509.

    Args:
        input_path: Ruta del PDF a firmar.
        output_path: Ruta del PDF firmado.
        config: Configuración de firma.

    Returns:
        SignResult con el resultado.
    """
    if not HAS_PYHANKO:
        return SignResult(
            success=False,
            message="pyhanko no instalado. Instale: pip install pyhanko[pkcs11]",
        )

    if not os.path.isfile(input_path):
        return SignResult(
            success=False,
            message=f"PDF no encontrado: {input_path}",
        )

    if not os.path.isfile(config.pfx_path):
        return SignResult(
            success=False,
            message=f"Certificado no encontrado: {config.pfx_path}",
        )

    try:
        signer = signers.SimpleSigner.load_pkcs12(
            pfx_file=config.pfx_path,
            passphrase=config.pfx_password.encode('utf-8') if config.pfx_password else None,
        )

        with open(input_path, 'rb') as inf:
            writer = IncrementalPdfFileWriter(inf)

            sig_field_spec = None
            if config.visible:
                x, y, w, h = config.position
                sig_field_spec = sig_fields.SigFieldSpec(
                    sig_field_name=config.field_name,
                    on_page=config.page,
                    box=(x, y, x + w, y + h),
                )

            signature_meta = signers.PdfSignatureMetadata(
                field_name=config.field_name,
                reason=config.reason or None,
                location=config.location or None,
                contact_info=config.contact_info or None,
            )

            if sig_field_spec:
                sig_fields.append_signature_field(writer, sig_field_spec)

            with open(output_path, 'wb') as outf:
                signers.sign_pdf(
                    writer,
                    signature_meta=signature_meta,
                    signer=signer,
                    output=outf,
                )

        signer_name = ""
        if signer.signing_cert:
            signer_name = signer.signing_cert.subject.rfc4514_string()

        logger.info(f"PDF firmado: {input_path} → {output_path}")

        return SignResult(
            success=True,
            output_path=output_path,
            message="Firma aplicada correctamente",
            signer_name=signer_name,
        )

    except Exception as e:
        logger.error(f"Error al firmar PDF: {e}")
        return SignResult(
            success=False,
            message=f"Error al firmar: {e}",
        )


def get_signature_count(file_path: str) -> int:
    """Obtiene el número de firmas en un PDF usando fitz.

    Args:
        file_path: Ruta del PDF.

    Returns:
        Número de firmas encontradas.
    """
    if not HAS_FITZ:
        return 0

    try:
        doc = fitz.open(file_path)
        count = 0
        for page in doc:
            widgets = page.widgets()
            if widgets:
                for w in widgets:
                    if w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        count += 1
        doc.close()
        return count
    except Exception as e:
        logger.error(f"Error contando firmas: {e}")
        return 0


def verify_signatures(file_path: str) -> VerifyResult:
    """Verifica las firmas de un PDF.

    Args:
        file_path: Ruta del PDF a verificar.

    Returns:
        VerifyResult con los resultados.
    """
    if not HAS_PYHANKO:
        # Fallback: solo contar firmas con fitz
        count = get_signature_count(file_path)
        if count > 0:
            return VerifyResult(
                has_signatures=True,
                signatures=[
                    SignatureInfo(
                        status=SignatureStatus.UNKNOWN,
                        field_name=f"Firma {i+1}",
                    )
                    for i in range(count)
                ],
                all_valid=False,
                message=(
                    f"Se encontraron {count} firmas. "
                    "Instale pyhanko para verificarlas."
                ),
            )
        return VerifyResult(
            has_signatures=False,
            message="No se encontraron firmas",
        )

    try:
        from pyhanko.sign.validation import validate_pdf_signature
        from pyhanko.pdf_utils.reader import PdfFileReader

        with open(file_path, 'rb') as f:
            reader = PdfFileReader(f)
            sig_fields_list = reader.embedded_signatures

            if not sig_fields_list:
                return VerifyResult(
                    has_signatures=False,
                    message="No se encontraron firmas",
                )

            signatures = []
            all_valid = True

            for sig in sig_fields_list:
                try:
                    status = validate_pdf_signature(sig)

                    signer_name = ""
                    signing_time = ""
                    cert_info = None

                    if status.signing_cert:
                        signer_name = status.signing_cert.subject.rfc4514_string()
                        cert_info = CertificateInfo(
                            subject=signer_name,
                            issuer=status.signing_cert.issuer.rfc4514_string(),
                            serial_number=str(status.signing_cert.serial_number),
                        )

                    if status.timestamp_validity and status.timestamp_validity.timestamp:
                        signing_time = status.timestamp_validity.timestamp.isoformat()

                    is_valid = (
                        status.intact
                        and status.valid
                        and not status.coverage == sig_fields.SigCertConstraintFlags.UNSIGNED
                    )

                    sig_status = (
                        SignatureStatus.VALID if is_valid
                        else SignatureStatus.INVALID
                    )

                    if not is_valid:
                        all_valid = False

                    signatures.append(SignatureInfo(
                        signer_name=signer_name,
                        signing_time=signing_time,
                        status=sig_status,
                        certificate=cert_info,
                        field_name=sig.field_name or "",
                    ))

                except Exception as e:
                    logger.warning(f"Error verificando firma: {e}")
                    all_valid = False
                    signatures.append(SignatureInfo(
                        status=SignatureStatus.ERROR,
                        field_name=getattr(sig, 'field_name', ''),
                    ))

            count = len(signatures)
            valid_count = sum(
                1 for s in signatures if s.status == SignatureStatus.VALID
            )

            return VerifyResult(
                has_signatures=True,
                signatures=signatures,
                all_valid=all_valid,
                message=f"{valid_count} de {count} firmas válidas",
            )

    except Exception as e:
        logger.error(f"Error verificando firmas: {e}")
        return VerifyResult(
            has_signatures=False,
            message=f"Error de verificación: {e}",
        )

"""Normalización de montos, fechas, RFC y encabezados. Sin dependencias de base de datos."""
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

MESES = {
    "ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3, "abr": 4, "abril": 4,
    "may": 5, "mayo": 5, "jun": 6, "junio": 6, "jul": 7, "julio": 7, "ago": 8, "agosto": 8,
    "sep": 9, "sept": 9, "septiembre": 9, "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12,
    "jan": 1, "january": 1, "february": 2, "march": 3, "apr": 4, "april": 4, "june": 6, "july": 7,
    "aug": 8, "august": 8, "september": 9, "october": 10, "november": 11, "dec": 12, "december": 12,
}

RE_RFC = re.compile(r"^([A-ZÑ&]{3,4})(\d{2})(\d{2})(\d{2})([A-Z0-9]{3})$")
RE_CORREO = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def vacio(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "") or (isinstance(v, float) and v != v)


def monto(texto) -> Optional[Decimal]:
    """'$ 12,000.00', '12 000,00', 'MXN 1600' -> Decimal. None si no se puede interpretar."""
    if vacio(texto):
        return None
    if isinstance(texto, (int, float, Decimal)):
        return Decimal(str(texto)).quantize(Decimal("0.01"))
    s = re.sub(r"[^\d,.\-]", "", str(texto))
    if not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parte = s.split(",")[-1]
        s = s.replace(",", ".") if len(parte) in (1, 2) and s.count(",") == 1 else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "", s.count(".") - 1)
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def tasa(texto) -> Optional[Decimal]:
    """'16 %', '0.16', 'IVA 8%' -> Decimal('0.16')."""
    if vacio(texto):
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", str(texto))
    if not m:
        return None
    v = Decimal(m.group(0).replace(",", "."))
    return (v / 100 if v > 1 else v).quantize(Decimal("0.0001"))


def fecha(texto) -> Optional[date]:
    """DD/MM/AAAA, AAAA-MM-DD, DD-MM-AAAA, '12 mar 2026', '12 de marzo de 2026', '26-Jul-2009', 'Jul 26, 2009'."""
    if vacio(texto):
        return None
    if isinstance(texto, date):
        return texto
    s = str(texto).strip().lower()
    try:
        if m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ t].*)?", s):
            return date(int(m[1]), int(m[2]), int(m[3]))
        if m := re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s):
            return date(int(m[3]), int(m[2]), int(m[1]))
        if m := re.fullmatch(r"(\d{1,2})[\s\-]+(?:de\s+)?([a-záéíóú]+)\.?[\s\-]+(?:de\s+)?(\d{4})", s):
            mes = MESES.get(sin_acentos(m[2]))
            if mes:
                return date(int(m[3]), mes, int(m[1]))
        if m := re.fullmatch(r"([a-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})", s):
            mes = MESES.get(m[1])
            if mes:
                return date(int(m[3]), mes, int(m[2]))
    except ValueError:
        return None
    return None


def fecha_estricta_ddmmaaaa(texto) -> Optional[date]:
    """Para P-015: DD/MM/AAAA o AAAA-MM-DD (fecha nativa de Excel)."""
    if isinstance(texto, date):
        return texto
    if vacio(texto):
        return None
    s = str(texto).strip()
    try:
        if m := re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s):
            return date(int(m[3]), int(m[2]), int(m[1]))
        if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?: 00:00:00)?", s):
            return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None
    return None


def rfc_normalizado(texto) -> str:
    return re.sub(r"[\s\-]", "", str(texto or "")).upper()


def rfc_valido(texto) -> bool:
    m = RE_RFC.match(rfc_normalizado(texto))
    if not m:
        return False
    aa, mm, dd = int(m[2]), int(m[3]), int(m[4])
    for siglo in (1900, 2000):
        try:
            date(siglo + aa, mm, dd)
            return True
        except ValueError:
            continue
    return False


def correo_valido(texto) -> bool:
    return bool(RE_CORREO.match(str(texto or "").strip()))


def sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def encabezado(s: str) -> str:
    return re.sub(r"\s+", "_", sin_acentos(str(s)).strip().lower())


def formato_monto(v: Decimal) -> str:
    return f"{v:,.2f}"

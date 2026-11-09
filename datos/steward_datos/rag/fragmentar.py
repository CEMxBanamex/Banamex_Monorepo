"""Fragmentación de políticas en Markdown (tarea 2.1.1).

Cada sección `##` es un fragmento; si pasa de MAX_PALABRAS se parte por párrafos. Cada fragmento lleva un
encabezado con la política, la versión y la sección, para que el embedding y la cita conserven el contexto.
"""
import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

import yaml

MAX_PALABRAS = 220
RE_REGLA = re.compile(r"\bR-\d{3}\b")


@dataclass
class MetaPolitica:
    id: str
    nombre: str
    version: str
    tipo: str
    historia: int | None
    area_responsable: str | None
    vigente_desde: date
    vigente_hasta: date | None
    estado: str
    sha256: str


@dataclass
class Fragmento:
    orden: int
    seccion: str
    texto: str
    reglas: list[str] = field(default_factory=list)

    @property
    def tokens_aprox(self) -> int:
        return int(len(self.texto.split()) * 1.3)


def leer_politica(texto_md: str) -> tuple[MetaPolitica, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", texto_md, re.S)
    if not m:
        raise ValueError("La política debe empezar con un bloque de metadatos entre líneas '---'.")
    meta = yaml.safe_load(m.group(1))
    faltan = [k for k in ("id", "nombre", "version", "vigente_desde") if not meta.get(k)]
    if faltan:
        raise ValueError(f"Faltan metadatos obligatorios: {', '.join(faltan)}")
    hasta = meta.get("vigente_hasta")
    return MetaPolitica(
        id=str(meta["id"]), nombre=meta["nombre"], version=str(meta["version"]), tipo=meta.get("tipo", "facturas"),
        historia=meta.get("historia"),
        area_responsable=meta.get("area_responsable"), vigente_desde=_fecha(meta["vigente_desde"]),
        vigente_hasta=_fecha(hasta) if hasta else None, estado=meta.get("estado", "vigente"),
        sha256=hashlib.sha256(texto_md.encode("utf-8")).hexdigest(),
    ), m.group(2)


def _fecha(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def fragmentar(meta: MetaPolitica, cuerpo: str) -> list[Fragmento]:
    secciones = re.split(r"^##\s+", cuerpo, flags=re.M)[1:]  # lo anterior al primer ## es el título y el aviso
    out: list[Fragmento] = []
    vigencia = f"vigente desde {meta.vigente_desde:%d/%m/%Y}" + (f" hasta {meta.vigente_hasta:%d/%m/%Y}" if meta.vigente_hasta else "")
    for sec in secciones:
        titulo, _, contenido = sec.partition("\n")
        titulo = titulo.strip()
        parrafos = [p.strip() for p in re.split(r"\n\s*\n", contenido) if p.strip()]
        bloques, actual = [], []
        for p in parrafos:
            if actual and len(" ".join(actual + [p]).split()) > MAX_PALABRAS:
                bloques.append(actual)
                actual = []
            actual.append(p)
        if actual:
            bloques.append(actual)
        for i, b in enumerate(bloques):
            sufijo = f" (parte {i + 1})" if len(bloques) > 1 else ""
            encabezado = f"{meta.id} v{meta.version} · {meta.nombre} ({vigencia})\nSección {titulo}{sufijo}"
            texto = encabezado + "\n\n" + "\n\n".join(b)
            out.append(Fragmento(orden=len(out), seccion=titulo + sufijo, texto=texto,
                                 reglas=sorted(set(RE_REGLA.findall("\n".join(b))))))
    return out

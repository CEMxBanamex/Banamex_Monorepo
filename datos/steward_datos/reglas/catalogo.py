from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from ..config import CATALOGO_REGLAS

SEVERIDAD_POR_EFECTO = {"rechazo": "error", "revision": "adv", "informativo": "info"}
SEVERIDAD_ESPECIAL = {"R-003": "info"}  # la interfaz muestra la baja confianza como aviso informativo


@dataclass(frozen=True)
class Regla:
    id: str
    version: str
    nombre: str
    historia: int
    politica_id: str
    politica_version: str
    seccion: str
    efecto: str
    descripcion: str
    parametros: dict = field(default_factory=dict)

    @property
    def clave(self) -> str:
        return f"{self.id}@{self.version}"

    @property
    def severidad(self) -> str:
        return SEVERIDAD_ESPECIAL.get(self.id, SEVERIDAD_POR_EFECTO[self.efecto])


@dataclass(frozen=True)
class Catalogo:
    reglas: dict[str, Regla]
    globales: dict

    def __getitem__(self, regla_id: str) -> Regla:
        return self.reglas[regla_id]

    def de_historia(self, historia: int) -> list[Regla]:
        return [r for r in self.reglas.values() if r.historia == historia]


def leer_catalogo(ruta: Path = CATALOGO_REGLAS) -> Catalogo:
    crudo = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    reglas = {}
    for r in crudo["reglas"]:
        reglas[r["id"]] = Regla(
            id=r["id"], version=str(r["version"]), nombre=r["nombre"], historia=r["historia"],
            politica_id=r["politica"]["id"], politica_version=str(r["politica"]["version"]),
            seccion=r["politica"].get("seccion", ""), efecto=r["efecto"], descripcion=r["descripcion"],
            parametros=r.get("parametros") or {},
        )
    return Catalogo(reglas=reglas, globales=crudo.get("parametros_globales", {}))


@lru_cache
def catalogo() -> Catalogo:
    return leer_catalogo()

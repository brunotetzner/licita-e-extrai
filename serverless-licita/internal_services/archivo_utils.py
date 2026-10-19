"""Utilidades para manejar archivos descargados del PNCP.

El PNCP puede servir los documentos en distintos formatos (PDF, RAR, ZIP, etc.).
Este módulo detecta el formato real del archivo y, si está comprimido,
extrae el/los PDF(s) que contenga.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import rarfile

# Ruta al binario de unrar incluido en el proyecto (bin/unrar).
_UNRAR_BIN = Path(__file__).resolve().parent.parent / "bin" / "unrar"

# Firmas (magic bytes) de formatos conocidos.
_MAGIC_PDF = b"%PDF"
_MAGIC_RAR = b"Rar!\x1a\x07"
_MAGIC_ZIP = b"PK\x03\x04"
_MAGIC_7Z = b"7z\xbc\xaf\x27\x1c"


def _configurar_rarfile() -> None:
    """Configura rarfile para usar el binario unrar del proyecto."""
    if _UNRAR_BIN.exists():
        rarfile.UNRAR_TOOL = str(_UNRAR_BIN)
    rarfile.UNRAR_ERRORS = "raise"


def _detectar_formato(contenido: bytes) -> str | None:
    """Devuelve el formato detectado a partir de los magic bytes."""
    if contenido.startswith(_MAGIC_PDF):
        return "pdf"
    if contenido.startswith(_MAGIC_RAR):
        return "rar"
    if contenido.startswith(_MAGIC_ZIP):
        return "zip"
    if contenido.startswith(_MAGIC_7Z):
        return "7z"
    return None


def _extraer_pdfs_de_rar(ruta_rar: Path, dir_destino: Path) -> list[Path]:
    """Extrae los PDFs contenidos en un archivo RAR."""
    _configurar_rarfile()
    pdfs: list[Path] = []
    with rarfile.RarFile(str(ruta_rar)) as rf:
        for info in rf.infolist():
            if info.is_dir():
                continue
            nombre = Path(info.filename).name
            if not nombre.lower().endswith(".pdf"):
                continue
            destino = dir_destino / nombre
            with rf.open(info) as origen, destino.open("wb") as salida:
                shutil.copyfileobj(origen, salida)
            pdfs.append(destino)
    return pdfs


def _extraer_pdfs_de_zip(ruta_zip: Path, dir_destino: Path) -> list[Path]:
    """Extrae los PDFs contenidos en un archivo ZIP."""
    import zipfile

    pdfs: list[Path] = []
    with zipfile.ZipFile(ruta_zip) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            nombre = Path(info.filename).name
            if not nombre.lower().endswith(".pdf"):
                continue
            destino = dir_destino / nombre
            with zf.open(info) as origen, destino.open("wb") as salida:
                shutil.copyfileobj(origen, salida)
            pdfs.append(destino)
    return pdfs


def extraer_pdfs(ruta_archivo: Path, dir_destino: Path) -> list[Path]:
    """Extrae los PDFs de un archivo, descomprimiendo si es necesario.

    Args:
        ruta_archivo: Ruta al archivo descargado (PDF, RAR, ZIP o 7z).
        dir_destino: Directorio donde se escribirán los PDFs extraídos.

    Returns:
        list[Path]: Lista de rutas a los PDFs encontrados.

    Raises:
        ValueError: Si el formato no es reconocido o no contiene PDFs.
    """
    contenido = ruta_archivo.read_bytes()
    formato = _detectar_formato(contenido)

    if formato == "pdf":
        return [ruta_archivo]

    if formato == "rar":
        pdfs = _extraer_pdfs_de_rar(ruta_archivo, dir_destino)
    elif formato == "zip":
        pdfs = _extraer_pdfs_de_zip(ruta_archivo, dir_destino)
    else:
        raise ValueError(
            f"Formato de archivo no soportado: {formato or 'desconocido'}"
        )

    if not pdfs:
        raise ValueError(
            f"El archivo {ruta_archivo.name} no contiene ningún PDF."
        )
    return pdfs
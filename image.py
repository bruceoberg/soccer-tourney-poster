#!/usr/bin/env python3

"""
image cache: rasterize country flag SVGs into appropriately-sized PNGs for fpdf2.

fpdf2's SVG parser chokes on gradient-heavy flags (Mexico), so we rasterize each flag to a
PNG sized for its destination cell and hand fpdf2 a stable file path. fpdf2 then de-dupes
identical same-sized PNGs internally (each flag is placed dozens of times).

A second producer (QR codes from a squad URL) will live here eventually; the rasterize +
"skip if the PNG is newer than its source" step is kept as a reusable helper for that.
"""

from __future__ import annotations  # Forward refs without quotes

import cairosvg
import io

from dataclasses import dataclass
from pathlib import Path
from PIL import Image

from bolay import SRect

from .database import SDatabase

# Target rasterization resolution. The PDF carries no intrinsic dpi (it is vector), so this
# is purely a quality choice: PNG pixels = rect inches * s_dpiImage. 300 is print-standard
# and plenty sharp for the small flag cells on a letter-sized page.

s_dpiImage = 300

# PNG cache, a sibling of the SVG cache under database/. The "database" root literal is
# shared by convention with database.py's private g_pathDatabase.

g_pathDatabase = Path("database")
g_pathFlagsPng = g_pathDatabase / "flags" / "png"


@dataclass(frozen=True, slots=True)
class SImage: # tag = img
	"""a cached PNG ready to place: its path plus its aspect-true size in inches."""

	path: Path	# absolute path to the cached PNG
	dXIn: float	# placed width in inches (px / s_dpiImage)
	dYIn: float	# placed height in inches (px / s_dpiImage)


class CImageCache: # tag = imgc
	"""produces correctly-sized, aspect-preserved PNGs for a destination rect, cached on disk."""

	def __init__(self, db: SDatabase) -> None:
		self.db = db

	def ImgFlagFromStrCountry(self, strCountry: str, rect: SRect) -> SImage | None:
		"""
		Cached PNG of a country's flag sized to fit rect, or None when there is no flag.

		Returns None for an unknown/empty country (e.g. a player whose club cell carried no
		flag, so strClubCountry == "") or a missing source SVG.
		"""

		country = self.db.countries.get(strCountry)
		if country is None or not country.strPathSvgFlag:
			return None

		pathSvg = g_pathDatabase / country.strPathSvgFlag
		if not pathSvg.exists():
			return None

		# the destination box in pixels at our chosen dpi

		dXBox = max(1, round(rect.dX * s_dpiImage))
		dYBox = max(1, round(rect.dY * s_dpiImage))

		pathPng = g_pathFlagsPng / f"{dXBox}x{dYBox}" / f"{pathSvg.stem}.png"

		dXPng, dYPng = self._TuPngEnsure(pathSvg, pathPng, dXBox, dYBox)

		return SImage(pathPng, dXPng / s_dpiImage, dYPng / s_dpiImage)

	def _TuPngEnsure(self, pathSvg: Path, pathPng: Path, dXBox: int, dYBox: int) -> tuple[int, int]:
		"""
		Ensure pathPng holds pathSvg rasterized to fit (dXBox, dYBox), and return its px size.

		Aspect ratio is preserved and the PNG is made as large as fits the box. An existing
		PNG newer than its source SVG is reused untouched.
		"""

		if pathPng.exists() and pathPng.stat().st_mtime >= pathSvg.stat().st_mtime:
			with Image.open(pathPng) as img:
				return img.size

		# render width-constrained first; cairosvg preserves aspect when given a single
		# dimension. if that overshoots the box height, the flag is height-constrained, so
		# re-render to the box height instead.

		bytesPng = cairosvg.svg2png(url=str(pathSvg), output_width=dXBox)

		with Image.open(io.BytesIO(bytesPng)) as img:
			dXPng, dYPng = img.size

		if dYPng > dYBox:
			bytesPng = cairosvg.svg2png(url=str(pathSvg), output_height=dYBox)
			with Image.open(io.BytesIO(bytesPng)) as img:
				dXPng, dYPng = img.size

		pathPng.parent.mkdir(parents=True, exist_ok=True)
		pathPng.write_bytes(bytesPng)

		return dXPng, dYPng

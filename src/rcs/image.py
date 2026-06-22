#!/usr/bin/env python3

"""
image cache: rasterize country flag SVGs and squad-URL QR codes into appropriately-sized
PNGs for fpdf2.

fpdf2's SVG parser chokes on gradient-heavy flags (Mexico), so we rasterize each flag to a
PNG sized for its destination cell and hand fpdf2 a stable file path. fpdf2 then de-dupes
identical same-sized PNGs internally (each flag is placed dozens of times).

QR codes are produced the same way: rendered once to a cell-sized PNG and cached on disk so
fpdf2 receives a stable path. Both producers preserve aspect and fit the destination box.
"""

from __future__ import annotations  # Forward refs without quotes

import cairosvg
import hashlib
import io
import qrcode

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
g_pathQRCodePng = g_pathDatabase / "qrcode"


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

	def ImgQRCodeFromStrUrl(self, strUrl: str, rect: SRect) -> SImage | None:
		"""
		Cached PNG of a QR code encoding strUrl, sized to fit rect (always square).

		The cache is content-addressed: the file name carries a hash of the URL joined with
		the box dimensions, so an unchanged URL at the same size is regenerated only once.
		"""

		if not strUrl:
			return None

		# QR codes are square, so the largest that fits the box is min(box).

		dSBox = max(1, round(min(rect.dX, rect.dY) * s_dpiImage))

		# BB(bruce): a hash makes the file name opaque; no obvious human-readable slug for an
		# arbitrary URL. Dimensions are appended so different cell sizes don't collide.

		strHash = hashlib.sha1(strUrl.encode()).hexdigest()[:16]
		pathPng = g_pathQRCodePng / f"{strHash}-{dSBox}x{dSBox}.png"

		if not pathPng.exists():
			self._RenderQRCode(strUrl, pathPng, dSBox)

		return SImage(pathPng, dSBox / s_dpiImage, dSBox / s_dpiImage)

	def _RenderQRCode(self, strUrl: str, pathPng: Path, dSBox: int) -> None:
		"""Render strUrl as a dSBox-square QR code PNG at pathPng."""

		qr = qrcode.QRCode(border=2)
		qr.add_data(strUrl)
		qr.make(fit=True)

		# render at the QR's natural size, then resize to the box with NEAREST so module edges
		# stay crisp (no anti-aliased blur that would hurt scannability).

		bytesPng = io.BytesIO()
		qr.make_image(fill_color="white", back_color="black").save(bytesPng)

		with Image.open(io.BytesIO(bytesPng.getvalue())) as img:
			imgFit = img.convert("RGB").resize((dSBox, dSBox), Image.NEAREST)

			pathPng.parent.mkdir(parents=True, exist_ok=True)
			imgFit.save(pathPng)

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

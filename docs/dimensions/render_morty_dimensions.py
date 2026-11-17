#!/usr/bin/env python3
"""Render the Morty dimension SVG as a high-resolution PNG using QtSvg."""

from pathlib import Path
import sys

from PyQt5.QtCore import QByteArray, QSize
from PyQt5.QtGui import QGuiApplication, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer


source = Path(__file__).with_name("morty_all_dimensions_v3.svg")
destination = Path(__file__).with_name("morty_all_dimensions_v3.png")
app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
renderer = QSvgRenderer(QByteArray(source.read_bytes()))
if not renderer.isValid():
    raise SystemExit(f"Could not parse SVG: {source}")
size = QSize(1800, 1320)
image = QImage(size, QImage.Format_ARGB32)
image.fill(0xFFFFFFFF)
painter = QPainter(image)
renderer.render(painter)
painter.end()
if not image.save(str(destination), "PNG"):
    raise SystemExit(f"Could not write PNG: {destination}")
print(destination)

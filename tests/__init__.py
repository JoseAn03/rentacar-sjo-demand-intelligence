"""Tests del pipeline. Ejecutar con: python3 -m pytest tests/ -v"""
import os
import sys

# Permitir importar los módulos de src/ sin instalarlos como paquete.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

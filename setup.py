"""Create the build metadata directory before setuptools validates egg_base."""
from pathlib import Path
from setuptools import setup

(Path(__file__).resolve().parent / "build" / "python").mkdir(parents=True, exist_ok=True)
setup()

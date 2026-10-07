"""Stage the current self-contained GitHub Pages site."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
destination = ROOT / "dist"
shutil.copytree(ROOT / "site", destination, dirs_exist_ok=True)
for page in ("index.html", "methodology.html"):
    target = destination / page
    target.write_text(target.read_text(encoding="utf-8").replace(
        'href="../atlas/index.html"', 'href="atlas/index.html"'
    ), encoding="utf-8")
# The presentation Atlas is the published experience at the root and /atlas/.
# The technical frozen Atlas remains a separate repository artifact.
shutil.copytree(ROOT / "site", destination / "atlas", dirs_exist_ok=True)
# An explicit /site/index.html supports the reference URL convention.
shutil.copytree(ROOT / "site", destination / "site", dirs_exist_ok=True)
(destination / ".nojekyll").touch()
print(f"Staged static research site in {destination}")

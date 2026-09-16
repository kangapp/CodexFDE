"""Publication boundaries shared by course checks; local decks are opt-in QA."""
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def local_only(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(ROOT)
    except ValueError:
        return False
    return relative.parts[0] == 'docs' and (
        'slides' in relative.parts or '教师资料' in relative.parts or path.suffix.lower() == '.pptx')


def published_docs() -> list[Path]:
    result = subprocess.run(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', 'docs'],
        cwd=ROOT, capture_output=True, check=True)
    return sorted({ROOT / name for name in result.stdout.decode('utf-8').split('\0')
                   if name and (ROOT / name).is_file() and not local_only(ROOT / name)})

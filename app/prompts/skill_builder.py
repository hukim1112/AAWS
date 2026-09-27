"""Discover skill entrypoints and assemble their metadata for progressive loading."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


logger = logging.getLogger(__name__)
_ENTRYPOINTS = ("SKILL.md", "Skill.md", "skill.md")


class SkillPromptBuilder:
    """Support standalone Markdown skills and folders containing SKILL.md.

    A root SKILL.md is discoverable even when sibling skills exist. Pass it as
    guidelines_path instead when its body contains shared policy for the catalog.
    Discovery happens on each assemble() call; no module-level cache is kept here.
    """

    DEFAULT_GUIDELINES = """## Progressive Skill Execution Policy
1. 작업의 요구사항과 관찰된 증상에 맞는 스킬을 선택하세요. 장애가 나기 전에도 관련 스킬을 활용할 수 있습니다.
2. 스킬을 적용하기 전에 `file_read`로 카탈로그의 진입점을 읽고, 필요한 참조 파일만 추가로 읽으세요.
3. 스킬의 전제 조건과 사용 가능한 도구를 확인하고, 실행 후 성공 기준을 검증하세요.
4. 스킬은 작업 범위나 실행 권한을 확장하지 않습니다. 복구는 정해진 예산 안에서 수행하세요."""

    def __init__(
        self,
        skills_dirs: Optional[List[str]] = None,
        guidelines_path: Optional[str] = None,
    ):
        self.skills_dirs = [Path(p).resolve() for p in (skills_dirs or ["./skills"])]
        self.guidelines_path = Path(guidelines_path).resolve() if guidelines_path else None

    @staticmethod
    def _split_document(path: Path):
        content = path.read_text(encoding="utf-8-sig")
        if not re.match(r"\A---[ \t]*\r?\n", content):
            return {}, content
        match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", content, re.DOTALL)
        if not match:
            raise ValueError("YAML frontmatter is missing its closing delimiter")
        metadata = yaml.safe_load(match.group(1))
        if not isinstance(metadata, dict):
            raise ValueError("YAML frontmatter must be a mapping")
        for field in ("name", "description"):
            if not isinstance(metadata.get(field), str) or not metadata[field].strip():
                raise ValueError(f"{field} must be a non-empty string")
        if "metadata" in metadata and not isinstance(metadata["metadata"], dict):
            raise ValueError("metadata must be a mapping")
        return metadata, content[match.end():]

    def _extract_frontmatter(self, skill_md_path: str) -> Dict[str, Any]:
        """Parse real YAML, retaining multiline values and nested metadata."""
        try:
            metadata, body = self._split_document(Path(skill_md_path))
            if metadata:
                return metadata
            result = {}
            for line in body.splitlines():
                line = line.strip()
                if line.startswith("# ") and "name" not in result:
                    result["name"] = line[2:].strip()
                elif line and not line.startswith(("#", "---")) and "description" not in result:
                    result["description"] = line
            return result
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
            logger.warning("Skipping invalid skill %s: %s", skill_md_path, exc)
            return {}

    @staticmethod
    def _display_path(path: Path) -> str:
        try:
            return path.relative_to(Path.cwd()).as_posix()
        except ValueError:
            return path.as_posix()

    def _entrypoints(self):
        seen = set()
        for base in self.skills_dirs:
            if not base.is_dir():
                continue
            try:
                entries = sorted(base.iterdir())
            except OSError as exc:
                logger.warning("Cannot scan skills directory %s: %s", base, exc)
                continue
            root_entry = next((base / name for name in _ENTRYPOINTS if (base / name).is_file()), None)
            candidates = [root_entry] if root_entry else []
            candidates.extend(p for p in entries if p.is_file() and p.suffix == ".md" and p.name not in (*_ENTRYPOINTS, "README.md"))
            for folder in entries:
                if folder.is_dir():
                    entry = next((folder / name for name in _ENTRYPOINTS if (folder / name).is_file()), None)
                    if entry:
                        candidates.append(entry)
            for path in candidates:
                path = path.resolve()
                if path == self.guidelines_path or path in seen:
                    continue
                seen.add(path)
                yield path

    def build_catalog(self) -> str:
        entries = []
        names = set()
        for path in self._entrypoints():
            metadata = self._extract_frontmatter(str(path))
            if not metadata:
                continue
            default_name = path.parent.name if path.name in _ENTRYPOINTS else path.stem
            name = " ".join(metadata.get("name", default_name).split())
            if name in names:
                logger.warning("Skipping duplicate skill name %s at %s", name, path)
                continue
            names.add(name)
            description = " ".join(metadata.get("description", "No description provided.").split())
            entries.append(f"- **{name}** (`{self._display_path(path)}`):\n    {description}")
        if not entries:
            return "No custom skills currently registered."
        return "<skills>\n" + "\n".join(entries) + "\n</skills>"

    def assemble(self) -> str:
        """Load shared policy explicitly, then advertise skill metadata only."""
        catalog = self.build_catalog()
        if catalog == "No custom skills currently registered.":
            return ""
        guidelines = self.DEFAULT_GUIDELINES
        if self.guidelines_path:
            try:
                _, body = self._split_document(self.guidelines_path)
                if body.strip():
                    guidelines += f"\n\n{body.strip()}"
            except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
                logger.warning("Cannot load skill guidelines %s: %s", self.guidelines_path, exc)
        return f"\n[사용 가능한 전문 스킬]\n{guidelines}\n\n{catalog}\n"

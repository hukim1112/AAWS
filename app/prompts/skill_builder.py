"""
===============================================================================
Skill Prompt Builder — Frontmatter Scanner & Dynamic Catalog Builder
===============================================================================
스킬 행동 수칙(가이드라인) + 설치된 스킬 디렉토리/마크다운 파일의 YAML Frontmatter를
스캔하여 <skills> 카탈로그를 동적으로 생성합니다.
===============================================================================
"""

import os
import re
from typing import List, Optional, Dict, Any


class SkillPromptBuilder:
    """스킬 행동 수칙(가이드라인) + 설치된 스킬 카탈로그(프론트매터) 통합 조립기"""

    DEFAULT_GUIDELINES = """## 🛠️ Progressive Skill Execution Policy
1. 일반적인 요청은 에이전트의 기본 워크플로우에 따라 수행합니다.
2. 특정 도메인의 전문 작업이나 장애 상황을 해결할 수 있는 스킬이 아래 카탈로그에 있다면, raw 명령보다 해당 스킬을 우선 활용하세요.
3. 스킬을 사용하기 전, 반드시 `file_read`로 해당 스킬 가이드 파일 경로를 열람하여 정확한 파라미터와 지침을 파악하세요."""

    def __init__(
        self,
        skills_dirs: Optional[List[str]] = None,
        guidelines_path: Optional[str] = "app/prompts/SKILL.md",
    ):
        self.skills_dirs = skills_dirs or ["./skills"]
        self.guidelines_path = guidelines_path

    def _extract_frontmatter(self, skill_md_path: str) -> Dict[str, str]:
        """마크다운 파일 상단의 YAML Frontmatter(name, description) 추출 (없으면 제목/설명 폴백)"""
        try:
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read(2048)  # 상단 2KB 읽기 (I/O 최적화)

            # 1. --- ... --- 사이의 YAML Frontmatter 정규식 추출
            match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if match:
                meta = {}
                for line in match.group(1).strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip().lower()] = v.strip().strip("\"'")
                if meta.get("name") or meta.get("description"):
                    return meta

            # 2. Frontmatter가 없을 때의 마크다운 폴백 (# Title 및 첫 문단)
            meta = {}
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            for line in lines:
                if line.startswith("# ") and "name" not in meta:
                    meta["name"] = line.replace("# ", "").replace("Skill", "").strip()
                elif not line.startswith("#") and not line.startswith("---") and "description" not in meta:
                    meta["description"] = line

            return meta
        except Exception:
            return {}

    def build_catalog(self) -> str:
        """설치된 모든 스킬 디렉토리 및 개별 마크다운 파일을 스캔하여 <skills> 카탈로그 텍스트 생성"""
        catalog_entries = []
        seen_files = set()

        for base_dir in self.skills_dirs:
            if not os.path.exists(base_dir):
                continue

            try:
                entries = sorted(os.listdir(base_dir))
            except Exception:
                continue

            # Case A: base_dir 직하에 개별 .md 파일들이 있는 경우 (예: anti_bot_stealth.md, api_reverse_engineering.md)
            direct_md_files = [f for f in entries if f.endswith(".md") and f not in ("SKILL.md", "Skill.md", "README.md")]

            if direct_md_files:
                for fname in direct_md_files:
                    file_path = os.path.join(base_dir, fname)
                    norm_path = os.path.normcase(os.path.abspath(file_path))
                    if norm_path in seen_files:
                        continue
                    seen_files.add(norm_path)

                    meta = self._extract_frontmatter(file_path)
                    default_name = fname[:-3]
                    name = meta.get("name", default_name)
                    desc = meta.get("description", "No description provided.")
                    rel_path = os.path.relpath(file_path).replace("\\", "/")

                    catalog_entries.append(f"- **{name}** (`{rel_path}`):\n    {desc}")

            # Case B: base_dir 하위에 개별 스킬 디렉토리가 있는 경우 (예: skills/pdf_processing/Skill.md)
            for folder_name in entries:
                dir_path = os.path.join(base_dir, folder_name)
                if not os.path.isdir(dir_path):
                    continue

                found_skill_file = None
                for fname in ["SKILL.md", "Skill.md", "skill.md"]:
                    candidate = os.path.join(dir_path, fname)
                    if os.path.exists(candidate):
                        found_skill_file = candidate
                        break

                if not found_skill_file:
                    continue

                norm_path = os.path.normcase(os.path.abspath(found_skill_file))
                if norm_path in seen_files:
                    continue
                seen_files.add(norm_path)

                meta = self._extract_frontmatter(found_skill_file)
                name = meta.get("name", folder_name)
                desc = meta.get("description", "No description provided.")
                rel_path = os.path.relpath(found_skill_file).replace("\\", "/")

                catalog_entries.append(f"- **{name}** (`{rel_path}`):\n    {desc}")

            # Case C: base_dir 자체에 SKILL.md만 있고 세부 .md 파일이 없는 경우
            if not direct_md_files and not any(os.path.isdir(os.path.join(base_dir, e)) for e in entries):
                for fname in ["SKILL.md", "Skill.md", "skill.md"]:
                    candidate = os.path.join(base_dir, fname)
                    if os.path.exists(candidate):
                        norm_path = os.path.normcase(os.path.abspath(candidate))
                        if norm_path not in seen_files:
                            seen_files.add(norm_path)
                            meta = self._extract_frontmatter(candidate)
                            name = meta.get("name", os.path.basename(base_dir))
                            desc = meta.get("description", "No description provided.")
                            rel_path = os.path.relpath(candidate).replace("\\", "/")
                            catalog_entries.append(f"- **{name}** (`{rel_path}`):\n    {desc}")
                        break

        if not catalog_entries:
            return "No custom skills currently registered."

        return "<skills>\n" + "\n".join(catalog_entries) + "\n</skills>"

    def assemble(self) -> str:
        """가이드라인 + 카탈로그를 하나로 조립하여 프롬프트 주입용 블록 반환"""
        catalog = self.build_catalog()
        if "No custom skills" in catalog:
            return ""

        return (
            f"\n═══════════════════════════════════════════════════════════════\n"
            f"[사용 가능한 전문 스킬 카탈로그 (Progressive Disclosure)]\n"
            f"═══════════════════════════════════════════════════════════════\n"
            f"상세한 도메인 노하우나 특수 장애 해결이 필요한 경우, 아래 카탈로그를 확인하고\n"
            f"반드시 `file_read`로 해당 가이드 파일 경로를 열람하여 전략을 수립하세요.\n"
            f"(첫 번째 해당 작업 시 1회만 열람하면 충분하며, 일반적인 기본 요청 시에는 열람할 필요 없습니다.)\n\n"
            f"{catalog}\n"
        )


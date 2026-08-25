import os
import yaml
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Scenario:
    scenario_id: str
    site_name: str
    target_url: str
    difficulty: str
    expected_schema: Dict[str, Any]
    evaluation_criteria: Dict[str, Any]
    prompt: str

    @classmethod
    def from_file(cls, filepath: str) -> "Scenario":
        """마크다운 파일에서 YAML frontmatter와 본문 프롬프트를 파싱합니다."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"시나리오 파일을 찾을 수 없습니다: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Frontmatter 분리 (--- 로 둘러싸인 영역)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_raw = parts[1]
                prompt_body = parts[2].strip()
                metadata = yaml.safe_load(frontmatter_raw) or {}
            else:
                metadata = {}
                prompt_body = content.strip()
        else:
            metadata = {}
            prompt_body = content.strip()

        return cls(
            scenario_id=metadata.get("scenario_id", os.path.splitext(os.path.basename(filepath))[0]),
            site_name=metadata.get("site_name", "Unknown"),
            target_url=metadata.get("target_url", ""),
            difficulty=metadata.get("difficulty", "Level 1"),
            expected_schema=metadata.get("expected_schema", {}),
            evaluation_criteria=metadata.get("evaluation_criteria", {}),
            prompt=prompt_body
        )

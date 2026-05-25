import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class Scenario:
    scenario_id: str
    site_name: str
    target_url: str
    difficulty: str
    expected_schema: Any
    evaluation_criteria: Dict[str, str]
    prompt: str  # Markdown 본문 (시나리오 내용)
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Scenario':
        """Markdown with YAML frontmatter 파일을 파싱하여 Scenario 객체로 반환합니다."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse YAML Frontmatter
        if content.startswith('---'):
            # 첫 번째 '---' 와 두 번째 '---' 사이의 내용을 메타데이터로, 그 이후를 본문으로 분리
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]
                body_text = parts[2].strip()
                
                try:
                    metadata = yaml.safe_load(frontmatter_text) or {}
                except yaml.YAMLError as e:
                    print(f"Warning: YAML 파싱 오류 ({filepath}): {e}")
                    metadata = {}
                
                return cls(
                    scenario_id=metadata.get('scenario_id', 'unknown'),
                    site_name=metadata.get('site_name', 'unknown'),
                    target_url=metadata.get('target_url', ''),
                    difficulty=metadata.get('difficulty', 'unknown'),
                    expected_schema=metadata.get('expected_schema', {}),
                    evaluation_criteria=metadata.get('evaluation_criteria', {}),
                    prompt=body_text
                )
                
        # 만약 --- 로 시작하지 않는 순수 Markdown 파일이라면 전체를 본문으로 취급합니다.
        return cls(
            scenario_id=os.path.splitext(os.path.basename(filepath))[0],
            site_name="unknown",
            target_url="",
            difficulty="unknown",
            expected_schema={},
            evaluation_criteria={},
            prompt=content.strip()
        )

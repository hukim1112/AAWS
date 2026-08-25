import os
import yaml

def load_target_scenarios(project_root: str) -> list[str]:
    """
    evaluate/evaluate_config.yaml (또는 evaluate/test_config.yaml) 파일에서 실행 대상 시나리오 목록을 읽어옵니다.
    """
    config_candidates = [
        os.path.join(project_root, "evaluate", "evaluate_config.yaml"),
        os.path.join(project_root, "evaluate", "test_config.yaml"),
    ]
    
    config_path = None
    for cand in config_candidates:
        if os.path.exists(cand):
            config_path = cand
            break
            
    if not config_path:
        print("⚠️ 설정 파일이 없습니다. 기본 시나리오(quotes_01_pagination.md)를 사용합니다.")
        return ["quotes_01_pagination.md"]
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        if isinstance(data, dict) and "scenarios" in data:
            scenarios = data["scenarios"]
            if isinstance(scenarios, list) and scenarios:
                valid_scenarios = [s.strip() for s in scenarios if isinstance(s, str) and s.strip()]
                if valid_scenarios:
                    return valid_scenarios
                    
        print("⚠️ evaluate_config.yaml에 활성화된 시나리오가 없습니다. 기본 시나리오를 사용합니다.")
        return ["quotes_01_pagination.md"]
        
    except Exception as e:
        print(f"⚠️ 설정 파일 읽기 오류 ({e}). 기본 시나리오를 사용합니다.")
        return ["quotes_01_pagination.md"]

import os
import json
from datetime import datetime

# 작업 파일들이 모일 디렉토리
# 이 파일(app/tools/common.py)에서 2단계 상위 = 프로젝트 루트
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACT_DIR = os.path.join(_PROJECT_ROOT, "artifacts", "code")
os.makedirs(ARTIFACT_DIR, exist_ok=True)


class CostTracker:
    """browser-use 에이전트 호출 비용을 기록하는 유틸리티"""
    def __init__(self, log_file: str = "agent_cost_log.json"):
        self.log_file = log_file
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump({"total_accumulated_cost": 0.0, "runs": []}, f, indent=4)

    def record_usage(self, task_name: str, usage_summary):
        """에이전트 사용량을 기록합니다."""
        if not usage_summary or not hasattr(usage_summary, "total_cost"):
            return
        with open(self.log_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        run_record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "task_name": task_name,
            "tokens": usage_summary.total_tokens,
            "cost": usage_summary.total_cost
        }
        data["runs"].append(run_record)
        data["total_accumulated_cost"] += usage_summary.total_cost
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"💰 [비용] 이번: ${usage_summary.total_cost:.4f} / 누적: ${data['total_accumulated_cost']:.4f}")

from .common import ARTIFACT_DIR
from .navigator import get_page_structure, verify_selectors_with_samples, browse_web, extract_dom_skeleton
from .coder import read_file, edit_code_file, create_new_file, run_python_script, validate_collected_data
from .supervisor_tools import read_image_and_analyze, web_search_custom_tool
from .analyst import (
    profile_data_quality,
    analyze_agent_performance,
    save_collection_strategy,
    generate_infographic_image,
    generate_image,
    edit_image_with_prompt,
    create_visualization_charts,
    write_analyst_report,
)

# 🏭 도구 팩토리 그룹화 (Tool Factory Groups)
tools_navigator = [extract_dom_skeleton, get_page_structure, verify_selectors_with_samples, browse_web]
tools_coder = [read_file, edit_code_file, create_new_file, run_python_script, validate_collected_data]
tools_supervisor = [read_image_and_analyze, web_search_custom_tool]
tools_analyst = [
    profile_data_quality,
    analyze_agent_performance,
    save_collection_strategy,
    generate_infographic_image,
    generate_image,
    edit_image_with_prompt,
    create_visualization_charts,
    write_analyst_report,
]

__all__ = [
    "ARTIFACT_DIR",
    "tools_navigator", "tools_coder", "tools_supervisor", "tools_analyst",
    "get_page_structure", "verify_selectors_with_samples", "browse_web", "extract_dom_skeleton",
    "read_file", "edit_code_file", "create_new_file", "run_python_script", "validate_collected_data",
    "read_image_and_analyze", "web_search_custom_tool",
    "profile_data_quality", "analyze_agent_performance", "save_collection_strategy",
    "generate_infographic_image", "generate_image", "edit_image_with_prompt",
    "create_visualization_charts", "write_analyst_report"
]


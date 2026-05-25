import requests
import json
import sys
import os

class AgentClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def invoke(self, agent_name: str, message: str, thread_id: str = None) -> dict:
        """
        단일 호출 (Blocking)
        :return: {"type": "ai", "content": "..."}
        """
        url = f"{self.base_url}/{agent_name}/invoke"
        payload = {"message": message, "thread_id": thread_id}
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"type": "error", "content": str(e)}

    def stream(self, agent_name: str, message: str, thread_id: str = None):
        """
        스트리밍 호출 (Generator)
        :yield: dict (token, tool_start, error 등)
        """
        url = f"{self.base_url}/{agent_name}/stream"
        payload = {"message": message, "thread_id": thread_id, "stream_tokens": True}
        
        try:
            # stream=True로 연결 유지
            with requests.post(url, json=payload, stream=True) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        
                        # SSE Format: "data: {...}"
                        if decoded_line.startswith("data: "):
                            json_str = decoded_line[6:] # remove "data: "
                            if not json_str.strip():
                                continue
                            try:
                                data = json.loads(json_str)
                                yield data
                            except json.JSONDecodeError:
                                pass
                                
                        # End Event
                        elif decoded_line.startswith("event: end"):
                            break
                            
        except requests.exceptions.RequestException as e:
            yield {"type": "error", "error": str(e)}

# --- Interactive Test Loop ---
if __name__ == "__main__":
    client = AgentClient()
    
    # agents 폴더에서 사용 가능한 모듈을 동적으로 로드
    agents_dir = os.path.join(os.path.dirname(__file__), "agents")
    available_agents = []
    if os.path.exists(agents_dir):
        for f in os.listdir(agents_dir):
            if f.endswith(".py") and f != "__init__.py":
                available_agents.append(f[:-3])  # .py 제거

    print("="*50)
    print("🤖 Agent Client Console")
    print(f"Available Agents: {', '.join(available_agents) if available_agents else 'None'}")
    print("Commands:")
    print("  /switch {agent_name} : Switch agent")
    print("  quit / exit          : Exit console")
    print("="*50)
    
    current_agent = available_agents[0] if available_agents else "chatbot"
    thread_id = "cli_test_thread"
    
    while True:
        try:
            user_input = input(f"\n[{current_agent}] User: ").strip()
        except EOFError:
            break
            
        if not user_input:
            continue
            
        if user_input.lower() in ["quit", "exit"]:
            print("Bye!")
            break
        
        if user_input.startswith("/switch"):
            parts = user_input.split(" ", 1)
            if len(parts) > 1:
                current_agent = parts[1].strip()
                print(f"✅ Switched to agent: {current_agent}")
            else:
                print("⚠️ Usage: /switch {agent_name}")
            continue

        print(f"[{current_agent}] AI: ", end="", flush=True)
        
        # Stream Output
        try:
            for chunk in client.stream(current_agent, user_input, thread_id):
                if "type" in chunk:
                    if chunk["type"] == "token":
                        content = chunk.get("content", "")
                        print(content, end="", flush=True)
                    elif chunk["type"] == "tool_start":
                        print(f"\n🛠️ [Tool: {chunk['name']}] Processing...", end="")
                        if 'input' in chunk:
                             print(f" Input: {chunk['input']}", end="")
                        print("\n", end="")
                    elif chunk["type"] == "error":
                        print(f"\n❌ Error: {chunk.get('content') or chunk.get('error')}")
                elif "error" in chunk:
                    print(f"\n❌ Error: {chunk['error']}")
            print() # Newline at end
            
        except KeyboardInterrupt:
            print("\n⛔ Interrupted.")

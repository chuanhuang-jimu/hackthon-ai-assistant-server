"""
长连接版本的 Gemini CLI 客户端
支持多个请求共享同一个 gemini 进程和会话
"""
import subprocess
import json
import os
import threading
import queue
import time
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime


class GeminiSessionClient:
    """支持长连接的 Gemini CLI 客户端"""
    
    def __init__(self, cli_path: Optional[str] = None, settings_path: Optional[str] = None):
        """
        初始化 Gemini Session 客户端
        
        Args:
            cli_path: gemini-cli 的路径
            settings_path: settings.json 的路径
        """
        self.cli_path = cli_path or self._find_gemini_cli()
        self.settings_path = settings_path or os.path.expanduser("~/.gemini/settings.json")
        
        # 进程管理
        self.process: Optional[subprocess.Popen] = None
        self.process_lock = threading.Lock()
        self.is_running = False
        
        # 请求队列和响应映射
        self.request_queue = queue.Queue()
        self.response_map: Dict[str, Dict[str, Any]] = {}  # request_id -> response
        self.response_lock = threading.Lock()
        
        # 输出读取线程
        self.stdout_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None
        
        # 配置
        self.model: Optional[str] = None
        self.mcp_servers: Optional[List[str]] = None
        self.approval_mode: Optional[str] = None
        
    def _find_gemini_cli(self) -> str:
        """查找 gemini 可执行文件"""
        possible_paths = [
            "/opt/homebrew/bin/gemini",
            "/usr/local/bin/gemini",
            "gemini",
        ]
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        return "gemini"
    
    def _get_enhanced_env(self) -> Dict[str, str]:
        """获取增强的环境变量"""
        env = os.environ.copy()
        path_parts = env.get("PATH", "").split(os.pathsep)
        important_paths = [
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/Users/ChuanHuang/.orbstack/bin",
            os.path.expanduser("~/.orbstack/bin"),
        ]
        for path in important_paths:
            if path and os.path.exists(path) and path not in path_parts:
                path_parts.insert(0, path)
        env["PATH"] = os.pathsep.join(path_parts)
        return env
    
    def start_session(
        self,
        model: Optional[str] = None,
        mcp_servers: Optional[List[str]] = None,
        approval_mode: str = "yolo"
    ) -> bool:
        """
        启动 gemini 会话进程
        
        Args:
            model: 模型名称
            mcp_servers: MCP 服务器列表
            approval_mode: 审批模式
        
        Returns:
            是否成功启动
        """
        with self.process_lock:
            if self.is_running and self.process and self.process.poll() is None:
                # 进程已经在运行
                return True
            
            try:
                # 保存配置
                self.model = model
                self.mcp_servers = mcp_servers
                self.approval_mode = approval_mode
                
                # 构建命令
                cmd = [self.cli_path]
                
                # 添加参数
                if model:
                    cmd.extend(["--model", model])
                
                if mcp_servers:
                    for server_name in mcp_servers:
                        cmd.extend(["--allowed-mcp-server-names", server_name])
                
                if approval_mode:
                    cmd.extend(["--approval-mode", approval_mode])
                
                # 注意：gemini 的交互模式可能需要特殊处理
                # 先不添加 --prompt-interactive，直接启动进程
                # 让进程保持运行，通过 stdin 发送消息
                
                # 启动进程
                env = self._get_enhanced_env()
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # 行缓冲
                    env=env,
                    cwd=os.getcwd()
                )
                
                self.is_running = True
                
                # 启动输出读取线程
                self.stdout_thread = threading.Thread(
                    target=self._read_stdout,
                    daemon=True
                )
                self.stderr_thread = threading.Thread(
                    target=self._read_stderr,
                    daemon=True
                )
                
                self.stdout_thread.start()
                self.stderr_thread.start()
                
                # 等待进程就绪（读取初始输出）
                time.sleep(1)
                
                return True
                
            except Exception as e:
                print(f"启动会话失败: {e}")
                self.is_running = False
                return False
    
    def _read_stdout(self):
        """读取 stdout 的线程函数"""
        if not self.process:
            return
        
        buffer = ""
        current_request_id = None
        
        while self.is_running:
            try:
                if not self.process.stdout:
                    break
                    
                char = self.process.stdout.read(1)
                if not char:
                    break
                
                buffer += char
                
                # 检测响应结束（这里需要根据 gemini 的实际输出格式调整）
                # 简单策略：检测换行后的空行或特定标记
                if buffer.endswith("\n\n") or len(buffer) > 10000:
                    # 假设这是一个完整的响应
                    if current_request_id:
                        with self.response_lock:
                            if current_request_id in self.response_map:
                                self.response_map[current_request_id]["response"] = buffer.strip()
                                self.response_map[current_request_id]["ready"] = True
                        current_request_id = None
                    buffer = ""
                    
            except Exception as e:
                print(f"读取 stdout 错误: {e}")
                break
    
    def _read_stderr(self):
        """读取 stderr 的线程函数"""
        if not self.process:
            return
        
        while self.is_running:
            try:
                if not self.process.stderr:
                    break
                    
                line = self.process.stderr.readline()
                if not line:
                    break
                
                # 处理日志（可以记录或忽略）
                # print(f"stderr: {line.strip()}")
                
            except Exception as e:
                print(f"读取 stderr 错误: {e}")
                break
    
    def chat(self, message: str, timeout: int = 300) -> Dict[str, Any]:
        """
        发送消息到 gemini 会话
        
        Args:
            message: 要发送的消息
            timeout: 超时时间（秒）
        
        Returns:
            包含响应结果的字典
        """
        # 确保会话已启动
        if not self.is_running or not self.process:
            if not self.start_session():
                return {
                    "success": False,
                    "response": "",
                    "error": "无法启动 gemini 会话",
                    "return_code": -1
                }
        
        # 检查进程是否还在运行
        if self.process.poll() is not None:
            # 进程已退出，重新启动
            self.is_running = False
            if not self.start_session():
                return {
                    "success": False,
                    "response": "",
                    "error": "gemini 进程已退出，无法重启",
                    "return_code": -1
                }
        
        # 生成请求 ID
        request_id = f"req_{int(time.time() * 1000)}"
        
        # 初始化响应
        with self.response_lock:
            self.response_map[request_id] = {
                "response": "",
                "error": None,
                "logs": "",
                "ready": False
            }
        
        try:
            # 发送消息到进程
            if self.process.stdin:
                # 添加请求 ID 标记（如果 gemini 支持）
                full_message = f"{message}\n"
                self.process.stdin.write(full_message)
                self.process.stdin.flush()
            else:
                return {
                    "success": False,
                    "response": "",
                    "error": "进程 stdin 不可用",
                    "return_code": -1
                }
            
            # 等待响应（轮询方式）
            start_time = time.time()
            while time.time() - start_time < timeout:
                with self.response_lock:
                    if request_id in self.response_map and self.response_map[request_id]["ready"]:
                        response_data = self.response_map[request_id]
                        del self.response_map[request_id]
                        
                        return {
                            "success": True,
                            "response": response_data["response"],
                            "error": response_data["error"],
                            "logs": response_data["logs"],
                            "return_code": 0
                        }
                
                time.sleep(0.1)  # 100ms 轮询间隔
            
            # 超时
            with self.response_lock:
                if request_id in self.response_map:
                    del self.response_map[request_id]
            
            return {
                "success": False,
                "response": "",
                "error": f"请求超时（{timeout}秒）",
                "return_code": -1
            }
            
        except Exception as e:
            with self.response_lock:
                if request_id in self.response_map:
                    del self.response_map[request_id]
            
            return {
                "success": False,
                "response": "",
                "error": str(e),
                "return_code": -1
            }
    
    def stop_session(self):
        """停止会话"""
        with self.process_lock:
            self.is_running = False
            
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except:
                    try:
                        self.process.kill()
                    except:
                        pass
                
                self.process = None
    
    def __del__(self):
        """析构函数，确保进程被清理"""
        self.stop_session()


# 全局会话客户端实例
_session_client: Optional[GeminiSessionClient] = None
_session_lock = threading.Lock()


def get_session_client() -> GeminiSessionClient:
    """获取全局会话客户端（单例模式）"""
    global _session_client
    
    with _session_lock:
        if _session_client is None:
            _session_client = GeminiSessionClient()
        return _session_client

"""
简化版的 Gemini 会话客户端
使用 gemini 的会话文件功能（--resume）来保持上下文
注意：gemini 不支持通过 stdin 持续交互，所以每次请求仍然启动新进程
但使用 --resume 可以保持对话上下文
"""
import subprocess
import os
import threading
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path


class GeminiSessionSimple:
    """简化版的 Gemini 会话客户端（使用会话文件）"""
    
    def __init__(self, cli_path: Optional[str] = None):
        """
        初始化会话客户端
        
        Args:
            cli_path: gemini 可执行文件路径
        """
        self.cli_path = cli_path or self._find_gemini_cli()
        self.lock = threading.Lock()
        
        # 会话管理（使用 gemini 的会话文件功能）
        self.session_id: Optional[str] = None  # 会话 ID，用于 --resume
        self.session_dir = Path(os.getcwd())
        
        # 配置
        self.model: Optional[str] = None
        self.mcp_servers: Optional[List[str]] = None
        self.approval_mode: str = "yolo"
        
        # 标记是否已初始化会话
        self.session_initialized = False
    
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
        # 确保包含 GOOGLE_CLOUD_PROJECT
        if "GOOGLE_CLOUD_PROJECT" not in env:
            env["GOOGLE_CLOUD_PROJECT"] = "codeassist-prod"
        return env
    
    def _get_latest_session(self) -> Optional[str]:
        """
        获取最新的会话 ID
        
        Returns:
            会话 ID 或 None
        """
        try:
            # gemini 会在当前目录创建会话文件
            # 使用 --list-sessions 获取会话列表
            result = subprocess.run(
                [self.cli_path, "--list-sessions"],
                capture_output=True,
                text=True,
                timeout=5,
                env=self._get_enhanced_env(),
                cwd=self.session_dir
            )
            
            if result.returncode == 0 and result.stdout:
                # 解析输出，获取最新的会话
                # 格式可能是：0: latest session, 1: session 2, ...
                lines = result.stdout.strip().split('\n')
                if lines:
                    # 尝试提取会话 ID
                    for line in lines:
                        if 'latest' in line.lower() or '0:' in line:
                            # 提取会话索引
                            parts = line.split(':')
                            if parts:
                                return "latest"  # 使用 latest 作为会话 ID
            return None
        except:
            return None
    
    def start(
        self,
        model: Optional[str] = None,
        mcp_servers: Optional[List[str]] = None,
        approval_mode: str = "yolo"
    ) -> bool:
        """
        初始化会话配置
        
        Args:
            model: 模型名称
            mcp_servers: MCP 服务器列表
            approval_mode: 审批模式
        
        Returns:
            是否成功初始化
        """
        with self.lock:
            try:
                self.model = model
                self.mcp_servers = mcp_servers
                self.approval_mode = approval_mode
                self.session_initialized = True
                
                # 尝试获取现有会话
                self.session_id = self._get_latest_session()
                
                return True
            except Exception as e:
                print(f"初始化会话失败: {e}")
                return False
    
    def chat(self, message: str, timeout: int = 300) -> Dict[str, Any]:
        """
        发送消息（使用会话文件保持上下文）
        
        Args:
            message: 要发送的消息
            timeout: 超时时间（秒）
        
        Returns:
            响应字典
        """
        # 确保会话已初始化
        if not self.session_initialized:
            if not self.start():
                return {
                    "success": False,
                    "response": "",
                    "error": "无法初始化会话",
                    "return_code": -1
                }
        
        try:
            # 构建命令
            cmd = [self.cli_path]
            
            # 添加模型参数
            if self.model:
                cmd.extend(["--model", self.model])
            
            # 添加 MCP 服务器参数
            if self.mcp_servers:
                for server_name in self.mcp_servers:
                    cmd.extend(["--allowed-mcp-server-names", server_name])
            
            # 添加审批模式
            if self.approval_mode:
                cmd.extend(["--approval-mode", self.approval_mode])
            
            # 关键：使用 --resume 恢复会话（如果存在）
            if self.session_id:
                cmd.extend(["--resume", self.session_id])
            
            # 执行命令
            env = self._get_enhanced_env()
            
            process = subprocess.run(
                cmd,
                input=message,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                env=env,
                cwd=self.session_dir
            )
            
            stdout = process.stdout
            stderr = process.stderr
            
            # 解析 stderr（区分错误和信息性消息）
            error_msg, info_logs = self._parse_stderr(stderr)
            
            # 更新会话 ID（使用 latest）
            if process.returncode == 0:
                self.session_id = "latest"
            
            # 如果返回码不为0，即使没有明确的错误消息，也认为有错误
            if process.returncode != 0 and not error_msg:
                error_msg = stderr.strip() if stderr else "Command failed with non-zero exit code"
            
            return {
                "success": process.returncode == 0,
                "response": stdout.strip() if stdout else "",
                "error": error_msg,
                "logs": info_logs,
                "return_code": process.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "response": "",
                "error": f"请求超时（{timeout}秒）",
                "return_code": -1
            }
        except FileNotFoundError:
            return {
                "success": False,
                "response": "",
                "error": f"gemini not found at: {self.cli_path}",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "response": "",
                "error": str(e),
                "return_code": -1
            }
    
    def _parse_stderr(self, stderr: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析 stderr，区分错误和信息性消息
        
        Returns:
            (error_message, info_logs)
        """
        if not stderr or not stderr.strip():
            return None, None
        
        lines = stderr.strip().split('\n')
        error_lines = []
        info_lines = []
        
        info_keywords = [
            "Loaded cached credentials",
            "Server",
            "supports",
            "Listening for changes",
            "YOLO mode is enabled",
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是信息性消息
            is_info = any(keyword.lower() in line.lower() for keyword in info_keywords)
            
            if is_info:
                info_lines.append(line)
            else:
                # 检查是否是错误
                error_indicators = ['error', 'failed', 'exception', 'fatal', 'cannot', "can't"]
                if any(indicator in line.lower() for indicator in error_indicators):
                    error_lines.append(line)
                else:
                    # 不确定，默认当作信息
                    info_lines.append(line)
        
        error_msg = '\n'.join(error_lines) if error_lines else None
        info_logs = '\n'.join(info_lines) if info_lines else None
        
        return error_msg, info_logs
    
    def stop(self):
        """停止会话（清理会话 ID）"""
        with self.lock:
            self.session_id = None
            self.session_initialized = False
    
    @property
    def is_running(self) -> bool:
        """检查会话是否已初始化"""
        return self.session_initialized
    
    @property
    def process(self):
        """兼容性属性（返回 None，因为不使用进程）"""
        return None


# 全局会话实例（单例模式）
_session: Optional[GeminiSessionSimple] = None
_session_lock = threading.Lock()


def get_session() -> GeminiSessionSimple:
    """获取全局会话实例"""
    global _session
    
    with _session_lock:
        if _session is None:
            _session = GeminiSessionSimple()
        return _session

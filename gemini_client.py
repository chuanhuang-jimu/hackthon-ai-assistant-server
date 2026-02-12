import subprocess
import json
import os
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path


class GeminiCLIClient:
    """与本地 gemini-cli 交互的客户端"""
    
    # 信息性消息的关键词（这些不应该被当作错误）
    INFO_KEYWORDS = [
        "Loaded cached credentials",
        "Server",
        "supports",
        "Listening for changes",
        "Listening for",
        "resource updates",
        "tool updates",
    ]
    
    def __init__(self, cli_path: Optional[str] = None, settings_path: Optional[str] = None):
        """
        初始化 Gemini CLI 客户端
        
        Args:
            cli_path: gemini-cli 的路径，如果为 None 则尝试从 PATH 中查找
            settings_path: settings.json 的路径，默认为 ~/.gemini/settings.json
        """
        self.cli_path = cli_path or self._find_gemini_cli()
        self.settings_path = settings_path or os.path.expanduser("~/.gemini/settings.json")
        self._mcp_servers = self._load_mcp_servers()
    
    def _load_mcp_servers(self) -> Dict[str, Any]:
        """
        从 settings.json 加载 MCP 服务器配置
        
        Returns:
            MCP 服务器配置字典
        """
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get("mcpServers", {})
        except Exception as e:
            # 如果读取失败，返回空字典
            pass
        return {}
    
    def get_available_mcp_servers(self) -> List[str]:
        """
        获取可用的 MCP 服务器名称列表
        
        Returns:
            MCP 服务器名称列表
        """
        return list(self._mcp_servers.keys())
    
    def _is_info_message(self, message: str) -> bool:
        """
        判断消息是否为信息性消息（而非错误）
        
        Args:
            message: 要检查的消息
        
        Returns:
            如果是信息性消息返回 True，否则返回 False
        """
        if not message:
            return False
        message_lower = message.lower()
        return any(keyword.lower() in message_lower for keyword in self.INFO_KEYWORDS)
    
    def _parse_stderr(self, stderr: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析 stderr 输出，区分错误和信息性消息
        
        Args:
            stderr: stderr 输出内容
        
        Returns:
            (error_message, info_logs) 元组
            - error_message: 真正的错误消息，如果没有错误则为 None
            - info_logs: 信息性日志，如果没有则为 None
        """
        if not stderr or not stderr.strip():
            return None, None
        
        lines = stderr.strip().split('\n')
        error_lines = []
        info_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 明确忽略 DeprecationWarning
            if "DeprecationWarning" in line:
                continue
            
            if self._is_info_message(line):
                info_lines.append(line)
            else:
                # 检查是否是真正的错误消息
                # 通常错误消息包含 "error", "failed", "exception" 等关键词
                error_indicators = ['error', 'failed', 'exception', 'fatal', 'cannot', "can't"]
                if any(indicator in line.lower() for indicator in error_indicators):
                    error_lines.append(line)
                else:
                    # 不确定的消息，默认当作信息性消息
                    info_lines.append(line)
        
        error_msg = '\n'.join(error_lines) if error_lines else None
        info_logs = '\n'.join(info_lines) if info_lines else None
        
        return error_msg, info_logs
    
    def _get_enhanced_env(self) -> Dict[str, str]:
        """
        获取增强的环境变量，确保包含必要的 PATH 路径
        
        Returns:
            增强后的环境变量字典
        """
        env = os.environ.copy()
        # 确保 PATH 包含必要的路径
        path_parts = env.get("PATH", "").split(os.pathsep)
        important_paths = [
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/Users/ChuanHuang/.orbstack/bin",  # Docker (OrbStack)
            os.path.expanduser("~/.orbstack/bin"),
        ]
        for path in important_paths:
            if path and os.path.exists(path) and path not in path_parts:
                path_parts.insert(0, path)
        env["PATH"] = os.pathsep.join(path_parts)
        return env
    
    def _find_gemini_cli(self) -> str:
        """尝试查找 gemini-cli 可执行文件"""
        # 常见的可能路径（按优先级排序）
        possible_paths = [
            # 直接使用绝对路径（最可靠）
            "/opt/homebrew/bin/gemini",  # Homebrew on Apple Silicon
            "/usr/local/bin/gemini",  # Homebrew on Intel Mac
            "/opt/homebrew/bin/gemini-cli",
            "/usr/local/bin/gemini-cli",
            # 相对路径（需要 PATH）
            "gemini-cli",
            "gemini",
            # 用户目录
            os.path.expanduser("~/.local/bin/gemini-cli"),
            os.path.expanduser("~/bin/gemini-cli"),
            os.path.expanduser("~/.local/bin/gemini"),
            os.path.expanduser("~/bin/gemini"),
        ]
        
        for path in possible_paths:
            try:
                if os.path.isabs(path):
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        return path
                else:
                    # 使用 which 查找命令
                    result = subprocess.run(
                        ["which", path],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        found_path = result.stdout.strip()
                        if found_path and os.access(found_path, os.X_OK):
                            return found_path
            except:
                continue
        
        # 默认返回 gemini-cli，让调用时再处理错误
        return "gemini-cli"
    
    def is_available(self) -> Dict[str, Any]:
        """
        检查 gemini-cli 是否可用（不执行实际命令）
        
        Returns:
            包含检查结果的字典
        """
        try:
            # 检查文件是否存在且可执行
            if os.path.isabs(self.cli_path):
                exists = os.path.exists(self.cli_path) and os.access(self.cli_path, os.X_OK)
            else:
                # 尝试查找命令
                result = subprocess.run(
                    ["which", self.cli_path],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                exists = result.returncode == 0
            
            return {
                "available": exists,
                "cli_path": self.cli_path,
                "message": "gemini-cli is available" if exists else f"gemini-cli not found at: {self.cli_path}"
            }
        except Exception as e:
            return {
                "available": False,
                "cli_path": self.cli_path,
                "message": f"Error checking gemini-cli: {str(e)}"
            }
    
    def chat(self, message: str, model: Optional[str] = None, 
             mcp_servers: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        发送消息到 gemini-cli 并获取响应
        
        Args:
            message: 要发送的消息
            model: 模型名称（可选）
            mcp_servers: 要使用的 MCP 服务器名称列表（可选，如果为 None 则使用所有配置的服务器）
            **kwargs: 其他参数
        
        Returns:
            包含响应结果的字典
        """
        try:
            # 构建命令
            cmd = [self.cli_path]
            
            # 添加模型参数（如果提供）
            if model:
                cmd.extend(["--model", model])
            
            # 添加 MCP 服务器参数
            if mcp_servers is not None:
                # 如果指定了 MCP 服务器，使用 --allowed-mcp-server-names
                for server_name in mcp_servers:
                    cmd.extend(["--allowed-mcp-server-names", server_name])
            # 如果没有指定，gemini 会自动使用 settings.json 中配置的所有服务器
            
            # 添加审批模式参数（如果提供）
            approval_mode = kwargs.pop("approval_mode", None)
            if approval_mode:
                cmd.extend(["--approval-mode", approval_mode])
            
            # 添加其他参数
            for key, value in kwargs.items():
                if value is not None:
                    # 跳过 mcp_servers，因为已经单独处理了
                    if key == "mcp_servers":
                        continue
                    cmd.extend([f"--{key.replace('_', '-')}", str(value)])
            
            # 执行命令并传递消息
            # 使用 run 而不是 Popen，这样更容易控制超时
            # 使用增强的环境变量，确保包含 Docker 等必要路径
            env = self._get_enhanced_env()
            
            process = subprocess.run(
                cmd,
                input=message,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd(),
                env=env,  # 使用增强的环境变量
                timeout=300
            )
            
            stdout = process.stdout
            stderr = process.stderr
            
            # 解析 stderr，区分错误和信息性消息
            error_msg, info_logs = self._parse_stderr(stderr)
            
            # 定义成功条件：返回码为0，或者返回码不为0但没有解析出真正的错误信息
            is_success = process.returncode == 0 or (process.returncode != 0 and not error_msg)

            # 如果最终判断为不成功，确保 error_msg 字段有内容
            if not is_success and not error_msg:
                error_msg = stderr.strip() if stderr else "Command failed with non-zero exit code and no specific error message."
            
            return {
                "success": is_success,
                "response": stdout.strip() if stdout else "",
                "error": error_msg,
                "logs": info_logs,  # 信息性日志
                "return_code": process.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "response": "",
                "error": "Command timeout after 300 seconds",
                "return_code": -1
            }
        except FileNotFoundError:
            return {
                "success": False,
                "response": "",
                "error": f"gemini-cli not found at: {self.cli_path}. Please ensure gemini-cli is installed and in your PATH.",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "response": "",
                "error": str(e),
                "return_code": -1
            }

    async def async_chat(self, message: str, model: Optional[str] = None, 
                  mcp_servers: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        异步发送消息到 gemini-cli 并获取响应
        """
        try:
            cmd = [self.cli_path]
            if model:
                cmd.extend(["--model", model])
            if mcp_servers is not None:
                for server_name in mcp_servers:
                    cmd.extend(["--allowed-mcp-server-names", server_name])
            
            approval_mode = kwargs.pop("approval_mode", None)
            if approval_mode:
                cmd.extend(["--approval-mode", approval_mode])
            
            for key, value in kwargs.items():
                if value is not None and key != "mcp_servers":
                    cmd.extend([f"--{key.replace('_', '-')}", str(value)])
            
            env = self._get_enhanced_env()
            
            # 使用 asyncio 创建异步子进程
            import asyncio
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=os.getcwd()
            )
            
            try:
                # 设置超时
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(input=message.encode()),
                    timeout=300
                )
            except asyncio.TimeoutExpired:
                process.kill()
                return {
                    "success": False,
                    "response": "",
                    "error": "Command timeout after 300 seconds",
                    "return_code": -1
                }

            stdout = stdout_data.decode()
            stderr = stderr_data.decode()
            return_code = process.returncode
            
            error_msg, info_logs = self._parse_stderr(stderr)
            is_success = return_code == 0 or (return_code != 0 and not error_msg)

            if not is_success and not error_msg:
                error_msg = stderr.strip() if stderr else "Command failed with non-zero exit code"
            
            return {
                "success": is_success,
                "response": stdout.strip() if stdout else "",
                "error": error_msg,
                "logs": info_logs,
                "return_code": return_code
            }
            
                except Exception as e:
                    return {
                        "success": False,
                        "response": "",
                        "error": str(e),
                        "return_code": -1
                    }
        
            async def async_chat_with_args(self, message: str, args: list) -> Dict[str, Any]:
                """
                使用自定义参数列表异步调用 gemini-cli
                """
                try:
                    cmd = [self.cli_path] + args
                    env = self._get_enhanced_env()
                    
                    import asyncio
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env,
                        cwd=os.getcwd()
                    )
                    
                    try:
                        stdout_data, stderr_data = await asyncio.wait_for(
                            process.communicate(input=message.encode()),
                            timeout=300
                        )
                    except asyncio.TimeoutExpired:
                        process.kill()
                        return {
                            "success": False,
                            "response": "",
                            "error": "Command timeout after 300 seconds",
                            "return_code": -1
                        }
        
                    stdout = stdout_data.decode()
                    stderr = stderr_data.decode()
                    return_code = process.returncode
                    
                    error_msg, info_logs = self._parse_stderr(stderr)
                    if return_code != 0 and not error_msg:
                        error_msg = stderr.strip() if stderr else "Command failed with non-zero exit code"
                    
                    return {
                        "success": return_code == 0,
                        "response": stdout.strip() if stdout else "",
                        "error": error_msg,
                        "logs": info_logs,
                        "return_code": return_code
                    }
                    
                except Exception as e:
                    return {
                        "success": False,
                        "response": "",
                        "error": str(e),
                        "return_code": -1
                    }
        
            def chat_with_args(self, message: str, args: list) -> Dict[str, Any]:        """
        使用自定义参数列表调用 gemini-cli
        
        Args:
            message: 要发送的消息
            args: 额外的命令行参数列表
        
        Returns:
            包含响应结果的字典
        """
        try:
            cmd = [self.cli_path] + args
            
            # 使用增强的环境变量，确保包含 Docker 等必要路径
            env = self._get_enhanced_env()
            
            process = subprocess.run(
                cmd,
                input=message,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd(),
                env=env,  # 使用增强的环境变量
                timeout=300
            )
            
            stdout = process.stdout
            stderr = process.stderr
            
            # 解析 stderr，区分错误和信息性消息
            error_msg, info_logs = self._parse_stderr(stderr)
            
            # 如果返回码不为0，即使没有明确的错误消息，也认为有错误
            if process.returncode != 0 and not error_msg:
                error_msg = stderr.strip() if stderr else "Command failed with non-zero exit code"
            
            return {
                "success": process.returncode == 0,
                "response": stdout.strip() if stdout else "",
                "error": error_msg,
                "logs": info_logs,  # 信息性日志
                "return_code": process.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "response": "",
                "error": "Command timeout after 300 seconds",
                "return_code": -1
            }
        except FileNotFoundError:
            return {
                "success": False,
                "response": "",
                "error": f"gemini-cli not found at: {self.cli_path}. Please ensure gemini-cli is installed and in your PATH.",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "response": "",
                "error": str(e),
                "return_code": -1
            }


# 全局客户端实例
gemini_client = GeminiCLIClient()

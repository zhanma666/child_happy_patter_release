"""
统一异常处理模块
符合项目规范：避免敏感错误信息直接暴露给客户端
"""

from typing import Dict, Any, Optional
import logging
import traceback
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class AudioProcessingError(Exception):
    """音频处理相关异常"""
    def __init__(self, message: str, error_code: str = "AUDIO_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class VoiceVerificationError(Exception):
    """声纹验证相关异常"""
    def __init__(self, message: str, error_code: str = "VOICE_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class STTError(Exception):
    """语音转文本异常"""
    def __init__(self, message: str, error_code: str = "STT_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class TTSError(Exception):
    """文本转语音异常"""
    def __init__(self, message: str, error_code: str = "TTS_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class SafeExceptionHandler:
    """安全的异常处理器 - 避免敏感信息泄露"""
    
    @staticmethod
    def get_safe_error_response(error: Exception, default_message: str = "服务暂时不可用") -> Dict[str, Any]:
        """
        获取安全的错误响应，避免敏感信息泄露
        
        Args:
            error: 原始异常
            default_message: 默认错误消息
            
        Returns:
            安全的错误响应字典
        """
        # 记录详细错误信息到日志
        logger.error(f"Exception occurred: {type(error).__name__}: {str(error)}")
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
        
        # 根据异常类型返回不同的安全消息
        if isinstance(error, AudioProcessingError):
            return {
                "success": False,
                "error_code": error.error_code,
                "message": "音频处理失败，请检查音频文件格式",
                "timestamp": None
            }
        elif isinstance(error, VoiceVerificationError):
            return {
                "success": False,
                "error_code": error.error_code,
                "message": "声纹验证失败，请重试",
                "timestamp": None
            }
        elif isinstance(error, STTError):
            return {
                "success": False,
                "error_code": error.error_code,
                "message": "语音识别失败，请重新录制或上传音频",
                "timestamp": None
            }
        elif isinstance(error, TTSError):
            return {
                "success": False,
                "error_code": error.error_code,
                "message": "语音合成失败，请稍后重试",
                "timestamp": None
            }
        elif isinstance(error, HTTPException):
            return {
                "success": False,
                "error_code": f"HTTP_{error.status_code}",
                "message": error.detail if isinstance(error.detail, str) else "请求处理失败",
                "timestamp": None
            }
        elif isinstance(error, ValueError):
            return {
                "success": False,
                "error_code": "INVALID_INPUT",
                "message": "输入参数无效，请检查输入格式",
                "timestamp": None
            }
        elif isinstance(error, FileNotFoundError):
            return {
                "success": False,
                "error_code": "FILE_NOT_FOUND",
                "message": "请求的资源不存在",
                "timestamp": None
            }
        elif isinstance(error, PermissionError):
            return {
                "success": False,
                "error_code": "PERMISSION_DENIED",
                "message": "权限不足，无法访问资源",
                "timestamp": None
            }
        else:
            # 对于未知异常，返回通用错误消息
            return {
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": default_message,
                "timestamp": None
            }


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """全局异常处理中间件"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # 使用安全异常处理器
            error_response = SafeExceptionHandler.get_safe_error_response(exc)
            
            # 根据异常类型确定HTTP状态码
            if isinstance(exc, HTTPException):
                status_code = exc.status_code
            elif isinstance(exc, (AudioProcessingError, VoiceVerificationError, STTError, TTSError)):
                status_code = 422  # Unprocessable Entity
            elif isinstance(exc, ValueError):
                status_code = 400  # Bad Request
            elif isinstance(exc, FileNotFoundError):
                status_code = 404  # Not Found
            elif isinstance(exc, PermissionError):
                status_code = 403  # Forbidden
            else:
                status_code = 500  # Internal Server Error
                
            return JSONResponse(
                status_code=status_code,
                content=error_response
            )


def setup_exception_handlers(app):
    """设置异常处理器"""
    app.add_middleware(GlobalExceptionMiddleware)
    
    logger.info("全局异常处理中间件已注册")
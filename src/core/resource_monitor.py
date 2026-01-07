"""
システムリソース監視モジュール
"""
import psutil
from typing import Dict


class ResourceMonitor:
    """システムリソース監視クラス"""
    
    def __init__(self, high_cpu_threshold: float = 80.0):
        """
        Args:
            high_cpu_threshold: 高負荷と判定するCPU使用率(%)
        """
        self.high_cpu_threshold = high_cpu_threshold
    
    def get_cpu_usage(self, interval: float = 1.0) -> float:
        """
        CPU使用率を取得
        
        Args:
            interval: 測定間隔(秒)
        
        Returns:
            CPU使用率(%)
        """
        return psutil.cpu_percent(interval=interval)
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        メモリ使用状況を取得
        
        Returns:
            メモリ情報の辞書
        """
        mem = psutil.virtual_memory()
        return {
            "total": mem.total / (1024 ** 3),  # GB
            "available": mem.available / (1024 ** 3),  # GB
            "used": mem.used / (1024 ** 3),  # GB
            "percent": mem.percent
        }
    
    def is_high_load(self) -> bool:
        """
        高負荷状態かどうかを判定
        
        Returns:
            True: 高負荷, False: 通常
        """
        cpu_usage = self.get_cpu_usage(interval=0.5)
        return cpu_usage > self.high_cpu_threshold
    
    def get_system_info(self) -> Dict[str, any]:
        """
        システム情報を取得
        
        Returns:
            システム情報の辞書
        """
        return {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": self.get_cpu_usage(interval=0.5),
            "memory": self.get_memory_usage(),
            "is_high_load": self.is_high_load()
        }

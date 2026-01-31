"""
跨平台文件锁模块
支持 Windows 和 Unix/Linux/macOS
"""

import os
import platform


class FileLock:
    """跨平台文件锁"""
    
    def __init__(self, lock_file: str):
        self.lock_file = lock_file
        self.fd = None
        self._lock = None
    
    def acquire(self) -> bool:
        """获取锁，返回是否成功"""
        try:
            if platform.system() == 'Windows':
                return self._acquire_windows()
            else:
                return self._acquire_unix()
        except Exception:
            return False
    
    def release(self):
        """释放锁"""
        try:
            if platform.system() == 'Windows':
                self._release_windows()
            else:
                self._release_unix()
        except Exception:
            pass
    
    def _acquire_windows(self) -> bool:
        """Windows 平台获取锁"""
        import msvcrt
        
        try:
            # 创建或打开锁文件
            self.fd = open(self.lock_file, 'w')
            
            # 尝试锁定文件的前 1 个字节
            msvcrt.locking(self.fd.fileno(), msvcrt.LK_NBLCK, 1)
            
            # 如果成功，重新锁定为独占锁
            msvcrt.locking(self.fd.fileno(), msvcrt.LK_UNLCK, 1)
            msvcrt.locking(self.fd.fileno(), msvcrt.LK_LOCK, 1)
            
            # 写入 PID
            self.fd.write(str(os.getpid()))
            self.fd.flush()
            
            return True
        except (IOError, OSError):
            if self.fd:
                self.fd.close()
                self.fd = None
            return False
    
    def _release_windows(self):
        """Windows 平台释放锁"""
        import msvcrt
        
        if self.fd:
            try:
                msvcrt.locking(self.fd.fileno(), msvcrt.LK_UNLCK, 1)
            except:
                pass
            self.fd.close()
            self.fd = None
    
    def _acquire_unix(self) -> bool:
        """Unix/Linux/macOS 平台获取锁"""
        import fcntl
        
        try:
            self.fd = open(self.lock_file, 'w')
            fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # 写入 PID
            self.fd.write(str(os.getpid()))
            self.fd.flush()
            
            return True
        except (IOError, OSError):
            if self.fd:
                self.fd.close()
                self.fd = None
            return False
    
    def _release_unix(self):
        """Unix/Linux/macOS 平台释放锁"""
        import fcntl
        
        if self.fd:
            try:
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
            except:
                pass
            self.fd.close()
            self.fd = None
    
    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Could not acquire lock: {self.lock_file}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


def acquire_lock(lock_file: str) -> bool:
    """
    获取文件锁的便捷函数
    
    Args:
        lock_file: 锁文件路径
        
    Returns:
        bool: 是否成功获取锁
    """
    lock = FileLock(lock_file)
    return lock.acquire()


def release_lock(lock_file: str):
    """
    释放文件锁的便捷函数（通过删除 PID 文件）
    
    注意：这只是一个标记，实际的锁释放需要通过 FileLock 对象
    """
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except:
        pass

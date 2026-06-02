#!/usr/bin/env python3
"""环境验证脚本 - 检查 Python 版本和依赖兼容性"""

import sys
import importlib
from typing import Dict, Tuple

def check_python_version() -> Tuple[bool, str]:
    """检查 Python 版本"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 12:
        return True, f"Python {version.major}.{version.minor}.{version.micro} ✓"
    else:
        return False, f"Python {version.major}.{version.minor}.{version.micro} (需要 3.12+)"

def check_dependency(name: str, min_version: str = None) -> Tuple[bool, str]:
    """检查单个依赖"""
    try:
        # 尝试从模块获取版本
        module = importlib.import_module(name)
        version = getattr(module, '__version__', None)
        if version:
            return True, f"{name} {version} ✓"
        # 如果模块没有 __version__，使用 importlib.metadata
        from importlib.metadata import version as get_version, PackageNotFoundError
        try:
            version = get_version(name)
            return True, f"{name} {version} ✓"
        except PackageNotFoundError:
            return True, f"{name} 已安装 ✓"
    except ImportError:
        return False, f"{name} 未安装 ✗"

def main():
    print("=" * 60)
    print("环境验证 - Offer Hunter LangChain Migration")
    print("=" * 60)

    results: Dict[str, Tuple[bool, str]] = {}

    # 检查 Python 版本
    ok, msg = check_python_version()
    results["Python"] = (ok, msg)

    # 检查核心依赖
    dependencies = [
        "langchain",
        "langgraph",
        "langchain_core",
        "langchain_openai",
        "langchain_anthropic",
        "langchain_chroma",
        "anthropic",
        "openai",
        "chromadb",
        "fastapi",
        "uvicorn",
        "pydantic",
        "httpx",
    ]

    for dep in dependencies:
        ok, msg = check_dependency(dep)
        results[dep] = (ok, msg)

    # 打印结果
    print("\n检查结果:")
    print("-" * 60)

    all_ok = True
    for name, (ok, msg) in results.items():
        status = "✓" if ok else "✗"
        print(f"  {status} {msg}")
        if not ok:
            all_ok = False

    print("-" * 60)

    if all_ok:
        print("\n✓ 所有依赖检查通过！环境准备就绪。")
        return 0
    else:
        print("\n✗ 部分依赖检查失败，请安装缺失的依赖。")
        print("\n建议运行:")
        print("  pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())

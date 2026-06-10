# Project Overview

这是一个 以vn.py 为基础 的交易系统。

* 简单稳定
* 不做过度抽象
* 不要新增 abstraction 
* 不要为了未来需求设计 
* 优先直接实现

# Tech Stack


# Directory Structure

gateway/      行情网关
strategy/     策略
engine/       核心引擎
tests/        测试

# Coding Rules

* 优先简单实现
* 不允许新增 wrapper
* 不允许兼容旧逻辑
* 不允许无意义抽象
* 不允许 silent catch


# Python Rules

* Python 版本固定 3.12
* 使用 pathlib

# Build

make -j8

# Test

pytest tests/

# Git Workflow

修改前：

1. 先分析
2. 给 implementation plan
3. 不要直接改代码

修改后：

1. 跑测试
2. 输出 root cause
3. 总结影响范围

# Forbidden

禁止：

* 大规模重构
* 修改 public API
* 自动删文件
* 修改数据库 schema

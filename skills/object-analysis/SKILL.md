---
name: object-analysis
description: 用于安防物品研判、图片识别、现场抓拍分析和多模态场景理解。适用于用户提供图片或提出识图、研判、抓拍分析需求的问题。
triggers:
  - 图片
  - 图像
  - 照片
  - 抓拍
  - 识别
  - 研判
  - 物品
  - 识图
  - 多模态
---

# 安防物品研判 Skill

## 能力边界

用于识别图片中的安防相关对象、场景和风险，并输出可执行的研判结论。

## 可用工具

- `analyze_security_object`：调用多模态大模型完成图片识别与物品研判。
- `search_security_knowledge`：必要时补充本地 SOP 或规范依据。

## 使用方式

1. 主 Agent 先识别是否为图片识别 / 物品研判意图。
2. 命中后委派 `object-analyst` 子 Agent。
3. 子 Agent 调用 `analyze_security_object`，传入图片路径、URL 或 base64。
4. 输出按“场景概述、识别对象、风险判断、建议动作”组织。

## 输入要求

- 必须提供以下任一图片输入：`image_path`、`image_url`、`image_base64`。
- `image_path` 只能指向 `data/workspace/` 内文件。

## 适用问题

- 请识别这张抓拍图里是否有异常物品？
- 帮我研判现场照片中的人员和车辆情况。
- 这张门禁图片里是否存在安全风险？

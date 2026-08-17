---
name: install-vision-skill
description: Install and configure the claude-code-vision-skill (xiincs/claude-code-vision-skill) on a new machine, wire it to an Aliyun MaaS / DashScope / OpenAI-compatible vision workspace, and enable image input (input_modalities ["text", "image"]) for CC Switch. Use when the user asks to install a vision skill, configure a vision API (API Key / API Host / OpenAI compatible address / DashScope), set up 视觉 skill / 视觉模型 on this or another computer, or enable image modality.
---

# Install Vision Skill

把 claude-code-vision-skill 装到新电脑并接入阿里云 MaaS 视觉端点，一步完成
Codex 与 Claude Code 两侧的安装、环境变量配置、CLAUDE.md 合并和 CC Switch
图像输入开启。

## 收集输入（不要写入本 skill）

运行前向用户索取，或从环境变量读取：

| 输入 | 环境变量 |
|------|----------|
| API Key（`sk-...`） | `VISION_SETUP_API_KEY` |
| OpenAI 兼容地址（形如 `https://<host>.maas.aliyuncs.com/compatible-mode/v1`） | `VISION_SETUP_BASE_URL` |
| 模型（可选，默认 `qwen-vl-max`） | — |

必须使用 OpenAI 兼容地址（`/compatible-mode/v1`），不要用 DashScope 原生
`/api/v1`：本 skill 的 qwen provider 走 OpenAI chat-completions 协议，
`/api/v1` 不响应该协议（已验证）。

## 安装

```bash
python scripts/install_vision_skill.py --api-key "<KEY>" --base-url "<BASE_URL>" [--model qwen-vl-max]
```

脚本自动完成：

1. 从 `xiincs/claude-code-vision-skill`（main 分支 zip，用 Python urllib 下载，
   规避 Windows git/curl 的 schannel 凭据问题）解压 vision 文件。
2. 安装到 `~/.codex/skills/vision`（Codex 侧）和 `~/.claude/skills/vision`
   （Claude Code 侧）。
3. 写 `~/.claude/settings.json`：`DASHSCOPE_API_KEY`、
   `DASHSCOPE_BASE_URL`、`QWEN_MODEL`、`OPENAI_API_KEY`、
   `OPENAI_BASE_URL`、`OPENAI_MODEL`、`VISION_PROVIDER=qwen`，并注册
   SessionStart 路由 hook（幂等去重）。
4. 合并 `~/.claude/CLAUDE.md`：模板自身已含标记时不再重复包裹（修复上游
   install.py 的双标记 bug）。
5. 若存在 `~/.codex/cc-switch-model-catalog.json`，把
   `"input_modalities": ["text"]` 改为 `["text", "image"]`；不存在则跳过并提示。

修改前会为已存在的文件生成 `.bak` 备份。可用 `--dry-run` 预览，不写任何文件；
也可用 `--codex-skills-dir` / `--claude-home` / `--cc-switch-catalog` 指定目标路径
（用于迁移演练）。

## 验证

```bash
python ~/.claude/skills/vision/vision.py --help
```

若缺依赖（`openai>=1.0.0`、`anthropic>=0.40.0`），安装仓库的 requirements：

```bash
python -m pip install -r <repo>/requirements.txt
```

然后用一张测试图片做端到端调用（路由为 `external` 时才会真正调用模型；
可先设 `VISION_ROUTING=external` 强制走外部视觉）：

```bash
VISION_ROUTING=external python ~/.claude/skills/vision/vision.py test.png "describe this image"
```

## 注意

- API Key 只存在于 `~/.claude/settings.json` 等用户配置中，不要写进本 skill。
- Claude Code 侧 hook 使用 PATH 里的 `python`；若目标机器缺 Python 依赖，
  在真实终端（非沙箱）里执行 `pip install -r requirements.txt`。
- 安装完成后，Codex 侧 vision skill 在下一次会话生效。

# install-vision-skill

一个可复用的 Codex skill：在新电脑上自动完成
[claude-code-vision-skill](https://github.com/xiincs/claude-code-vision-skill)
的安装与阿里云 MaaS（DashScope / OpenAI 兼容）视觉端点配置，并开启 CC Switch
的图像输入（`input_modalities: ["text", "image"]`）。

## 安装

把 `install-vision-skill/` 整个文件夹复制到 `~/.codex/skills/` 下，重新打开
Codex 后即可用。也可以用 skill-installer 直接安装：

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo <owner>/install-vision-skill \
  --path install-vision-skill
```

## 使用

对 Codex 说"用 install-vision-skill 安装配置视觉技能"，然后提供 API Key 和
OpenAI 兼容地址（形如 `https://<host>.maas.aliyuncs.com/compatible-mode/v1`）。

也可以手动运行脚本：

```bash
python install-vision-skill/scripts/install_vision_skill.py \
  --api-key "<KEY>" \
  --base-url "https://<host>.maas.aliyuncs.com/compatible-mode/v1"
```

密钥可用环境变量 `VISION_SETUP_API_KEY` / `VISION_SETUP_BASE_URL` 传入，
不要写入 skill 文件。

## 脚本功能

- 下载并安装 vision skill 到 `~/.codex/skills/vision` 和 `~/.claude/skills/vision`
- 写 `~/.claude/settings.json`（DASHSCOPE / OPENAI 的 key、base URL、模型、
  `VISION_PROVIDER=qwen`）+ SessionStart 路由 hook
- 合并 `~/.claude/CLAUDE.md`（已修复上游 install.py 的双标记 bug）
- 把 `~/.codex/cc-switch-model-catalog.json` 的 `input_modalities` 从
  `["text"]` 改为 `["text", "image"]`
- 修改前自动备份 `.bak`；支持 `--dry-run` 预览

## 注意

- 必须使用 OpenAI 兼容地址（`/compatible-mode/v1`），不要用 DashScope 原生
  `/api/v1`。
- 缺依赖时执行：`pip install 'openai>=1.0.0' 'anthropic>=0.40.0'`

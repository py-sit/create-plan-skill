# create-plan-skill 2.0.0

面向 Codex 的正式方案与 PDF 交付插件。它把复杂任务拆成四个可独立验收的阶段：

- 需求澄清：`$clarify-plan-requirements`
- 方案调研：`$research-plan-options`
- 正式方案与 PDF：`$author-formal-plan`
- 独立验收：`$validate-plan-package`

统一入口为 `$create-plan-skill`。

## V2.0 主要能力

- Codex Plugin manifest 与五个独立 Skill
- `plan-manifest.yaml` 与 `source-register.yaml`
- HTML/CSS + Playwright/Chromium 正式 PDF 引擎
- 三套主题和中英文 PDF
- ReportLab V1.1 兼容引擎
- Mermaid PNG/SVG/PDF 交付约束
- 40 个 V2 Eval、路由质量门禁和中英文视觉基线
- V1.1 workspace 无损迁移、隐私扫描和确定性 Release 包

## 安装

从 GitHub Release 下载 `create-plan-skill-2.0.0.zip` 并解压，然后在解压目录执行：

```bash
python3 -m pip install -r scripts/requirements-v2.txt
python3 -m playwright install chromium
python3 scripts/install_skills.py --apply
```

如果已安装 V1.1，先 dry-run，再执行带备份的升级：

```bash
python3 scripts/install_skills.py --json
python3 scripts/install_skills.py --apply --upgrade
```

安装器会先备份已有 Skill，再复制 V2 的五个 Skill。安装完成后请新建一个 Codex 任务，使新的 Skill 元数据重新加载。

## 快速使用

初始化工作区：

```bash
python3 scripts/init_plan_workspace.py \
  --output-dir ./plan-workspace \
  --title "方案名称" \
  --language zh-CN
```

生成正式 PDF：

```bash
python3 scripts/render_plan_pdf.py \
  ./plan-workspace/proposal.md \
  --output ./plan-workspace/output/pdf/formal-plan.pdf \
  --engine playwright
```

验收：

```bash
python3 scripts/validate_plan_package.py \
  --mode full-proposal \
  --workspace ./plan-workspace
```

V1.1 workspace 升级：

```bash
python3 scripts/migrate_v11_workspace.py ./legacy-workspace
python3 scripts/migrate_v11_workspace.py ./legacy-workspace --apply
```

## 兼容边界

- 仓库根目录保留 V1.1 standalone Skill 和原 CLI。
- V2 Plugin 使用 `skills/` 下的路由与专项 Skill。
- V1.1 默认 ReportLab 行为不变；V2 正式流程显式使用 Playwright。
- 不会自动实施方案、部署系统或修改生产数据。

License: MIT

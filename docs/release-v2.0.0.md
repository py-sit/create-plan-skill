# create-plan-skill V2.0.0

## Alpha

- 建立 `.codex-plugin/plugin.json`。
- 拆分统一路由 Skill 与需求澄清、方案调研、正式编写、独立验收四个专项 Skill。
- 引入 `plan-manifest.yaml`、`source-register.yaml` 和对应 schema。
- 保留 V1.1 根 Skill、CLI 与 workspace 兼容层。

## Beta

- 增加 HTML/CSS + Playwright/Chromium 正式 PDF 引擎。
- 保留 ReportLab 为显式兼容引擎。
- 增加 `corporate-blue`、`executive-slate`、`minimal-mono` 三套主题。
- 将来源日期、版本、许可证和证据 ID 写入参考资料附录。
- 阻断渲染阶段的外部网络资源请求，不把本地路径写成 `file://` 链接。

## RC

- 增加 Python 3.9、3.11、3.13 GitHub Actions。
- V2 Eval 扩展到 40 条，中英文、四种模式和非触发边界全部覆盖。
- 路由 precision、recall、mode accuracy 和 skill accuracy 门槛为 95%。
- 增加 V1.1 workspace 无损迁移工具。
- 增加敏感内容扫描和中英文视觉基线。

## GA

- 增加确定性 Plugin ZIP、SHA256、独立包校验和安全升级安装器。
- 完成 V1.1 与 V2 全量回归、官方 Plugin/Skill 校验、包内隐私扫描和安装升级验收。
- 发布公开仓库 main、`v2.0.0` Tag 和 GitHub Release。

## 升级说明

V1.1 workspace 默认只做 dry-run，只有明确使用 `--apply` 才新增 V2 metadata 文件。迁移不会改写已有 Markdown、图表或 PDF。

V1.1 Skill 升级使用 `install_skills.py --apply --upgrade`。安装器会把已有 Skill 复制到 `.create-plan-backups` 后再安装 V2。

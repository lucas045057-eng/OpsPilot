# OpsPilot 项目说明 / Project Brief

## 中文项目说明

OpsPilot 是一个小型企业级 SRE 运维平台 Demo，覆盖“服务运行—监控—告警—自动修复—事故复盘”的完整闭环。

核心能力：

- 使用 FastAPI 采集服务状态和主机 CPU、内存、磁盘、网络指标；
- 通过 Prometheus 暴露指标，使用 Grafana 展示服务可用性与系统趋势；
- 通过 Alertmanager webhook 接收 firing/resolved 事件，并写入 SQLite 事故时间线；
- 通过白名单 Runbook 和冷却时间控制自动重启，避免任意 Shell 执行和重启风暴；
- 提供模拟运行时和 Docker 运行时，支持本地面试演示以及 Docker Compose 部署；
- 记录检测时间、恢复时间、处理动作和 MTTR，生成事故报告；
- 通过故障注入脚本和 GitHub Actions 验证核心链路。

### 中文简历短版

**OpsPilot - Docker 服务可观测与自动修复平台** | Python、FastAPI、Docker、Prometheus、Grafana、Alertmanager、SQLite、GitHub Actions

- 独立设计并实现服务监控、P1 告警、SQLite 事故时间线、白名单 Runbook 自动重启和 MTTR 报告闭环。
- 使用 FastAPI/psutil 采集主机与服务指标，通过 Prometheus/Grafana 展示可用性趋势，并接入 Alertmanager webhook。
- 提供模拟运行时、Docker Compose 编排和故障注入脚本，验证“停止服务→告警→自动修复→恢复确认”的端到端流程。

### DevOps/SRE 定向版

- 设计 Monitor、Alert、Runbook、Repair 四阶段故障处理链路，加入 action cooldown 与 allowlist，降低误操作和重启风暴风险。
- 使用 Docker SDK 读取容器状态，配合 Prometheus/Grafana/Alertmanager 构建基础可观测性栈。

### Python/测试开发定向版

- 将监控、告警和修复逻辑拆分为可测试模块，覆盖健康采集、故障注入、自动恢复、人工处理和指标输出场景。
- 使用 SQLite 持久化 incident 状态，生成可查询的恢复时长和动作结果。

## English Project Description

OpsPilot is a small enterprise-style SRE platform demo covering the full service lifecycle: runtime health, monitoring, alerting, automated remediation, and post-incident review.

Key capabilities:

- Collects service status and host CPU, memory, disk, and network metrics with FastAPI and psutil.
- Exposes Prometheus metrics and provides a Grafana dashboard for availability and system trends.
- Receives Alertmanager firing/resolved webhooks and persists the incident timeline in SQLite.
- Uses allowlisted runbooks and action cooldowns for safe automated restarts, avoiding arbitrary shell execution and restart storms.
- Supports both a deterministic simulated runtime and a Docker runtime for local demos and Compose deployments.
- Records detection/recovery timestamps, actions, and MTTR, then generates incident reports.
- Validates the complete loop with fault injection scripts, unit tests, and GitHub Actions.

### English resume version

**OpsPilot - Docker Service Observability and Automated Self-Healing Platform** | Python, FastAPI, Docker, Prometheus, Grafana, Alertmanager, SQLite, GitHub Actions

- Built an end-to-end SRE workflow covering service monitoring, P1 alerting, SQLite incident timelines, allowlisted runbook restarts, and MTTR reports.
- Collected host and service metrics with FastAPI/psutil, exposed Prometheus metrics, provisioned Grafana dashboards, and integrated Alertmanager webhooks.
- Added simulated and Docker runtimes, Compose orchestration, fault injection, and CI checks to validate the stop → alert → repair → recovery flow.

### DevOps/SRE version

- Designed a four-stage Monitor → Alert → Runbook → Repair workflow with an action allowlist and cooldown control to reduce unsafe operations and restart storms.
- Used the Docker SDK plus Prometheus/Grafana/Alertmanager to build a practical observability stack.

### Python/testing version

- Split monitoring, alerting, and repair into testable modules covering healthy collection, fault injection, automated recovery, manual review, and metric output.
- Persisted incident state in SQLite and generated queryable recovery duration and action results.

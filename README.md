# OpsPilot

Docker Service Observability and Automated Self-Healing Platform

English version: [README.en.md](README.en.md) · Resume/project brief: [docs/PROJECT_BRIEF_BILINGUAL.md](docs/PROJECT_BRIEF_BILINGUAL.md)

OpsPilot 是一个可运行的 SRE 运维平台 Demo：它持续检查主机和服务状态，把异常写入事故时间线，按白名单执行安全的自动修复，并通过 Prometheus/Grafana 提供指标和大屏。项目与 AgentOps 形成互补：AgentOps 管理“任务如何执行”，OpsPilot 管理“服务运行后如何被观测、恢复和复盘”。

## 你可以演示什么

1. 打开 `http://localhost:8000`，查看服务状态、CPU/内存/磁盘和事故记录。
2. 点击某个服务的“模拟故障”，或运行 `python scripts/fault_injection.py nginx`。
3. Monitor 发现服务停止，创建 P1 Incident。
4. Repair Engine 按 `container_down` Runbook 执行白名单动作 `restart`。
5. 服务恢复后，事故被标记为 `resolved`，并记录检测时间、恢复时间、动作和持续时间。
6. 打开 `http://localhost:3000` 查看 Grafana 大屏；Prometheus 地址为 `http://localhost:9090`，Alertmanager 地址为 `http://localhost:9093`。

## 架构

```text
Docker containers / host
          |
          v
  OpsPilot Monitor (FastAPI + Python)
       |             |
       v             v
  SQLite incidents  /metrics
       |             |
       v             v
  Repair Engine   Prometheus -> Grafana
       |
       v
  Docker API (restart / inspect)
```

## 快速开始：本地无 Docker 模式

这个模式不需要 Docker Desktop，适合先开发和面试演示。程序会使用模拟运行时，但完整保留监控、告警、事故记录、自愈和 Prometheus 指标链路。

```powershell
cd work/OpsPilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:RUNTIME_MODE="simulated"
uvicorn app.main:app --reload --port 8000
```

打开 `http://localhost:8000`，点击“模拟故障”。也可以执行：

```powershell
python scripts/fault_injection.py nginx
```

## Docker + Grafana 模式

安装 Docker Desktop 后，在项目目录执行：

```bash
docker compose up -d --build
```

访问：

| 地址 | 用途 |
|---|---|
| `http://localhost:8000` | OpsPilot 控制台 |
| `http://localhost:3000` | Grafana，账号 `admin`，密码 `opspilot` |
| `http://localhost:9090` | Prometheus |
| `http://localhost:9093` | Alertmanager |

Docker 模式通过 `/var/run/docker.sock` 读取并重启 `nginx`、`redis`、`api-service`。如果你不希望授予 Docker Socket 权限，可以保持本地模拟模式。

## 关键 API

```text
GET  /health
GET  /api/services
GET  /api/alerts
GET  /api/stats
GET  /api/metrics
GET  /metrics
POST /api/monitor/tick
POST /api/alerts/webhook
POST /api/services/{name}/stop
POST /api/services/{name}/restart
GET  /api/incidents/{id}/report
```

## 测试与 CI

```bash
pytest -q
```

GitHub Actions 会执行 pytest，并构建 Docker 镜像。测试覆盖：

- 正常服务采集；
- 故障注入、P1 告警、自动重启和事故恢复；
- Prometheus 指标输出；
- 关闭自动修复后的人工处理状态。

## 面试讲法

> 我把 AgentOps 和 OpsPilot 拆成两个层次：AgentOps 解决任务执行生命周期，OpsPilot 解决服务运行生命周期。OpsPilot 通过 Python/FastAPI 采集主机和容器状态，用 Prometheus/Grafana 做可观测性，用 SQLite 保存事故时间线，再通过白名单 Runbook 自动重启故障服务，并用故障注入验证了检测、恢复和复盘链路。

## 已实现与后续增强

- 已接入 Prometheus Alertmanager webhook，支持 firing/resolved 事件写入事故时间线；
- 已提供本地模拟运行时，Docker Desktop 可用时自动切换到 Docker API；
- 后续可加入真实 HTTP health check、TCP 探活，以及 k3d/Minikube Deployment/Service；
- 后续可加入 Runbook 检索和人工确认式 LLM 建议，但禁止模型直接执行任意 Shell。

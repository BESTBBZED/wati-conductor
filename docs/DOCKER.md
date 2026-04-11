# Docker 部署指南

## 快速启动

```bash
# 1. 启动容器（自动构建）
./docker-start.sh

# 2. 进入容器
docker-compose exec wati-conductor bash

# 3. 运行命令
python -m conductor.cli "Find all VIP contacts"
```

## 手动步骤

### 1. 构建镜像

```bash
docker-compose build
```

### 2. 启动容器

```bash
docker-compose up -d
```

### 3. 使用方式

#### 方式 A: 进入容器交互式使用

```bash
# 进入容器
docker-compose exec wati-conductor bash

# 在容器内运行
python -m conductor.cli "Find all VIP contacts"
python -m conductor.cli "Send renewal_reminder to VIP contacts" --dry-run
./demo.sh
```

#### 方式 B: 从外部直接运行

```bash
# 单次命令
docker-compose exec wati-conductor python -m conductor.cli "Find all VIP contacts"

# 带参数
docker-compose exec wati-conductor python -m conductor.cli "Send template to VIPs" --dry-run --verbose

# 运行 demo
docker-compose exec wati-conductor ./demo.sh
```

### 4. 停止容器

```bash
docker-compose down
```

## 环境配置

编辑 `.env` 文件：

```bash
# 必需
DEEPSEEK_API_KEY=sk-your-key-here

# 可选
LLM_PARSE_MODEL=deepseek-chat
USE_MOCK=true
LOG_LEVEL=INFO
```

## 开发模式

代码挂载为 volume，修改本地代码会立即生效：

```bash
# 修改代码
vim conductor/agent/parser.py

# 在容器内测试（无需重启）
docker-compose exec wati-conductor python -m conductor.cli "test"
```

## 查看日志

```bash
# 实时日志
docker-compose logs -f

# 查看最近日志
docker-compose logs --tail=100
```

## 故障排查

### 容器无法启动

```bash
# 查看日志
docker-compose logs

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

### API Key 未生效

```bash
# 检查环境变量
docker-compose exec wati-conductor env | grep API_KEY

# 重启容器
docker-compose restart
```

### 代码修改未生效

```bash
# 检查 volume 挂载
docker-compose exec wati-conductor ls -la /app/conductor

# 如果需要，重新构建
docker-compose down
docker-compose build
docker-compose up -d
```

## 生产部署

### 使用真实 WATI API

编辑 `.env`:

```bash
USE_MOCK=false
WATI_TENANT_ID=your-tenant-id
WATI_TOKEN=your-api-token
```

### 后台运行

```bash
# 启动
docker-compose up -d

# 运行命令
docker-compose exec wati-conductor python -m conductor.cli "your instruction"
```

## Docker Compose 配置说明

```yaml
services:
  wati-conductor:
    build: .                    # 从当前目录构建
    container_name: wati-conductor
    environment:                # 环境变量从 .env 读取
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:                    # 代码挂载（开发模式）
      - ./conductor:/app/conductor
      - ./tests:/app/tests
    stdin_open: true           # 支持交互式
    tty: true
    command: /bin/bash         # 默认启动 bash
```

## 常用命令速查

```bash
# 构建
docker-compose build

# 启动
docker-compose up -d

# 进入容器
docker-compose exec wati-conductor bash

# 运行命令
docker-compose exec wati-conductor python -m conductor.cli "instruction"

# 查看日志
docker-compose logs -f

# 停止
docker-compose down

# 重启
docker-compose restart

# 清理
docker-compose down -v
```

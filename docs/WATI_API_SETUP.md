# 切换到真实 WATI API

## 1. 获取 WATI 凭证

从 WATI 控制台获取：
- **API Endpoint**: 你的 WATI 服务器地址（例如：`https://live-server-123.wati.io`）
- **API Token**: 你的 API 访问令牌

## 2. 配置环境变量

编辑 `.env` 文件：

```bash
# 关闭 Mock 模式
USE_MOCK=false

# WATI API 配置
WATI_API_ENDPOINT=https://live-server-123.wati.io
WATI_TOKEN=your_actual_api_token_here

# 其他配置保持不变
DEEPSEEK_API_KEY=your_key
TICKET_REPORTER=Zachary
```

## 3. 重启容器

```bash
docker compose down
docker compose up -d
```

## 4. 测试连接

```bash
docker compose exec wati-conductor python -m conductor.cli "List my templates" --trust
```

## 支持的 WATI API

### 已实现的端点：

| 功能 | API 端点 | 方法 |
|------|---------|------|
| 发送模板消息 | `/api/v1/sendTemplateMessage` | POST |
| 发送会话消息 | `/api/v1/sendSessionMessage/{phone}` | POST |
| 获取联系人列表 | `/api/v1/getContacts` | GET |
| 获取联系人详情 | `/api/v1/getContact/{phone}` | GET |
| 添加标签 | `/api/v1/addTag` | POST |
| 更新联系人属性 | `/api/v1/updateContactAttributes/{phone}` | PUT |
| 获取消息模板 | `/api/v1/getMessageTemplates` | GET |
| 分配操作员 | `/api/v1/assignOperator` | POST |

### 本地功能（不使用 WATI API）：

- **Ticket 管理**: 存储在本地 `./mock_data/tickets.json`
- **对话历史**: 存储在本地 `./history/current_session.json`

## 注意事项

1. **Ticket 系统是本地的**：即使使用真实 WATI API，ticket 管理仍然存储在本地文件中
2. **速率限制**：WATI API 有速率限制，注意不要频繁调用
3. **错误处理**：真实 API 可能返回各种错误，建议先在 sandbox 环境测试

## 切换回 Mock 模式

如果需要切换回 Mock 模式进行测试：

```bash
# .env
USE_MOCK=true
```

然后重启容器。

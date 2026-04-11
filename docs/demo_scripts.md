# WATI Conductor - Demo Scripts

演示脚本设计文档，用于展示 WATI Conductor 的核心功能和用户体验。

---

## 🎯 设计思路

### **DEMO 目标**
- 展示 Agent 能理解自然语言
- 展示 Agent 能生成正确的 API 调用计划
- 展示 Agent 能处理错误和边界情况
- 展示 CLI 的用户体验（Rich 格式化）

### **核心功能覆盖**
- ✅ 自然语言理解（Parse）
- ✅ 计划生成（Plan）
- ✅ 验证和澄清（Validate + Clarify）
- ✅ 执行和错误处理（Execute）
- ✅ Dry-run 模式

### **场景选择原则**
- **简单 → 复杂**：从单步操作到多步编排
- **成功 → 失败**：展示正常流程和错误处理
- **查询 → 修改**：从只读操作到写入操作

---

## 📋 Demo 脚本

### **脚本 1: 简单查询（热身）**

**目标**：展示基础的 NLU 和 API 调用

```bash
# 场景：查询 VIP 客户
conductor run "找出所有 VIP 客户"
```

**预期输出：**
```
Instruction: 找出所有 VIP 客户

Execution Plan (execute mode)
┌──────┬─────────────────┬──────────────────────────┐
│ Step │ Action          │ Description              │
├──────┼─────────────────┼──────────────────────────┤
│ 1    │ search_contacts │ 搜索标签为 'VIP' 的联系人 │
└──────┴─────────────────┴──────────────────────────┘

Executing...
✓ 搜索标签为 'VIP' 的联系人 (15 found)

Summary: 找到 15 个 VIP 客户
```

**为什么选这个？**
- ✅ 最简单的场景，只有 1 个 API 调用
- ✅ 展示 Agent 能理解中文
- ✅ 展示 Rich CLI 的表格输出
- ✅ 非破坏性操作，安全

---

### **脚本 2: 多步编排（核心能力）**

**目标**：展示 Agent 能生成多步骤计划

```bash
# 场景：给 VIP 客户发送续费提醒
conductor run "给所有 VIP 客户发送 renewal_reminder 模板，填入他们的名字"
```

**预期输出：**
```
Instruction: 给所有 VIP 客户发送 renewal_reminder 模板，填入他们的名字

Execution Plan (execute mode)
┌──────┬──────────────────────────┬────────────────────────────────────┐
│ Step │ Action                   │ Description                        │
├──────┼──────────────────────────┼────────────────────────────────────┤
│ 1    │ search_contacts          │ 搜索标签为 'VIP' 的联系人           │
│ 2    │ get_template_details     │ 获取 'renewal_reminder' 模板信息   │
│ 3    │ send_template_message_batch │ 批量发送模板消息（填入姓名参数） │
└──────┴──────────────────────────┴────────────────────────────────────┘

⚠ This will send messages to ~15 contacts. Proceed? (y/n): y

Executing...
✓ 搜索标签为 'VIP' 的联系人 (15 found)
✓ 获取 'renewal_reminder' 模板信息
✓ 批量发送模板消息 (14 sent, 1 failed)

Summary: 
  ✓ 14 messages sent successfully
  ✗ 1 failed (contact_10: invalid phone number format)
```

**为什么选这个？**
- ✅ 展示多步骤编排（3 步）
- ✅ 展示依赖关系（步骤 3 依赖步骤 1 和 2）
- ✅ 展示人工确认（批量操作需要确认）
- ✅ 展示部分失败处理（14 成功，1 失败）
- ✅ 这是 WATI 的核心使用场景

---

### **脚本 3: Dry-run 模式（安全预览）**

**目标**：展示 Dry-run 功能，用户可以预览而不执行

```bash
# 场景：预览批量操作
conductor run "给所有雅加达的客户发送 flash_sale 模板" --dry-run
```

**预期输出：**
```
Instruction: 给所有雅加达的客户发送 flash_sale 模板

Execution Plan (dry-run mode)
┌──────┬──────────────────────────┬────────────────────────────────────┐
│ Step │ Action                   │ Description                        │
├──────┼──────────────────────────┼────────────────────────────────────┤
│ 1    │ search_contacts          │ 搜索属性 city='Jakarta' 的联系人   │
│ 2    │ get_template_details     │ 获取 'flash_sale' 模板信息         │
│ 3    │ send_template_message_batch │ 批量发送模板消息                │
└──────┴──────────────────────────┴────────────────────────────────────┘

Estimated impact:
  - ~50 contacts will receive the message
  - Estimated cost: $0.05 (50 messages × $0.001)
  - API calls: 3 requests

Dry-run mode: no actions executed
```

**为什么选这个？**
- ✅ 展示 Dry-run 模式（产品思维）
- ✅ 展示成本估算（实用功能）
- ✅ 展示影响范围预览（安全性）
- ✅ 不实际执行，适合演示

---

### **脚本 4: 错误处理和澄清（智能交互）**

**目标**：展示 Agent 能处理模糊输入并主动澄清

```bash
# 场景：模糊的指令
conductor run "给 VIP 客户发消息"
```

**预期输出：**
```
Instruction: 给 VIP 客户发消息

⚠ Need clarification:

I need more details:
1. Which message should I send?
   - Session message (free text)?
   - Template message (which template)?

2. Available templates:
   - renewal_reminder (续费提醒)
   - flash_sale (限时促销)
   - vip_exclusive (VIP 专属)

Please clarify your instruction.
```

**为什么选这个？**
- ✅ 展示 Agent 的智能（不会盲目执行）
- ✅ 展示澄清机制（Clarify 节点）
- ✅ 展示用户友好的错误提示
- ✅ 真实场景（用户输入常常不完整）

---

### **脚本 5: 错误恢复（健壮性）**

**目标**：展示 Agent 能处理 API 错误并给出建议

```bash
# 场景：使用不存在的模板
conductor run "给 VIP 客户发送 welcome_new 模板"
```

**预期输出：**
```
Instruction: 给 VIP 客户发送 welcome_new 模板

Execution Plan (execute mode)
┌──────┬─────────────────┬──────────────────────────┐
│ Step │ Action          │ Description              │
├──────┼─────────────────┼──────────────────────────┤
│ 1    │ search_contacts │ 搜索标签为 'VIP' 的联系人 │
│ 2    │ get_template_details │ 获取 'welcome_new' 模板信息 │
└──────┴─────────────────┴──────────────────────────┘

Executing...
✓ 搜索标签为 'VIP' 的联系人 (15 found)
✗ 获取 'welcome_new' 模板信息 (Template not found)

Error: Template 'welcome_new' does not exist.

Available templates:
  - renewal_reminder (续费提醒)
  - flash_sale (限时促销)
  - vip_exclusive (VIP 专属)

Suggestion: Did you mean 'renewal_reminder'?
```

**为什么选这个？**
- ✅ 展示错误处理（不会崩溃）
- ✅ 展示有用的错误信息（列出可用模板）
- ✅ 展示智能建议（"Did you mean..."）
- ✅ 真实场景（用户会输错名字）

---

### **脚本 6: 复杂编排（高级能力）**

**目标**：展示 Agent 能处理复杂的多步骤工作流

```bash
# 场景：升级工单并通知
conductor run "把 6281234567890 的对话分配给 Support 团队，添加 'escalated' 标签，然后发消息告诉他我们正在处理"
```

**预期输出：**
```
Instruction: 把 6281234567890 的对话分配给 Support 团队，添加 'escalated' 标签，然后发消息告诉他我们正在处理

Execution Plan (execute mode)
┌──────┬─────────────────────┬────────────────────────────────────┐
│ Step │ Action              │ Description                        │
├──────┼─────────────────────┼────────────────────────────────────┤
│ 1    │ assign_team         │ 分配对话到 'Support' 团队           │
│ 2    │ add_tag             │ 添加标签 'escalated'               │
│ 3    │ send_session_message│ 发送消息："我们正在处理您的问题..." │
└──────┴─────────────────────┴────────────────────────────────────┘

⚠ This will modify conversation assignment. Proceed? (y/n): y

Executing...
✓ 分配对话到 'Support' 团队
✓ 添加标签 'escalated'
✓ 发送消息："我们正在处理您的问题，Support 团队会尽快联系您"

Summary: Conversation escalated successfully
```

**为什么选这个？**
- ✅ 展示复杂工作流（3 个不同类型的操作）
- ✅ 展示 Agent 能理解复杂的自然语言
- ✅ 展示实际业务场景（客服升级）
- ✅ 展示确认机制（修改操作需要确认）

---

## 🎬 完整 Demo 流程

### **推荐顺序（15 分钟演示）**

```
1. 简单查询 (1 分钟)
   → 展示基础能力，建立信心

2. Dry-run 模式 (2 分钟)
   → 展示产品思维，强调安全性

3. 多步编排 (3 分钟)
   → 展示核心价值，这是最重要的场景

4. 错误处理 (2 分钟)
   → 展示健壮性，用户会犯错

5. 澄清机制 (2 分钟)
   → 展示智能交互，不是简单的命令执行

6. 复杂编排 (3 分钟)
   → 展示高级能力，wow factor

7. 总结 + Q&A (2 分钟)
```

---

## 📝 Demo 脚本文件

创建 `demo.sh` 用于自动化演示：

```bash
#!/bin/bash
# WATI Conductor Demo Script

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           WATI Conductor - Interactive Demo                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "=== DEMO 1: 简单查询 ==="
echo "Command: conductor run \"找出所有 VIP 客户\""
echo ""
conductor run "找出所有 VIP 客户"
read -p "按回车继续..."
echo ""

echo "=== DEMO 2: Dry-run 模式 ==="
echo "Command: conductor run \"给所有雅加达的客户发送 flash_sale 模板\" --dry-run"
echo ""
conductor run "给所有雅加达的客户发送 flash_sale 模板" --dry-run
read -p "按回车继续..."
echo ""

echo "=== DEMO 3: 多步编排 ==="
echo "Command: conductor run \"给所有 VIP 客户发送 renewal_reminder 模板，填入他们的名字\""
echo ""
conductor run "给所有 VIP 客户发送 renewal_reminder 模板，填入他们的名字"
read -p "按回车继续..."
echo ""

echo "=== DEMO 4: 错误处理 ==="
echo "Command: conductor run \"给 VIP 客户发送 welcome_new 模板\""
echo ""
conductor run "给 VIP 客户发送 welcome_new 模板"
read -p "按回车继续..."
echo ""

echo "=== DEMO 5: 澄清机制 ==="
echo "Command: conductor run \"给 VIP 客户发消息\""
echo ""
conductor run "给 VIP 客户发消息"
read -p "按回车继续..."
echo ""

echo "=== DEMO 6: 复杂编排 ==="
echo "Command: conductor run \"把 6281234567890 的对话分配给 Support 团队，添加 'escalated' 标签，然后发消息告诉他我们正在处理\""
echo ""
conductor run "把 6281234567890 的对话分配给 Support 团队，添加 'escalated' 标签，然后发消息告诉他我们正在处理"
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Demo 完成！                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
```

**使用方法：**
```bash
chmod +x demo.sh
./demo.sh
```

---

## 🎯 功能覆盖矩阵

| Demo | Parse | Plan | Validate | Execute | Clarify | Dry-run | Error Handling |
|------|-------|------|----------|---------|---------|---------|----------------|
| 1. 简单查询 | ✅ | ✅ | ✅ | ✅ | - | - | - |
| 2. 多步编排 | ✅ | ✅ | ✅ | ✅ | - | - | ✅ (部分失败) |
| 3. Dry-run | ✅ | ✅ | ✅ | - | - | ✅ | - |
| 4. 澄清机制 | ✅ | ✅ | ✅ | - | ✅ | - | - |
| 5. 错误恢复 | ✅ | ✅ | ✅ | ✅ | - | - | ✅ (API 错误) |
| 6. 复杂编排 | ✅ | ✅ | ✅ | ✅ | - | - | - |

---

## 📊 业务场景覆盖

| 场景类型 | Demo 脚本 | WATI API 域 |
|---------|----------|------------|
| **客户管理** | Demo 1 | Contacts |
| **营销推广** | Demo 2, 3 | Messages, Templates, Broadcasts |
| **客服支持** | Demo 6 | Operators, Tickets, Messages |
| **错误处理** | Demo 4, 5 | 所有域 |

---

## 💡 演示技巧

### **准备工作**
1. 确保 Mock 数据已初始化（50 个联系人，10 个模板）
2. 测试所有脚本至少运行一次
3. 准备备用方案（如果某个 demo 失败）

### **演示时**
1. **先解释场景**：告诉观众这个场景的业务价值
2. **展示命令**：让观众看到自然语言输入
3. **强调亮点**：表格格式、进度条、错误提示
4. **互动提问**：问观众"你们平时怎么做这个？"

### **常见问题准备**
- Q: "支持英文吗？" A: "支持，LLM 是多语言的"
- Q: "能处理多少联系人？" A: "有速率限制保护，可以批量处理"
- Q: "错了怎么办？" A: "有 Dry-run 模式和确认机制"
- Q: "能自定义工作流吗？" A: "可以，通过自然语言描述任意流程"

---

## 🎥 录制 Demo 视频建议

### **视频结构（3-5 分钟）**

```
00:00 - 00:30  介绍（问题 + 解决方案）
00:30 - 01:00  Demo 1: 简单查询
01:00 - 02:00  Demo 3: 多步编排（核心）
02:00 - 02:30  Demo 2: Dry-run 模式
02:30 - 03:00  Demo 5: 错误处理
03:00 - 03:30  总结 + 下一步
```

### **录制工具**
- **终端录制**: asciinema (可以复制粘贴)
- **屏幕录制**: OBS Studio / QuickTime
- **后期处理**: 添加字幕、加速无聊部分

---

## ✅ Demo 检查清单

演示前确认：

- [ ] Mock 数据已初始化
- [ ] 所有 6 个脚本都测试过
- [ ] CLI 输出格式正确（表格、颜色）
- [ ] 错误信息清晰易懂
- [ ] 确认提示正常工作
- [ ] Dry-run 模式不执行实际操作
- [ ] 演示环境稳定（不会崩溃）
- [ ] 准备了备用方案

---

**最后更新**: 2026-04-09  
**用途**: WATI Conductor 产品演示和视频录制

# Domain Knowledge: Team & Operator Structure

## Teams

| Team Name | Responsibility | Hours | Escalation To |
|-----------|---------------|-------|---------------|
| `general-support` | First-line support, general inquiries | 9:00-18:00 | senior-support |
| `senior-support` | VIP contacts, complex issues, escalations | 9:00-21:00 | team-lead |
| `sales` | Pre-sales inquiries, product questions | 9:00-18:00 | sales-manager |
| `marketing` | Campaign management, broadcast operations | 9:00-18:00 | marketing-lead |

## Assignment Rules

### Auto-Assignment

- New conversations from contacts with tag "vip" → `senior-support`
- New conversations from contacts with tag "new" → `general-support`
- Conversations mentioning "order" or "shipping" → `general-support`
- Conversations mentioning "pricing" or "demo" → `sales`

### Manual Assignment

- Use `assign_operator` for specific operator assignment
- Use `assign_team` for team-level assignment (round-robin within team)
- Always check operator availability before assigning

## Operator Availability

- Operators have statuses: "online", "busy", "offline", "on-leave"
- Never assign to "offline" or "on-leave" operators
- "busy" operators can receive assignments but may have delayed response

## Escalation Protocol

1. If no response within SLA (30 min general, 15 min VIP) → escalate to team lead
2. If customer expresses frustration → immediate escalation
3. If issue requires technical knowledge → assign to senior-support
4. If issue involves billing/refund → assign to sales team

# SOP: VIP Contact Handling

## Purpose

Standard procedure for managing VIP contacts who require premium service levels.

## VIP Identification

- VIP contacts are identified by the tag "vip"
- VIP contacts may also have custom_param `tier: "premium"` or `tier: "enterprise"`
- Any contact with lifetime spend > $10,000 should be tagged as VIP

## Communication Rules

### Language Preference

- Always check the contact's `language` custom_param before sending templates
- If language is "zh" or "cn", use Chinese template variants (suffix `_zh`)
- If language is "ja", use Japanese template variants (suffix `_ja`)
- Default to English ("en") if no language preference is set

### Response Priority

- VIP contacts must be assigned to the "senior-support" team
- Response time SLA: within 15 minutes during business hours
- If no senior-support operator is available, escalate to team lead

### Template Selection

- Use personalized templates for VIP contacts (prefix `vip_`)
- If no VIP-specific template exists, use the standard template but add a personalized greeting
- Never send bulk marketing templates to VIP contacts — use targeted campaigns only

## Tagging Protocol

- When a contact becomes VIP: add tag "vip", remove tag "regular"
- When a VIP contact churns: add tag "vip-churned", keep tag "vip" for historical tracking
- VIP sub-segments: "vip-enterprise", "vip-premium", "vip-partner"

## Escalation

- If a VIP contact expresses dissatisfaction, immediately assign to team lead
- Log all VIP interactions for quarterly review
- Never auto-resolve VIP tickets — always require manual confirmation

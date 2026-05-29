# Domain Knowledge: Template Catalog

## Template Naming Convention

Templates follow the pattern: `{purpose}_{variant}_{version}`

- Purpose: what the template does (welcome, order_confirm, promo)
- Variant: language or audience (en, zh, vip)
- Version: iteration number (v1, v2)

## Available Templates

### Welcome Templates

| Name | Category | Language | Parameters | Use Case |
|------|----------|----------|------------|----------|
| `welcome_wati` | MARKETING | en_US | {{name}} | First-time contact greeting |
| `welcome_wati_zh` | MARKETING | zh_CN | {{name}} | Chinese-speaking contacts |

### Order Templates

| Name | Category | Language | Parameters | Use Case |
|------|----------|----------|------------|----------|
| `shopify_default_cod_confirm_order_v5` | MARKETING | en_US | {{name}}, {{total_price}} | COD order confirmation |
| `order_shipped` | UTILITY | en_US | {{name}}, {{tracking_number}} | Shipping notification |
| `order_delivered` | UTILITY | en_US | {{name}} | Delivery confirmation |

### Promotional Templates

| Name | Category | Language | Parameters | Use Case |
|------|----------|----------|------------|----------|
| `ecom_presales_oct` | MARKETING | en_US | {{name}}, {{discount}} | Seasonal promotion |
| `flash_sale_alert` | MARKETING | en_US | {{name}}, {{product}}, {{price}} | Flash sale notification |

### Support Templates

| Name | Category | Language | Parameters | Use Case |
|------|----------|----------|------------|----------|
| `ticket_created` | UTILITY | en_US | {{name}}, {{ticket_id}} | Ticket creation confirmation |
| `ticket_resolved` | UTILITY | en_US | {{name}}, {{ticket_id}} | Ticket resolution notification |
| `satisfaction_survey` | MARKETING | en_US | {{name}} | Post-resolution survey |

## Template Selection Guide

- **New contact, first interaction** → `welcome_wati` (or language variant)
- **Order placed** → `shopify_default_cod_confirm_order_v5`
- **Shipping update** → `order_shipped` (UTILITY — can send anytime)
- **Marketing campaign** → Check contact's opt-in status first, use appropriate promo template
- **Support ticket** → `ticket_created` / `ticket_resolved` (UTILITY — can send anytime)

## Parameter Mapping

Template parameters map to contact `custom_params`:

- `{{name}}` → contact.name
- `{{total_price}}` → must be provided at send time
- `{{tracking_number}}` → must be provided at send time
- `{{discount}}` → campaign-specific, provided at send time
- `{{ticket_id}}` → from ticket system

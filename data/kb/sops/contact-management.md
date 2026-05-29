# SOP: Contact Management

## Purpose

Standard procedures for searching, tagging, and updating contacts in WATI.

## Searching Contacts

### By Tag

- Use `search_contacts(tags=["tag_name"])` for single-tag search
- For multi-tag filtering, search by one tag then filter results client-side
- Common tags: "vip", "regular", "new", "unsubscribed", "do-not-contact"

### By Attributes

- Search by name: partial match supported
- Search by phone: use full international format (e.g., "628123450001")
- Search by custom_params: filter by city, tier, language after initial search

## Tagging Best Practices

### Adding Tags

- Tags are lowercase, hyphen-separated: "new-customer", "black-friday-2024"
- Campaign tags should include date: "promo-oct-2024", "welcome-q4"
- Never add more than 10 tags to a single contact

### Removing Tags

- Remove campaign tags after campaign ends (30 days post-campaign)
- Never remove "vip" or "do-not-contact" tags without explicit user confirmation
- When removing tags in batch, always confirm the count first

## Updating Attributes

### Allowed Updates

- `city`, `tier`, `language`, `company`, `notes` — freely updatable
- `name` — updatable but confirm with user first
- `whatsapp_number` — NEVER update (create new contact instead)

### Batch Updates

- Maximum 100 contacts per batch update operation
- Always preview 3-5 sample contacts before executing batch update
- Log all batch updates with before/after values

## Contact Lifecycle

1. **New**: Contact created, tag "new" added
2. **Active**: Engaged in conversation, tag "new" removed, segment tags added
3. **VIP**: High-value contact, tag "vip" added (see VIP SOP)
4. **Inactive**: No interaction for 90 days, tag "inactive" added
5. **Unsubscribed**: Opted out, tag "unsubscribed" added, excluded from all campaigns

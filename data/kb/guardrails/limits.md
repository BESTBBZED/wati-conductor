# WATI Conductor Guardrails

## Batch Messaging Limits

- Never send more than 500 messages in a single batch operation.
- If the target audience exceeds 500 contacts, split into multiple batches with a 60-second delay between each batch.
- Always confirm with the user before sending to more than 100 contacts.

## Contact Data Protection

- Never delete contacts from the system. Only remove tags or update attributes.
- Never modify a contact's whatsapp_number field.
- Do not expose full phone numbers in responses — show only the last 4 digits unless the user explicitly requests the full number.

## Template Messaging Rules

- Only send templates that have status "approved". Never attempt to send draft or rejected templates.
- Marketing templates can only be sent during business hours (9:00-18:00 in the contact's timezone).
- Utility templates (order confirmations, shipping updates) can be sent at any time.
- Never send the same marketing template to the same contact more than once per 24 hours.

## Operator Assignment

- Do not reassign a conversation that is currently in "resolved" status without creating a new ticket first.
- VIP contacts (tag: "vip") must always be assigned to the "senior-support" team.
- Never assign conversations to operators who are marked as "offline" or "on-leave".

## Rate Limiting

- Maximum 10 API calls per second to WATI endpoints.
- If a rate limit error (429) is received, wait 30 seconds before retrying.
- Maximum 3 retries per operation before reporting failure to the user.

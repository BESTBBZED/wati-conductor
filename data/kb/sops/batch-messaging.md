# SOP: Batch Template Messaging

## Purpose

Standard procedure for sending template messages to multiple contacts via WATI.

## Prerequisites

- Template must have status "approved" in WATI
- Target contacts must have valid WhatsApp numbers
- Contacts must not have opted out (no "unsubscribed" tag)

## Procedure

### Step 1: Identify Target Audience

1. Search contacts using relevant tags or attributes
2. Exclude contacts with tag "unsubscribed" or "do-not-contact"
3. Confirm the count with the user before proceeding

### Step 2: Select Template

1. List available templates matching the use case
2. Verify template status is "approved"
3. Check template parameters match available contact data
4. If template has parameters (e.g., {{name}}), ensure all target contacts have the required custom_params

### Step 3: Prepare Broadcast

1. Generate a broadcast name: `{template_name}_{date}_{time}`
2. Map contact custom_params to template parameters
3. If audience > 500, split into batches of 500

### Step 4: Execute Send

1. Call send_template_message_batch with the prepared recipients
2. Log the broadcast result (success count, failure count)
3. Report results to the user

### Step 5: Post-Send

1. Tag sent contacts with the broadcast name for tracking
2. If failures occurred, report which contacts failed and why
3. Do NOT retry failed sends automatically — inform the user first

## Common Failure Modes

- "Template not found": Template name is case-sensitive, check exact spelling
- "Invalid parameter": Contact is missing a required custom_param field
- "Number not on WhatsApp": Contact's number is not registered on WhatsApp
- "24h window expired": For session messages only, not applicable to templates

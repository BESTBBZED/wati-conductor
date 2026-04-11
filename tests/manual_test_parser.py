"""Manual test script for intent parser."""

import asyncio
from conductor.agent.parser import parse_intent


async def main():
    """Test intent parser with various instructions."""
    
    test_cases = [
        "Find all VIP contacts",
        "Send renewal_reminder template to all VIP contacts",
        "Escalate 6281234567890 to Support",
        "Send flash_sale to all Jakarta contacts",
        "Update contact 6281234567890 tier to premium",
    ]
    
    print("Testing Intent Parser\n" + "=" * 60)
    
    for instruction in test_cases:
        print(f"\n📝 Instruction: {instruction}")
        try:
            intent = await parse_intent(instruction)
            print(f"✅ Action: {intent.action}")
            print(f"   Target: {intent.target}")
            print(f"   Parameters: {intent.parameters}")
            print(f"   Confidence: {intent.confidence:.2f}")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

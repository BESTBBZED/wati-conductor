"""Manual test for parse → plan flow."""

import asyncio
from conductor.agent import parse_intent, generate_plan


async def main():
    """Test full parse → plan flow."""
    
    test_cases = [
        "Find all VIP contacts",
        "Send renewal_reminder template to all VIP contacts",
        "Escalate 6281234567890 to Support",
        "Update contact 6281234567890 tier to premium",
    ]
    
    print("Testing Parse → Plan Flow\n" + "=" * 80)
    
    for instruction in test_cases:
        print(f"\n📝 Instruction: {instruction}")
        print("-" * 80)
        
        try:
            # Parse intent
            intent = await parse_intent(instruction)
            print(f"✅ Intent parsed: {intent.action} (confidence: {intent.confidence:.2f})")
            
            # Generate plan
            plan = generate_plan(intent)
            print(f"📋 Plan generated: {plan.estimated_api_calls} API calls")
            print(f"   Explanation: {plan.explanation}")
            print(f"   Requires confirmation: {plan.requires_confirmation}")
            print(f"\n   Steps:")
            for i, step in enumerate(plan.steps, 1):
                deps = f" (depends on: {step.depends_on})" if step.depends_on else ""
                destructive = " [DESTRUCTIVE]" if step.is_destructive else ""
                print(f"   {i}. {step.tool}{deps}{destructive}")
                print(f"      → {step.description}")
                
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

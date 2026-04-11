"""Manual test for LangGraph state machine."""

import asyncio
from conductor.agent import create_agent_graph


async def main():
    """Test the agent graph."""
    
    test_cases = [
        {
            "instruction": "Find all VIP contacts",
            "mode": "execute"
        },
        {
            "instruction": "Send renewal_reminder template to all VIP contacts",
            "mode": "dry-run"  # Dry-run to avoid actual execution
        },
        {
            "instruction": "This is gibberish that won't parse",
            "mode": "execute"
        }
    ]
    
    print("Testing LangGraph Agent\n" + "=" * 80)
    
    agent = create_agent_graph()
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}: {test['instruction']}")
        print(f"Mode: {test['mode']}")
        print("=" * 80)
        
        try:
            result = await agent.ainvoke({
                "instruction": test["instruction"],
                "mode": test["mode"],
                "intent": None,
                "plan": None,
                "validation_errors": [],
                "needs_clarification": False,
                "clarification_questions": [],
                "execution_results": [],
                "execution_errors": [],
                "final_response": "",
                "success": False
            })
            
            print(f"\n✅ Success: {result.get('success', False)}")
            
            if result.get("intent"):
                print(f"📝 Intent: {result['intent'].action}")
            
            if result.get("plan"):
                print(f"📋 Plan: {len(result['plan'].steps)} steps")
                print(f"   {result['plan'].explanation}")
            
            if result.get("final_response"):
                print(f"\n💬 Response:\n{result['final_response']}")
            
            if result.get("execution_results"):
                print(f"\n📊 Executed {len(result['execution_results'])} steps")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

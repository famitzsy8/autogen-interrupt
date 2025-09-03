#!/usr/bin/env python3
"""
Test table parsing with realistic agent output formats
"""

import asyncio
from stream_accumulator import StreamAccumulator

# Sample table formats that agents might produce
SAMPLE_OUTPUTS = {
    "numbered_list": """
Based on my analysis, here are the key congressional members for this investigation:

1. Senator Ted Cruz (R-TX) - Committee Chair on Energy and Natural Resources, strong ties to oil industry
2. Representative Alexandria Ocasio-Cortez (D-NY-14) - Vocal critic of fossil fuel lobbying, Green New Deal advocate  
3. Senator Joe Manchin (D-WV) - Receives significant energy industry donations, moderate on climate policy
4. Representative Dan Crenshaw (R-TX-2) - Former oil industry executive, sits on Energy Committee
5. Senator Elizabeth Warren (D-MA) - Financial Services Committee, focuses on corporate accountability

TERMINATE
""",

    "markdown_table": """
Here's my ranking of congressional members by relevance to this lobbying investigation:

| Member Name | State | Party | Committee Role | Influence Level |
|-------------|-------|-------|----------------|-----------------|
| Ted Cruz | TX | R | Energy Committee Chair | High - Industry connections |
| Joe Manchin | WV | D | Energy Committee Ranking | High - Moderate swing vote |
| AOC | NY-14 | D | Oversight Subcommittee | Medium - Anti-lobbying advocate |
| Dan Crenshaw | TX-2 | R | Energy Committee Member | Medium - Former industry executive |
| Lisa Murkowski | AK | R | Energy Committee Vice Chair | High - Alaska oil interests |

This concludes my analysis.

TERMINATE
""",

    "mixed_format": """
Congressional Members Analysis - Exxon Mobil Lobbying on HR2307:

Top Priority Members:
1. Ted Cruz (R-Texas): Energy Committee Chair, $2.1M from oil/gas industry
2. Joe Manchin (D-West Virginia): Key swing vote, owns coal company stock

Secondary Priority:
- Alexandria Ocasio-Cortez (NY-14, Democrat): Leading Green New Deal opponent
- Dan Crenshaw (TX-2, Republican): Former energy executive, reliable industry vote
- Lisa Murkowski (Alaska, Republican): State dependent on oil revenue

Additional Members of Interest:
• John Barrasso (R-WY) - Environment Committee ranking member
• Sheldon Whitehouse (D-RI) - Climate advocate and industry critic

Summary: 7 members identified across both chambers with varying levels of influence.

TERMINATE
""",

    "simple_text": """
Key findings from the investigation:

The most influential members regarding this bill are Ted Cruz from Texas (Republican, Energy Committee), Joe Manchin from West Virginia (Democrat, moderate), and Alexandria Ocasio-Cortez from New York's 14th district (Democrat, progressive). 

Cruz chairs the Energy Committee and has significant oil industry ties. Manchin is a key swing vote who owns energy assets. AOC leads progressive opposition to fossil fuel interests.

Other notable members include Dan Crenshaw (Texas 2nd district, Republican, former oil executive) and Lisa Murkowski (Alaska Republican, oil state interests).

TERMINATE
"""
}

class TestCallback:
    def __init__(self):
        self.events = []
        
    async def __call__(self, event):
        self.events.append(event)
        print(f"📡 Event: {event['type']}")
        if event['type'] == 'investigation_concluded':
            data = event.get('data', {})
            if data.get('table_available'):
                table_data = data.get('table_data', {})
                members = table_data.get('members', [])
                print(f"   📊 Table parsed: {len(members)} members found")
                for i, member in enumerate(members[:3]):  # Show first 3
                    print(f"   {i+1}. {member.get('name', 'Unknown')} ({member.get('state', 'Unknown')}) - {member.get('reason', 'No reason')[:50]}...")
            else:
                print(f"   ❌ No table detected")

async def test_table_format(format_name: str, content: str):
    print(f"\n🧪 Testing {format_name.upper()} Format")
    print("=" * 60)
    
    callback = TestCallback()
    accumulator = StreamAccumulator(websocket_callback=callback)
    
    # Simulate the message with TERMINATE
    class MockMessage:
        def __init__(self, content):
            self.__class__.__name__ = "ModelClientStreamingChunkEvent"
            self.source = "orchestrator"
            self.content = content
    
    # Process the content
    mock_msg = MockMessage(content)
    await accumulator.process_stream_message(mock_msg)
    await asyncio.sleep(0.6)  # Wait for finalization
    
    # Check results
    table_events = [e for e in callback.events if e['type'] == 'investigation_concluded']
    if table_events:
        data = table_events[0].get('data', {})
        if data.get('table_available'):
            table_data = data.get('table_data', {})
            print(f"✅ SUCCESS: Parsed {len(table_data.get('members', []))} members")
            print(f"   Table type: {table_data.get('table_type', 'unknown')}")
            
            # Show detailed results
            for member in table_data.get('members', [])[:5]:  # Show first 5
                name = member.get('name', 'Unknown')
                state = member.get('state', 'Unknown')
                district = member.get('district', '')
                party = member.get('party', 'Unknown')
                chamber = member.get('chamber', 'Unknown')
                reason = member.get('reason', 'No reason')
                
                location = f"{state}-{district}" if district else state
                print(f"   • {name} ({party}, {location}, {chamber}): {reason[:60]}...")
        else:
            print("❌ FAILED: No table detected")
    else:
        print("❌ FAILED: No investigation conclusion event")

async def main():
    print("🔍 Table Parsing Test Suite")
    print("Testing various agent output formats for table detection and parsing")
    
    for format_name, content in SAMPLE_OUTPUTS.items():
        await test_table_format(format_name, content)
    
    print("\n🎯 Summary")
    print("=" * 60)
    print("Test completed. Check results above to see which formats")
    print("are successfully parsed and which need improvement.")

if __name__ == "__main__":
    asyncio.run(main())
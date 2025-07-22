"""Simple test script to debug deck API endpoints"""
import asyncio
import httpx
import json

async def test_endpoints():
    async with httpx.AsyncClient() as client:
        base_url = "http://localhost:8000"
        
        print("Testing Deck API Endpoints...")
        print("=" * 50)
        
        # Test 1: Get all decks
        print("\n1. Testing GET /api/decks/")
        try:
            response = await client.get(f"{base_url}/api/decks/")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 2: Get specific deck
        print("\n2. Testing GET /api/decks/A")
        try:
            response = await client.get(f"{base_url}/api/decks/A")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 3: Get mixer state
        print("\n3. Testing GET /api/decks/mixer/state")
        try:
            response = await client.get(f"{base_url}/api/decks/mixer/state")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "=" * 50)
        print("Testing complete!")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
import asyncio
import websockets
import json

async def test_connection():
    uri = "ws://10.0.0.251:8011/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Send init
            init_msg = {"type": "connection.init", "payload": {"client_version": "1.0.0"}}
            await websocket.send(json.dumps(init_msg))
            print(f"Sent: {init_msg}")
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received: {response}")
            
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())

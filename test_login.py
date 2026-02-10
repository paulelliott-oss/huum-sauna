import asyncio
from huum.huum import Huum

async def test_credentials(username, password):
    print(f"Testing login for: {username}")
    huum = Huum(username=username, password=password)
    await huum.open_session()
    try:
        status = await huum.status()
        print("✅ SUCCESS! Connected to sauna.")
        print(f"   Temperature: {status.temperature}°C")
        print(f"   Humidity: {status.humidity}%")
        print(f"   Door: {'Open' if status.door else 'Closed'}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    finally:
        await huum.close_session()

# Replace with customer's actual credentials
USERNAME = "customer@email.com"
PASSWORD = "their_password"

asyncio.run(test_credentials(USERNAME, PASSWORD))

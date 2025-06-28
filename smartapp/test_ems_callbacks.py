import requests
import json

def test_data_callback():
    """Test the data callback endpoint with sample data"""
    
    # Sample data callback payload (based on EMS API documentation)
    test_payload = {
        "site": "NM-AIST",
        "locName": "Kikuletwa Kilimanjaro",
        "timeZone": "03:00:00",
        "lastVerified": "2025-06-28T10:00:00",
        "channels": "https://api.emsbrno.cz/channels/locality/NM-AIST/Kikuletwa%20Kilimanjaro/culture/en?auth=test_token",
        "data": {
            "1": {"url": "https://api.emsbrno.cz/data/locality/NM-AIST/Kikuletwa%20Kilimanjaro/from/2025-06-27/to/2025-06-28?auth=test_token"},
            "5": {"url": "https://api.emsbrno.cz/data/locality/NM-AIST/Kikuletwa%20Kilimanjaro/from/2025-06-23/to/2025-06-28?auth=test_token"},
            "10": {"url": "https://api.emsbrno.cz/data/locality/NM-AIST/Kikuletwa%20Kilimanjaro/from/2025-06-18/to/2025-06-28?auth=test_token"}
        }
    }
    
    # Send test request to your callback endpoint
    response = requests.post(
        'http://localhost:8000/ems-callback/',
        json=test_payload,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.status_code == 200

def test_image_callback():
    """Test the image callback endpoint with sample data"""
    
    test_payload = {
        "site": "NM-AIST",
        "locName": "Kikuletwa Kilimanjaro",
        "cultures": {
            "en": {
                "channels": {
                    "1": {"url": "https://api.emsbrno.cz/channels/locality/NM-AIST/Kikuletwa%20Kilimanjaro/culture/en/from/2025-06-27/to/2025-06-28?auth=test_token"}
                },
                "chart": {
                    "1": {
                        "4621": {"url": "https://api.emsbrno.cz/chart/channels/4621/culture/en/from/2025-06-27/to/2025-06-28?auth=test_token"},
                        "4622": {"url": "https://api.emsbrno.cz/chart/channels/4622/culture/en/from/2025-06-27/to/2025-06-28?auth=test_token"}
                    },
                    "5": {
                        "4621": {"url": "https://api.emsbrno.cz/chart/channels/4621/culture/en/from/2025-06-23/to/2025-06-28?auth=test_token"},
                        "4622": {"url": "https://api.emsbrno.cz/chart/channels/4622/culture/en/from/2025-06-23/to/2025-06-28?auth=test_token"}
                    }
                }
            }
        }
    }
    
    response = requests.post(
        'http://localhost:8000/ems-image-callback/',
        json=test_payload,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.status_code == 200

if __name__ == "__main__":
    print("Testing EMS API callbacks...")
    print("\n1. Testing data callback:")
    test_data_callback()
    
    print("\n2. Testing image callback:")
    test_image_callback()
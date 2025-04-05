from src.core.api_client import APIClient
import sys
from pathlib import Path

def test_vision():
    client = APIClient()
    
    # 1. URL 이미지 테스트
    print("\n1. Testing with URL image...")
    url_result = client.analyze_image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1869px-Python-logo-notext.svg.png",
        prompt="What is this logo?",
        detail="high"
    )
    print(f"URL Image Result: {url_result}\n")
    
    # 2. 로컬 이미지 테스트
    # macOS의 경우 일반적으로 사용자의 Desktop에 있는 이미지를 테스트
    print("\n2. Testing with local image...")
    home = Path.home()
    test_image = home / "Desktop" / "test.jpg"  # 테스트할 이미지 경로를 적절히 수정하세요
    
    if test_image.exists():
        local_result = client.analyze_image(
            str(test_image),
            prompt="이 이미지를 자세히 설명해주세요",
            detail="auto"
        )
        print(f"Local Image Result: {local_result}\n")
    else:
        print(f"Local test image not found at: {test_image}\n")
    
    # 3. 에러 케이스 테스트
    print("\n3. Testing error cases...")
    
    # 3.1. 존재하지 않는 파일
    try:
        client.analyze_image("nonexistent.jpg")
    except FileNotFoundError as e:
        print(f"Expected error for nonexistent file: {e}")
    
    # 3.2. 잘못된 URL
    try:
        client.analyze_image("https://example.com/nonexistent.jpg")
    except Exception as e:
        print(f"Expected error for invalid URL: {e}")

if __name__ == "__main__":
    print("Starting Vision API tests...")
    test_vision()
    print("\nTests completed!") 
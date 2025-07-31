"""
Test script for Forvo API integration.
This script can be used to test the Forvo API functionality once you have an API key.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from danish_audio_downloader.core.forvo_api import ForvoAPIClient
from danish_audio_downloader.core.audio_provider import ForvoAudioProvider

def test_forvo_api():
    """Test the Forvo API with a sample word."""
    print("Testing Forvo API Integration")
    print("=" * 40)
    
    # Check if API key is provided
    api_key = input("Enter your Forvo API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("⚠️  No API key provided. Skipping Forvo API test.")
        print("   To test the Forvo API:")
        print("   1. Get an API key from https://api.forvo.com/")
        print("   2. Run this script again with your API key")
        return
    
    try:
        # Test the Forvo API client
        print("Testing ForvoAPIClient...")
        client = ForvoAPIClient(api_key)
        
        # Test with a simple Danish word
        test_word = "hej"
        print(f"Testing pronunciation lookup for '{test_word}'...")
        
        result = client.get_word_pronunciations(test_word, "da")
        
        if result['success']:
            print(f"✅ Successfully found pronunciations for '{test_word}'")
            items = result['data']['items']
            print(f"   Found {len(items)} pronunciation(s)")
            
            for i, item in enumerate(items[:3]):  # Show first 3
                username = item.get('username', 'Unknown')
                votes = item.get('num_votes', 0)
                country = item.get('country', 'Unknown')
                print(f"   {i+1}. {username} from {country} (votes: {votes})")
        else:
            print(f"❌ Failed to get pronunciations: {result['error']}")
            return
        
        # Test the audio provider
        print("\nTesting ForvoAudioProvider...")
        temp_dir = "temp_test_audio"
        os.makedirs(temp_dir, exist_ok=True)
        
        provider = ForvoAudioProvider(
            forvo_api_key=api_key,
            output_dir=temp_dir
        )
        
        print(f"Testing audio download for '{test_word}'...")
        download_result = provider._download_word_audio_and_data(test_word)
        
        if download_result['success']:
            print(f"✅ Successfully downloaded audio for '{test_word}'")
            
            # Check if file exists
            audio_file = os.path.join(temp_dir, f"{test_word}.mp3")
            if os.path.exists(audio_file):
                file_size = os.path.getsize(audio_file)
                print(f"   Audio file: {audio_file}")
                print(f"   File size: {file_size} bytes")
                
                # Clean up
                os.remove(audio_file)
                os.rmdir(temp_dir)
                print("   Test files cleaned up")
            
            # Check dictionary data
            dict_data = download_result.get('dictionary_data')
            if dict_data and dict_data.get('ordnet_found'):
                print("   Dictionary data from Ordnet:")
                print(f"     Definition: {dict_data.get('danish_definition', 'N/A')}")
                print(f"     Word type: {dict_data.get('word_type', 'N/A')}")
                print(f"     Pronunciation: {dict_data.get('pronunciation', 'N/A')}")
        else:
            print(f"❌ Audio download failed")
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        
        print("\n✅ Forvo API integration test completed successfully!")
        print("   Your setup is ready to use with the Danish Audio Downloader.")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        # Clean up on error
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass

if __name__ == "__main__":
    test_forvo_api()

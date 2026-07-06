import requests
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_map():
    # Check if a URL was provided as an argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        print("Error: No URL provided.")
        print("1. Go to https://tracker.marineheatwaves.org/")
        print("2. Right-click the map download button -> Copy Link Address")
        print("3. Run: python fetch_map.py \"<PASTE_URL_HERE>\"")
        return
    
    output_file = "MHW_tracker_map.png" 
    
    print(f"Downloading map...")
    try:
        response = requests.get(url, stream=True, verify=False)
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Success! Saved to {output_file}")
        elif response.status_code == 404:
            print("Error 404: The session ID in this URL has expired.")
            print("Please get a fresh link from the tracker website.")
        else:
            print(f"Failed to download (Status: {response.status_code}).")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download_map()
import os
import urllib.request
import zipfile
import shutil

# Configuration
DATA_SOURCES = {
    'ai_models': {
        'url': 'https://epoch.ai/data/ai_models.zip',
        'target_dir': 'example_data/ai_models',
        'type': 'zip'
    },
    'benchmark_data': {
        'url': 'https://epoch.ai/data/benchmark_data.zip',
        'target_dir': 'example_data/benchmark_data',
        'type': 'zip'
    },
    'metr_data': {
        'url': 'https://metr.org/assets/benchmark_results.yaml',
        'target_path': 'METR/benchmark_results.yaml',
        'type': 'file'
    }
}

TEMP_DIR = 'temp_downloads'

def download_and_update():
    # Ensure local directory structure exists
    if not os.path.exists('example_data'):
        os.makedirs('example_data')
    
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    for name, config in DATA_SOURCES.items():
        url = config['url']
        source_type = config.get('type', 'zip')

        if source_type == 'zip':
            target_dir = config['target_dir']
            zip_path = os.path.join(TEMP_DIR, f"{name}.zip")

            print(f"Downloading {name} from {url}...")
            try:
                urllib.request.urlretrieve(url, zip_path)
                print(f"Successfully downloaded {zip_path}")

                # Ensure target directory exists
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                print(f"Extracting to {target_dir}...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Extracting all to target_dir
                    zip_ref.extractall(target_dir)
                
                print(f"Update complete for {name}.\n")

            except Exception as e:
                print(f"Error updating {name}: {e}")
        
        elif source_type == 'file':
            target_path = config['target_path']
            print(f"Downloading {name} from {url}...")
            
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                urllib.request.urlretrieve(url, target_path)
                print(f"Successfully downloaded to {target_path}")
                print(f"Update complete for {name}.\n")
            except Exception as e:
                print(f"Error updating {name}: {e}")

    # Cleanup temp directory
    print("Cleaning up temporary files...")
    shutil.rmtree(TEMP_DIR)
    print("Done.")

if __name__ == "__main__":
    download_and_update()

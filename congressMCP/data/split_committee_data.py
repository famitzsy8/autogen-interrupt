import yaml
import os
from collections import defaultdict

def split_committee_files():
    """
    Reads the large 113_119.yaml file and splits it into separate
    files for each congress, e.g., committees_113.yaml, committees_114.yaml, etc.
    """
    # Construct the path relative to the script's location
    script_dir = os.path.dirname(__file__)
    original_file_path = os.path.join(script_dir, '113_119.yaml')
    
    print(f"Reading from {original_file_path}...")

    try:
        with open(original_file_path, 'r') as f:
            full_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: Could not find the source file at {original_file_path}")
        return
    except yaml.YAMLError as e:
        print(f"ERROR: Could not parse the YAML file. {e}")
        return

    # Group data by congress number
    data_by_congress = defaultdict(dict)
    
    for key, value in full_data.items():
        try:
            congress_num = int(key.split('_')[-1])
            data_by_congress[congress_num][key] = value
        except (IndexError, ValueError):
            print(f"Skipping malformed key: {key}")
            continue

    # Write a new file for each congress
    for congress_num, congress_data in data_by_congress.items():
        new_file_name = f'committees_{congress_num}.yaml'
        new_file_path = os.path.join(script_dir, new_file_name)
        
        print(f"Writing data for {congress_num}th Congress to {new_file_path}...")
        try:
            with open(new_file_path, 'w') as f:
                yaml.dump(congress_data, f, default_flow_style=False, sort_keys=False)
        except IOError as e:
            print(f"ERROR: Could not write to file {new_file_path}. {e}")

    print("Splitting complete.")

if __name__ == "__main__":
    split_committee_files()

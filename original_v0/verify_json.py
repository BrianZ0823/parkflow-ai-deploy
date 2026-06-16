import json
import os

def load_json_file(filename):
    filepath = os.path.join("external_api", filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Successfully loaded {filename}")
            return data
    except Exception as e:
        print(f"Failed to load {filename}: {e}")

load_json_file("enterprise_news.json")

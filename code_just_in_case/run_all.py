import json
from data_collector import collect_data
from persona_generator import create_personas_from_data

def run_pipeline():
    """
    Runs the entire data collection and persona generation pipeline.
    """
    # 1. Collect and save the Reddit data
    print("Starting data collection...")
    reddit_data = collect_data()

    if not reddit_data:
        print("Data collection failed. Exiting.")
        return

    # 2. Generate personas from the collected data
    print("\nGenerating personas from collected comments...")
    personas = create_personas_from_data(reddit_data)

    # 3. Save the generated personas to a JSON file
    if personas:
        with open("personas.json", "w") as f:
            json.dump(personas, f, indent=2)
        print(f"Successfully generated and saved {len(personas)} personas to personas.json")
    else:
        print("No personas were generated.")

if __name__ == "__main__":
    run_pipeline()
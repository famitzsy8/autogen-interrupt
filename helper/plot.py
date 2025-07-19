import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def plot_token_distribution(json_file='bill_token_lengths.json'):
    """
    Reads a JSON file with bill token lengths and plots two distributions:
    1. Histogram with a logarithmic x-scale.
    2. Histogram with a linear x-scale.
    """
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {json_file} was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file}.")
        return

    token_lengths = list(data.values())
    num_bills = len(token_lengths)
    
    if num_bills == 0:
        print("No data to plot.")
        return

    sns.set_style("whitegrid")
    
    # --- Plot 1: Logarithmic Scale ---
    plt.figure(figsize=(12, 6))
    sns.histplot(token_lengths, bins=50, kde=True, stat="density", log_scale=True)
    plt.title(f'Token Length Distribution of {num_bills} Big Oil Bills (Log Scale)')
    plt.xlabel('Token Length (log scale)')
    plt.ylabel('Relative Frequency')
    plt.savefig('token_distribution_log.png')
    plt.show()

    # --- Plot 2: Linear Scale ---
    plt.figure(figsize=(12, 6))
    sns.histplot(token_lengths, bins=50, kde=True, stat="density")
    plt.title(f'Token Length Distribution of {num_bills} Big Oil Bills (Linear Scale)')
    plt.xlabel('Token Length')
    plt.ylabel('Relative Frequency')
    plt.savefig('token_distribution_linear.png')
    plt.show()

if __name__ == "__main__":
    plot_token_distribution() 
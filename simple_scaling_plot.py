#!/usr/bin/env python3
"""
Simple Scaling Analysis - Line Chart
Shows interrupt and send message performance scaling across 2, 3, and 5 agents.
"""

import matplotlib.pyplot as plt
import numpy as np

def main():
    """Create line chart showing individual samples for performance scaling."""
    
    # Data from your test runs
    agent_counts = [2, 3, 4, 5]  # Include 4 agents since we have data
    
    # INTERRUPT TIMING DATA (individual sample times in seconds)
    interrupt_data = {
        2: [25.296, 14.639, 12.369, 15.041],  # 4 samples
        3: [18.215, 6.705, 7.101],  # 3 samples
        4: [18.741, 14.841, 12.992, 14.946],  # 4 samples
        5: [24.159, 18.376, 19.685, 23.037]  # 4 samples
    }
    
    # SEND MESSAGE TIMING DATA (individual sample times in seconds)
    send_data = {
        2: [1.582, 1.237, 2.15, 1.747],  # 4 samples
        3: [2.267, 1.252, 1.306],  # 3 samples
        4: [1.328, 1.747, 2.165, 1.434],  # 4 samples
        5: [1.582, 1.237, 2.15, 1.747]   # 4 samples
    }
    
    print("📊 Creating Individual Sample Scaling Analysis...")
    print(f"Agent counts: {agent_counts}")
    print(f"Interrupt samples per config: {[len(interrupt_data[agents]) for agents in agent_counts]}")
    print(f"Send samples per config: {[len(send_data[agents]) for agents in agent_counts]}")
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Colors for different samples
    interrupt_colors = ['darkred', 'red', 'lightcoral', 'pink']
    send_colors = ['darkblue', 'blue', 'lightblue', 'lightsteelblue']
    
    # Plot individual interrupt samples
    max_samples = max(len(samples) for samples in interrupt_data.values())
    for sample_idx in range(max_samples):
        interrupt_values = []
        send_values = []
        valid_agent_counts = []
        
        for agents in agent_counts:
            if sample_idx < len(interrupt_data[agents]):
                interrupt_values.append(interrupt_data[agents][sample_idx])
                send_values.append(send_data[agents][sample_idx])
                valid_agent_counts.append(agents)
        
        if interrupt_values:  # Only plot if we have data
            # Plot interrupt sample line
            plt.plot(valid_agent_counts, interrupt_values, 
                    marker='o', linewidth=2, markersize=6, 
                    color=interrupt_colors[sample_idx % len(interrupt_colors)], 
                    alpha=0.8, linestyle='-',
                    label=f'Interrupt Sample {sample_idx + 1}')
            
            # Plot send message sample line
            plt.plot(valid_agent_counts, send_values, 
                    marker='s', linewidth=2, markersize=6, 
                    color=send_colors[sample_idx % len(send_colors)], 
                    alpha=0.8, linestyle='--',
                    label=f'Send Message Sample {sample_idx + 1}')
    
    # Formatting
    plt.xlabel('Number of Agents', fontsize=14, fontweight='bold')
    plt.ylabel('Runtime (seconds)', fontsize=14, fontweight='bold')
    plt.title('AutoGen Interrupt System - Individual Sample Performance', fontsize=16, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=9, loc='upper left', ncol=2)
    
    # Set x-axis ticks
    plt.xticks(agent_counts)
    
    # Add some padding to y-axis
    all_values = []
    for data in interrupt_data.values():
        all_values.extend(data)
    for data in send_data.values():
        all_values.extend(data)
    plt.ylim(0, max(all_values) * 1.1)
    
    # Save the plot
    plt.tight_layout()
    plt.savefig('/Users/tofixjr/Desktop/Thesis/autogen-interrupt/scaling_analysis.png', 
                dpi=300, bbox_inches='tight')
    plt.savefig('/Users/tofixjr/Desktop/Thesis/autogen-interrupt/scaling_analysis.pdf', 
                bbox_inches='tight')
    
    print("📈 Plot saved as:")
    print("   - scaling_analysis.png")
    print("   - scaling_analysis.pdf")
    
    # Print scaling analysis with averages
    print(f"\n🔍 SCALING ANALYSIS (AVERAGES):")
    interrupt_avg = {agents: sum(interrupt_data[agents])/len(interrupt_data[agents]) for agents in agent_counts}
    send_avg = {agents: sum(send_data[agents])/len(send_data[agents]) for agents in agent_counts}
    
    print("Interrupt time averages:")
    for agents in agent_counts:
        print(f"  {agents} agents: {interrupt_avg[agents]:.1f}s")
    
    print("\nSend message time averages:")
    for agents in agent_counts:
        print(f"  {agents} agents: {send_avg[agents]:.1f}s")
    
    print(f"\nScaling ratios:")
    print(f"Interrupt scaling: 2→3→4→5 agents: {interrupt_avg[2]:.1f} → {interrupt_avg[3]:.1f} → {interrupt_avg[4]:.1f} → {interrupt_avg[5]:.1f}")
    print(f"Send scaling: 2→3→4→5 agents: {send_avg[2]:.1f} → {send_avg[3]:.1f} → {send_avg[4]:.1f} → {send_avg[5]:.1f}")
    
    plt.show()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Performance Analysis Plotting Script
Analyzes interrupt and send message timing data across different numbers of agents.
"""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from typing import Dict, List
import statistics

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def main():
    """Main function to create performance analysis plots."""
    
    # Data from test runs - you'll need to update these with your actual measurements
    # Format: {num_agents: [list_of_times]}
    
    # INTERRUPT TIMING DATA (seconds)
    # Note: You'll need to run tests with 2 and 3 agents to get complete data
    interrupt_data = {
        # 2: [],  # Run test_real_interrupt.py to get this data
        # 3: [],  # Run interrupt2.py with 3 agents to get this data  
        5: [44.68, 34.509, 37.174, 33.18]  # From terminal output (5 agents)
    }
    
    # SEND MESSAGE TIMING DATA (seconds)  
    send_message_data = {
        # 2: [],  # Run test_real_interrupt.py to get this data
        # 3: [],  # Run interrupt2.py with 3 agents to get this data
        5: [1.591, 3.014, 2.148, 2.366]   # From terminal output (5 agents)
    }
    
    print("⚠️  NOTE: To get complete analysis, run:")
    print("   - test_real_interrupt.py (for 2 agents data)")
    print("   - interrupt2.py with 3 agents (modify participants list)")
    print("   - Then update this script with the timing data")
    print()
    
    # For now, let's create a demo plot with the 5-agent data we have
    if not interrupt_data or not send_message_data:
        print("📊 Creating demo plot with available 5-agent data...")
        create_demo_plots(interrupt_data[5], send_message_data[5])
        return
    
    print("🎨 Creating Performance Analysis Plots...")
    print("=" * 50)
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('AutoGen Interrupt System - Performance Analysis', fontsize=16, fontweight='bold')
    
    # Plot 1: Average Interrupt Times by Number of Agents
    plot_average_times(ax1, interrupt_data, "Interrupt", "🛑 Average Interrupt Time vs Number of Agents")
    
    # Plot 2: Average Send Message Times by Number of Agents  
    plot_average_times(ax2, send_message_data, "Send Message", "📤 Average Send Message Time vs Number of Agents")
    
    # Plot 3: Interrupt Time Distributions (Box Plot)
    plot_distributions(ax3, interrupt_data, "Interrupt", "🛑 Interrupt Time Distributions")
    
    # Plot 4: Send Message Time Distributions (Box Plot)
    plot_distributions(ax4, send_message_data, "Send Message", "📤 Send Message Time Distributions")
    
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('/Users/tofixjr/Desktop/Thesis/autogen-interrupt/performance_analysis.png', 
                dpi=300, bbox_inches='tight')
    plt.savefig('/Users/tofixjr/Desktop/Thesis/autogen-interrupt/performance_analysis.pdf', 
                bbox_inches='tight')
    
    print("📊 Plots saved as:")
    print("   - performance_analysis.png")
    print("   - performance_analysis.pdf")
    
    # Print statistical analysis
    print_statistical_analysis(interrupt_data, send_message_data)
    
    plt.show()

def plot_average_times(ax, data: Dict[int, List[float]], operation_type: str, title: str):
    """Plot average times with error bars."""
    agent_counts = sorted(data.keys())
    avg_times = [statistics.mean(data[count]) for count in agent_counts]
    std_times = [statistics.stdev(data[count]) if len(data[count]) > 1 else 0 for count in agent_counts]
    
    # Line plot with error bars
    ax.errorbar(agent_counts, avg_times, yerr=std_times, 
               marker='o', linewidth=2, markersize=8, capsize=5)
    
    # Add value labels on points
    for x, y, std in zip(agent_counts, avg_times, std_times):
        ax.annotate(f'{y:.2f}±{std:.2f}s', (x, y), textcoords="offset points", 
                   xytext=(0,10), ha='center', fontsize=9)
    
    ax.set_xlabel('Number of Agents', fontweight='bold')
    ax.set_ylabel(f'{operation_type} Time (seconds)', fontweight='bold')
    ax.set_title(title, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(agent_counts)

def plot_distributions(ax, data: Dict[int, List[float]], operation_type: str, title: str):
    """Plot distribution of times using box plots."""
    agent_counts = sorted(data.keys())
    values = [data[count] for count in agent_counts]
    labels = [f'{count} agents' for count in agent_counts]
    
    # Box plot
    bp = ax.boxplot(values, labels=labels, patch_artist=True)
    
    # Color the boxes
    colors = ['lightblue', 'lightgreen', 'lightcoral']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax.set_ylabel(f'{operation_type} Time (seconds)', fontweight='bold')
    ax.set_title(title, fontweight='bold')
    ax.grid(True, alpha=0.3)

def create_demo_plots(interrupt_times: List[float], send_times: List[float]):
    """Create demonstration plots with the 5-agent data we have."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('AutoGen Interrupt System - Performance Analysis (5 Agents)', 
                 fontsize=14, fontweight='bold')
    
    # Plot 1: Interrupt times across attempts
    ax1.plot(range(1, len(interrupt_times) + 1), interrupt_times, 
             marker='o', linewidth=2, markersize=8, color='red', alpha=0.7)
    ax1.set_xlabel('Interrupt Attempt', fontweight='bold')
    ax1.set_ylabel('Interrupt Time (seconds)', fontweight='bold')
    ax1.set_title('🛑 Interrupt Times (5 Agents)', fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=statistics.mean(interrupt_times), color='red', linestyle='--', 
                alpha=0.5, label=f'Average: {statistics.mean(interrupt_times):.1f}s')
    ax1.legend()
    
    # Annotate points with values
    for i, time in enumerate(interrupt_times):
        ax1.annotate(f'{time:.1f}s', (i+1, time), textcoords="offset points", 
                    xytext=(0,10), ha='center', fontsize=9)
    
    # Plot 2: Send message times across attempts  
    ax2.plot(range(1, len(send_times) + 1), send_times, 
             marker='s', linewidth=2, markersize=8, color='blue', alpha=0.7)
    ax2.set_xlabel('Send Message Attempt', fontweight='bold')
    ax2.set_ylabel('Send Message Time (seconds)', fontweight='bold')
    ax2.set_title('📤 Send Message Times (5 Agents)', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=statistics.mean(send_times), color='blue', linestyle='--', 
                alpha=0.5, label=f'Average: {statistics.mean(send_times):.1f}s')
    ax2.legend()
    
    # Annotate points with values
    for i, time in enumerate(send_times):
        ax2.annotate(f'{time:.1f}s', (i+1, time), textcoords="offset points", 
                    xytext=(0,10), ha='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('/Users/tofixjr/Desktop/Thesis/autogen-interrupt/interrupt_performance_5agents.png', 
                dpi=300, bbox_inches='tight')
    plt.savefig('/Users/tofixjr/Desktop/Thesis/autogen-interrupt/interrupt_performance_5agents.pdf', 
                bbox_inches='tight')
    
    print("📊 Demo plots saved as:")
    print("   - interrupt_performance_5agents.png")
    print("   - interrupt_performance_5agents.pdf")
    
    # Print statistics for current data
    print(f"\n📈 STATISTICS FOR 5-AGENT TEST:")
    print("=" * 40)
    print(f"🛑 INTERRUPT TIMES:")
    print(f"   Average: {statistics.mean(interrupt_times):.3f}s")
    print(f"   Median:  {statistics.median(interrupt_times):.3f}s")  
    print(f"   Std Dev: {statistics.stdev(interrupt_times):.3f}s")
    print(f"   Range:   {min(interrupt_times):.3f}s - {max(interrupt_times):.3f}s")
    print()
    print(f"📤 SEND MESSAGE TIMES:")
    print(f"   Average: {statistics.mean(send_times):.3f}s")
    print(f"   Median:  {statistics.median(send_times):.3f}s")
    print(f"   Std Dev: {statistics.stdev(send_times):.3f}s")
    print(f"   Range:   {min(send_times):.3f}s - {max(send_times):.3f}s")
    
    plt.show()

def print_statistical_analysis(interrupt_data: Dict[int, List[float]], 
                              send_data: Dict[int, List[float]]):
    """Print detailed statistical analysis."""
    print("\n📈 STATISTICAL ANALYSIS")
    print("=" * 50)
    
    print("\n🛑 INTERRUPT TIMING ANALYSIS:")
    print("-" * 30)
    for agents in sorted(interrupt_data.keys()):
        times = interrupt_data[agents]
        print(f"  {agents} agents:")
        print(f"    Average: {statistics.mean(times):.3f}s")
        print(f"    Median:  {statistics.median(times):.3f}s")
        print(f"    Std Dev: {statistics.stdev(times) if len(times) > 1 else 0:.3f}s")
        print(f"    Min:     {min(times):.3f}s")
        print(f"    Max:     {max(times):.3f}s")
        print()
    
    print("📤 SEND MESSAGE TIMING ANALYSIS:")
    print("-" * 30)
    for agents in sorted(send_data.keys()):
        times = send_data[agents]
        print(f"  {agents} agents:")
        print(f"    Average: {statistics.mean(times):.3f}s")
        print(f"    Median:  {statistics.median(times):.3f}s")
        print(f"    Std Dev: {statistics.stdev(times) if len(times) > 1 else 0:.3f}s")
        print(f"    Min:     {min(times):.3f}s")
        print(f"    Max:     {max(times):.3f}s")
        print()
    
    # Performance scaling analysis
    if len(interrupt_data) > 1 and len(send_data) > 1:
        print("🔍 SCALING ANALYSIS:")
        print("-" * 30)
        interrupt_means = {agents: statistics.mean(interrupt_data[agents]) for agents in sorted(interrupt_data.keys())}
        send_means = {agents: statistics.mean(send_data[agents]) for agents in sorted(send_data.keys())}
        
        print("Interrupt time scaling:")
        for i, agents in enumerate(sorted(interrupt_means.keys())[1:], 1):
            prev_agents = sorted(interrupt_means.keys())[i-1]
            ratio = interrupt_means[agents] / interrupt_means[prev_agents]
            print(f"  {prev_agents} → {agents} agents: {ratio:.2f}x slower")
        
        print("\nSend message time scaling:")
        for i, agents in enumerate(sorted(send_means.keys())[1:], 1):
            prev_agents = sorted(send_means.keys())[i-1]
            ratio = send_means[agents] / send_means[prev_agents]
            print(f"  {prev_agents} → {agents} agents: {ratio:.2f}x slower")

if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# === 1. Load your CSV ===
df = pd.read_csv("oe_threads_data.csv")

# Remove 32-thread rows
df = df[df['api_workers'] != 32]

# === 2. Compute MQ+OE overhead ===
df['mq_oe_overhead'] = df['mq_avg'] + df['oe_avg'] - df['oe_internal_avg_ms']

# === 3. Get unique OE workers and API threads ===
oe_workers = sorted(df['oe_workers'].unique())
api_threads = sorted(df['api_workers'].unique())

# === 4. Prepare data arrays for plotting ===
sc_avg = np.zeros((len(oe_workers), len(api_threads)))
deploy_avg = np.zeros_like(sc_avg)
oe_internal_avg = np.zeros_like(sc_avg)
mq_oe_overhead = np.zeros_like(sc_avg)
throughput = np.zeros_like(sc_avg)

for i, oe in enumerate(oe_workers):
    for j, th in enumerate(api_threads):
        row = df[(df['oe_workers'] == oe) & (df['api_workers'] == th)]
        if not row.empty:
            sc_avg[i,j] = row['sc_avg'].values[0]
            deploy_avg[i,j] = row['deploy_avg'].values[0]
            oe_internal_avg[i,j] = row['oe_internal_avg_ms'].values[0]
            mq_oe_overhead[i,j] = row['mq_oe_overhead'].values[0]
            throughput[i,j] = row['throughput'].values[0]

# === 5. Plot grouped stacked bars ===
bar_width = 0.15
x = np.arange(len(oe_workers))

fig, ax = plt.subplots(figsize=(16,8))

colors = {
    'sc': '#1f77b4',
    'deploy': '#ff7f0e',
    'oe_internal': '#2ca02c',
    'mq_oe': '#d62728'
}

for j, th in enumerate(api_threads):
    bottom = np.zeros(len(oe_workers))
    ax.bar(x + j*bar_width, sc_avg[:,j], width=bar_width, bottom=bottom, color=colors['sc'])
    bottom += sc_avg[:,j]
    ax.bar(x + j*bar_width, deploy_avg[:,j], width=bar_width, bottom=bottom, color=colors['deploy'])
    bottom += deploy_avg[:,j]
    ax.bar(x + j*bar_width, oe_internal_avg[:,j], width=bar_width, bottom=bottom, color=colors['oe_internal'])
    bottom += oe_internal_avg[:,j]
    ax.bar(x + j*bar_width, mq_oe_overhead[:,j], width=bar_width, bottom=bottom, color=colors['mq_oe'])

    
    # Add throughput labels on top of each bar
    for xi, thp in zip(x + j*bar_width, throughput[:,j]):
        ax.text(xi, bottom[np.where(x + j*bar_width == xi)][0] + 15, f"{thp:.1f} req/sec", ha='center', va='center', fontsize=13, rotation=90,color="black")
        #ax.text(xi, 150, f"{thp:.1f} req/sec", ha='center', va='center', fontsize=13, rotation=90,color="orange")

# === 6. Labels, grid, and legends ===
ax.set_xticks(x + bar_width*(len(api_threads)-1)/2)
ax.set_xticklabels(oe_workers)
ax.set_xlabel("OE Workers")
ax.set_ylabel("Latency (ms)")
ax.set_title("Latency Breakdown with MQ+OE Overhead and Throughput Labels")
ax.grid(True, axis='y', linestyle='--', alpha=0.7)

# Legends
latency_legend = ax.legend(['Service Catalog', 'Service Orchestrator Deploy to IML', 'Optimization Engine', 'Message Queue'], loc='upper left', bbox_to_anchor=(0,1))
ax.add_artist(latency_legend)

#throughput_legend = ax.legend([f"Threads {th}" for th in api_threads], title="API Threads", loc='upper right', bbox_to_anchor=(1,1))
#ax.add_artist(throughput_legend)

plt.tight_layout()
plt.savefig("scalability-all.png")

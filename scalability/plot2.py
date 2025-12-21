import matplotlib.pyplot as plt
import numpy as np

# X-axis
threads = np.array([1, 2, 4, 8, 16, 32])
x = np.arange(len(threads))

# Throughput (req/s)
throughput = np.array([
    24.27, 45.35, 56.30, 55.84, 56.12, 56.21
])

# ---- Latency (ms) ----
min_lat = np.array([35.84, 36.51, 43.30, 45.26, 45.27, 55.87])
avg_lat = np.array([41.04, 43.92, 70.81, 142.83, 283.88, 564.64])
max_lat = np.array([54.25, 105.41, 94.72, 207.34, 341.23, 690.64])

lat_err = np.vstack([
    avg_lat - min_lat,
    max_lat - avg_lat
])

# ---- CPU components (%) ----
oe_cpu = np.array([4.53, 6.76, 6.65, 6.70, 6.70, 6.80])
rabbitmq_cpu = np.array([1.26, 2.05, 1.43, 1.39, 1.61, 1.54])
orchestrator_cpu = np.array([9.52, 13.30, 13.90, 19.50, 15.15, 17.44])
catalog_cpu = np.array([1.50, 2.17, 2.00, 1.88, 1.97, 1.82])
topology_cpu = np.array([2.94, 4.13, 4.36, 4.58, 4.50, 4.37])

# ---- Plot ----
fig, ax1 = plt.subplots(figsize=(10, 5))

bottom = np.zeros(len(threads))

ax1.bar(x, oe_cpu, label="Optimization Engine", bottom=bottom)
bottom += oe_cpu

ax1.bar(x, rabbitmq_cpu, label="Message Queue", bottom=bottom)
bottom += rabbitmq_cpu

ax1.bar(x, orchestrator_cpu, label="Service Orchestrator", bottom=bottom)
bottom += orchestrator_cpu

ax1.bar(x, catalog_cpu, label="Service Catalog", bottom=bottom)
bottom += catalog_cpu

ax1.bar(x, topology_cpu, label="Topology", bottom=bottom)
bottom += topology_cpu

ax1.set_xlabel("Number of threads")
ax1.set_ylabel("CPU utilization (%)")
ax1.set_xticks(x)
ax1.set_xticklabels(threads)
ax1.grid(True, axis="y")

# ---- Throughput labels ----
for i, (cpu_total, tput) in enumerate(zip(bottom, throughput)):
    ax1.text(
        x[i],
        cpu_total + 0.5,          # small offset above bar
        f"{tput:.1f} req/s",
        ha="center",
        va="bottom",
        fontsize=11,
        rotation=0
    )

# ---- Latency axis ----
ax2 = ax1.twinx()
ax2.errorbar(
    x,
    avg_lat,
    yerr=lat_err,
    fmt="o-",
    linewidth=3,
    capsize=5,
    label="Avg latency (min–max)", color="black"
)
ax2.set_ylabel("Latency (ms)")

# ---- Legend ----
handles1, labels1 = ax1.get_legend_handles_labels()
handles2, labels2 = ax2.get_legend_handles_labels()

handles1, labels1 = ax1.get_legend_handles_labels()
handles2, labels2 = ax2.get_legend_handles_labels()


ax1.legend(
    handles1 + handles2,
    labels1 + labels2,
    loc="lower center",
    bbox_to_anchor=(0.5, 1.02),
    ncol=3
)

plt.subplots_adjust(right=0.75)

plt.tight_layout()
plt.savefig("scalability-threads.png")

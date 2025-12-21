import matplotlib.pyplot as plt
import numpy as np

# X-axis
oe_workers = np.array([1, 2, 4, 8, 16, 32])
x = np.arange(len(oe_workers))

# ---- Average latency components (ms) ----
sc_avg = np.array([2.57, 3.08, 4.83, 6.63, 8.17, 7.73])
deploy_avg = np.array([11.43, 15.80, 29.91, 57.30, 60.79, 57.24])

mq_avg = np.array([537.75, 310.18, 207.32, 142.97, 136.30, 128.33])
oe_avg = np.array([9.76, 11.25, 15.32, 21.06, 24.06, 23.31])
oe_internal_avg = np.array([10.75, 12.28, 16.34, 20.95, 20.89, 20.24])

# ---- Derived metric ----
mq_oe_overhead = mq_avg + oe_avg - oe_internal_avg

# ---- Plot ----
fig, ax = plt.subplots(figsize=(10, 5))

bottom = np.zeros(len(oe_workers))

ax.bar(x, sc_avg, label="SC", bottom=bottom)
bottom += sc_avg

ax.bar(x, deploy_avg, label="Deploy", bottom=bottom)
bottom += deploy_avg

ax.bar(x, oe_internal_avg, label="OE (internal)", bottom=bottom)
bottom += oe_internal_avg

ax.bar(
    x,
    mq_oe_overhead,
    label="MQ + OE overhead",
    bottom=bottom
)
bottom += mq_oe_overhead

# ---- Axes ----
ax.set_xlabel("Number of OE workers")
ax.set_ylabel("Average latency (ms)")
ax.set_xticks(x)
ax.set_xticklabels(oe_workers)
ax.grid(True, axis="y")

# ---- Total latency labels ----
for i, total in enumerate(bottom):
    ax.text(
        x[i],
        total + 10,
        f"{total:.0f} ms",
        ha="center",
        va="bottom",
        fontsize=9
    )

# ---- Legend outside ----
ax.legend(
    loc="center left",
    bbox_to_anchor=(1.02, 0.5),
    frameon=False
)

plt.subplots_adjust(right=0.75)
plt.tight_layout()
plt.savefig("scalability-latency.png")


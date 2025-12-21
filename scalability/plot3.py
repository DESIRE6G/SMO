import matplotlib.pyplot as plt
import numpy as np

# X-axis
threads = np.array([1, 2, 4, 8, 16, 32])
x = np.arange(len(threads))

# ---- Average latency components (ms) ----
sc_avg = np.array([2.41, 2.53, 2.57, 2.59, 2.55, 2.57])
deploy_avg = np.array([10.54, 11.25, 11.47, 11.48, 11.47, 11.43])

mq_avg = np.array([16.98, 18.13, 44.06, 115.96, 257.08, 537.75])
oe_avg = np.array([8.40, 9.15, 9.71, 9.76, 9.75, 9.76])
oe_internal_avg = np.array([9.91, 10.16, 10.44, 10.61, 10.69, 10.75])

# ---- Derived metric ----
mq_oe_overhead = mq_avg + oe_avg - oe_internal_avg

# ---- Plot ----
fig, ax = plt.subplots(figsize=(10, 5))

bottom = np.zeros(len(threads))

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
ax.set_xlabel("Number of threads")
ax.set_ylabel("Average latency (ms)")
ax.set_xticks(x)
ax.set_xticklabels(threads)
ax.grid(True, axis="y")

# ---- Total latency labels ----
for i, total in enumerate(bottom):
    ax.text(
        x[i],
        total + 5,
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
plt.savefig("scalability-cpu.png")

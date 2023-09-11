# Use https://www.xiconeditor.com to convert to ico
import matplotlib.pyplot as plt
import matplotlib as mp
import numpy as np

fig = plt.figure(frameon=False)
fig.set_size_inches(2, 2)
ax = plt.Axes(fig, [0, 0, 1, 1])
ax.set_axis_off()
fig.add_axes(ax)

t = np.arange(-6, 6, 0.001)
i = 6
x = np.cos(t*1) * np.exp(-(t**2)/4)
o = np.exp(-i/10)
shift = 0
ax.fill_between(t+shift, x*o + 0.2, color='midnightblue')
ax.fill_between(t+shift, x*o + 0.2, 1, color='cornflowerblue')
ax.plot(t+shift, x*o + 0.2, color='white', lw=3)

ax.axis(xmin=-5, xmax=5, ymin=0, ymax=1)

patch = mp.patches.Rectangle([0, 0], width=1, height=1, facecolor='none',
                             edgecolor='white', linewidth=10,
                             transform=ax.transAxes)
ax.add_patch(patch)

fig.savefig('abr.png')
plt.show()

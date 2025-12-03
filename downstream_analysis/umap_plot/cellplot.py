import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib import gridspec
import numpy as np

class CellPlot:
    #----------------------------------------------------------------------------
    # Plot functions
    
    def hist(self, xname, population=None, title='', xlabel='', ylabel='', show_inset=True, figsize=(4, 4), fontsize=9, population_name='Total', color='blue', xlim=(-0.05, 1.05)):
        if population is None:
            data_plot = self.data_all
        else:
            data_plot = population

        if isinstance(xname, str):
            x = [d[xname] for d in data_plot]
        elif isinstance(xname, list):
            x = [sum(d[key] for key in xname) for d in data_plot]
        else:
            raise ValueError('xname type error')

        fig, ax = plt.subplots(figsize=figsize)
        ax.hist(x, bins=200, label='debris', color=color)

        ax.set_xlim(xlim)

        if xlabel == '':
            xlabel = f'Probability - {xname}'
        if ylabel == '':
            ylabel = 'Frequency'

        ax.set_title(title, fontsize=fontsize+4)
        ax.set_xlabel(xlabel, fontsize=fontsize+4)
        ax.set_ylabel(ylabel, fontsize=fontsize+4)
        ax.tick_params(labelsize=fontsize)

        if show_inset:
            ax_inset = inset_axes(ax, width="50%", height="50%", loc='upper right', borderpad=0)
            ax_inset.margins(0)
            data_inset = [valx for valx in x if valx > 0.5]
            ax_inset.hist(data_inset, bins=200, alpha=0.5, color=color)
            ax_inset.set_xlim((xlim[0]+xlim[1])/2, xlim[1])

            ax_inset.grid(True)
            self.ax_inset = ax_inset

        self.total_count = len(x)
        textstr = f'{population_name}: {self.total_count:,}'
        ax.text(0, 1.02, textstr, transform=ax.transAxes, fontsize=fontsize, verticalalignment='bottom', horizontalalignment='left')

        self.fig = fig
        self.ax = ax
        self.gated_count = None
        self.hist_inset = show_inset
        self.data_plot = data_plot
        self.x = x

        return fig, ax
    

    def generate_nice_ticks(self, vmin, vmax, max_ticks=5):
        data_range = vmax - vmin
        if data_range <= 0:
            return [vmin]

        raw_step = data_range / (max_ticks - 1)
        base = 10 ** int(np.floor(np.log10(raw_step)))

        for step in [1, 2, 5, 10]:
            tick_step = step * base
            vmax_rounded = np.floor(vmax / tick_step) * tick_step
            ticks = np.arange(0, vmax_rounded + tick_step, tick_step)
            if len(ticks) <= max_ticks:
                return ticks.tolist()

        return ticks.tolist()

    

    def scatter(self, xname, yname, population=None, xlabel=None, ylabel=None, title="Scatter plot", colormap='r', figsize=(4, 4), fontsize=9, population_name='Total', xlim=(-0.05, 1.05), ylim=(-0.05, 1.05)):
        if population is None:
            data_plot = self.data_all
        else:
            data_plot = population

        if isinstance(xname, str):
            x = [d[xname] for d in data_plot]
        elif isinstance(xname, list):
            x = [sum(d[key] for key in xname) for d in data_plot]
        else:
            raise ValueError('xname should be defined.')

        if isinstance(yname, str):
            y = [d[yname] for d in data_plot]
        elif isinstance(yname, list):
            y = [sum(d[key] for key in yname) for d in data_plot]
        else:
            raise ValueError('yname should be defined.')

        x = np.array(x)
        y = np.array(y)

        H, xedges, yedges = np.histogram2d(x, y, bins=200)

        xcenters = (xedges[:-1] + xedges[1:]) / 2
        ycenters = (yedges[:-1] + yedges[1:]) / 2
        X, Y = np.meshgrid(xcenters, ycenters)

        threshold = 2

        low_density_x = []
        low_density_y = []

        for i in range(len(xedges) - 1):
            for j in range(len(yedges) - 1):
                if H[i, j] < threshold:
                    mask = (x >= xedges[i]) & (x < xedges[i + 1]) & (y >= yedges[j]) & (y < yedges[j + 1])
                    low_density_x.extend(x[mask])
                    low_density_y.extend(y[mask])

        fig = plt.figure(figsize=figsize)
        gs = gridspec.GridSpec(1, 1, left=0, right=0.9, top=1, bottom=0, hspace=0, wspace=0)

        ax = fig.add_subplot(gs[0])
        cax = fig.add_axes([0.95, 0.1, 0.05, 0.9])    # left, bottom, width, height
        
        if xlim is not None:
            ax.set_xlim(xlim)
        if ylim is not None:
            ax.set_ylim(ylim)

        pcol = 'grey'
        if colormap == 'r':
            colors = plt.cm.rainbow(np.linspace(0, 1, 256))
        elif colormap == 'gi':
            colors = plt.cm.gray(np.linspace(0.4, 0.9, 256))
            pcol = '#404040'
        elif colormap == 'g':
            colors = plt.cm.gray(np.linspace(0.4, 0, 256))
        else:
            raise ValueError('colormap should be defined.')

        colors = np.vstack((np.array([1, 1, 1, 1]), colors))
        custom_cmap = ListedColormap(colors)
        levels = np.linspace(0, H.max(), len(colors))
        norm = BoundaryNorm(boundaries=levels, ncolors=len(colors), clip=True)

        H_adjusted = np.copy(H)
        H_adjusted[H < threshold] = np.nan 
        contourf = ax.contourf(X, Y, H_adjusted.T, levels=levels, cmap=custom_cmap, norm=norm)

        cb = fig.colorbar(contourf, cax=cax, orientation='vertical')
        vmin, vmax = contourf.get_clim()
        nice_ticks = self.generate_nice_ticks(vmin, vmax, max_ticks=5)
        cb.set_ticks(nice_ticks)
        cb.ax.text(0, 1, "Density", fontsize=fontsize+4, rotation=0, transform=cb.ax.transAxes, va='bottom', ha='left')
        cb.ax.tick_params(labelsize=fontsize)
        cb.ax.minorticks_off()

        scatter = ax.scatter(low_density_x, low_density_y, c=pcol, s=0.5, label='Outliers')

        if xlabel is None:
            xlabel = xname
        if ylabel is None:
            ylabel = yname
        ax.set_title(title, fontsize=fontsize+4)
        ax.set_xlabel(xlabel, fontsize=fontsize+4)
        ax.set_ylabel(ylabel, fontsize=fontsize+4)
        ax.tick_params(labelsize=fontsize)

        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc='lower left', bbox_to_anchor=(0.99, -0.03), fontsize=fontsize, frameon=False, handletextpad=0)

        self.total_count = len(x)
        textstr = f'{population_name}: {self.total_count:,}'
        ax.text(0, 1.02, textstr, transform=ax.transAxes, fontsize=fontsize+4, verticalalignment='bottom', horizontalalignment='left')

        self.fig = fig
        self.ax = ax
        self.data_plot = data_plot
        self.x = x
        self.y = y

        return fig, ax


    #----------------------------------------------------------------------------
    # Gate functions
    
    def gate_linear(self, threshold, color = 'red', draw_text = True, name = '', fontsize=9, linepos=0.2):

        # Gating
        data_gated = [item for item, valx in zip(self.data_plot, self.x) if valx > threshold[0] and valx < threshold[1]]
        gated_count = len(data_gated)
        gated_percentage = gated_count / self.total_count * 100

        # Draw threshold range
        y_middle = (1-linepos) * self.ax.get_ylim()[0] + linepos * self.ax.get_ylim()[1] 
        self.ax.hlines(y=y_middle, xmin=threshold[0], xmax=threshold[1], color=color, linestyle='-', linewidth=1)
        self.ax.vlines(x=threshold[0], ymin=y_middle*0.9, ymax=y_middle*1.1, color=color, linestyle='-', linewidth=1)
        self.ax.vlines(x=threshold[1], ymin=y_middle*0.9, ymax=y_middle*1.1, color=color, linestyle='-', linewidth=1)
        
        # Draw text: name and count
        if draw_text:
            textstr = f'{name}\n{gated_count:,} ({gated_percentage:.1f}%)'
            self.ax.text(threshold[1], y_middle*1.1, textstr, fontsize=fontsize, verticalalignment='bottom', horizontalalignment='right', color=color)

        if self.hist_inset:
            y_middle_inset = 0.5 * self.ax_inset.get_ylim()[0] + 0.5 * self.ax_inset.get_ylim()[1]  # 子プロットのY軸の中央
            self.ax_inset.hlines(y=y_middle_inset, xmin=threshold[0], xmax=threshold[1], color=color, linestyle='-', linewidth=1)
            self.ax_inset.vlines(x=threshold[0], ymin=y_middle_inset*0.9, ymax=y_middle_inset*1.1, color=color, linestyle='-', linewidth=1)
            self.ax_inset.vlines(x=threshold[1], ymin=y_middle_inset*0.9, ymax=y_middle_inset*1.1, color=color, linestyle='-', linewidth=1)

        return {
            'data': data_gated,
            'name': name,
            'count': gated_count,
            'percentage': gated_percentage
        }
        

    def gate_rectangle(self, roi, color = 'red', text = True, textpos = 'c', name = '', fontsize=9):

        # Gating
        (x1, x2), (y1, y2) = roi
        xmin, xmax = min(x1, x2), max(x1, x2)
        ymin, ymax = min(y1, y2), max(y1, y2)
        data_gated = [item for item, valx, valy in zip(self.data_plot, self.x, self.y) if valx > xmin and valx < xmax and valy > ymin and valy < ymax] 
        gated_count = len(data_gated)
        gated_percentage = gated_count / self.total_count * 100

        # Draw ROI
        rect = plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, linewidth=1,edgecolor=color, facecolor='none')
        self.ax.add_patch(rect)

        # Draw text: name and count
        if text:
            textstr = f'{name}\n{gated_count:,}\n({gated_percentage:.1f}%)'
            if textpos == 'c':
                posx, posy = (xmin+xmax)/2, (ymin+ymax)/2
                va, ha = 'center', 'center'
            elif textpos == 'r':
                posx, posy = xmax*1.05, (ymin+ymax)/2
                va, ha = 'center', 'left'
            elif textpos == 'l':
                posx, posy = xmin*0.95, (ymin+ymax)/2
                va, ha = 'center', 'right'

            self.ax.text(posx, posy, textstr, fontsize=fontsize, verticalalignment=va, horizontalalignment=ha, color=color)

        return {
            'data': data_gated,
            'name': name,
            'count': gated_count,
            'percentage': gated_percentage
        }
    


    #----------------------------------------------------------------------------
    # Plot formatting functions
    
    def put_count(self, fontsize=9):
        if self.gated_count is not None:
            textstr = '\n'.join((
                f'Total: {self.total_count}',
                f'Gated: {self.gated_count}'
            ))
        else:
            textstr = f'Total: {self.total_count}'

        self.ax.text(-0.1, 1.1, textstr, transform=self.ax.transAxes, fontsize=fontsize, verticalalignment='top')

        return

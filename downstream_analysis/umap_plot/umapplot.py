import matplotlib.pyplot as plt
import numpy as np


classlist = ['Leu', 'Glan', 'Squ.epi', 'Squ.meta', 'Debris', 'Para.Squ', 'Para.Clust', 'LSIL', 'HSIL', 'Adenocarcinoma']

class_to_color_base = {
    'Squ.epi' : plt.cm.tab20(0),
    'Para.Squ' : plt.cm.tab20(4),
    'Squ.meta' : plt.cm.tab20(16),
    'Glan' : plt.cm.tab20(8),
    'Para.Clust' : plt.cm.tab20(5),
    'LSIL' : plt.cm.tab20(2),
    'HSIL' : plt.cm.tab20(6),
    'Adenocarcinoma' : plt.cm.tab20(12)
    }

class_to_color_mono = {
    'Squ.epi' : plt.cm.Greys(0.3),
    'Para.Squ' : plt.cm.Greys(0.3),
    'Squ.meta' : plt.cm.Greys(0.3),
    'Glan' : plt.cm.Greys(0.3),
    'Para.Clust' : plt.cm.Greys(0.3),
    'LSIL' : plt.cm.tab20(2),
    'HSIL' : plt.cm.tab20(6),
    'Adenocarcinoma' : plt.cm.tab20(12)
    }

class_to_label = {
    'Squ.epi' : 'Superficial/intermediate cell',
    'Para.Squ' : 'Parabasal cell',
    'Squ.meta' : 'Squamous metaplasia',
    'Glan' : 'Glandular cell',
    'Para.Clust' : 'Miscellaneous cell cluster',
    'LSIL' : 'LSIL',
    'HSIL' : 'HSIL',
    'Adenocarcinoma' : 'Adenocarcinoma',
    }


def plot_umap(ax, df, show_legend=True, show_axis=False, show_axis_label=True, alpha_zero=0.2, mono_color=False, weighted_alpha=True, size_highlight=[], dotsize=[1,3]):

    class_labels = df['class_label']
    class_probs = df['class_value']

    if mono_color:
        class_to_color = class_to_color_mono
    else:
        class_to_color = class_to_color_base
    prob_lim = [2, 6]
    if weighted_alpha:
        class_alpha = [alpha_zero + (1-alpha_zero)*(pr-prob_lim[0])/(prob_lim[1]-prob_lim[0]) for pr in class_probs]
        class_alpha = [min(max(x, alpha_zero), 1) for x in class_alpha]
    else:
        class_alpha = [1] * len(class_labels)
    class_indices = np.array([[*class_to_color[cls][:3], alpha] for cls, alpha in zip(class_labels, class_alpha)])
    size = [dotsize[1] if classname in size_highlight else dotsize[0] for classname in class_labels]

    # Plot
    ax.scatter(df['umap1'], df['umap2'], c=class_indices, s=size, edgecolor='none')
    for highlight_class in size_highlight:
        highlight_indices = df['class_label'] == highlight_class
        ax.scatter(df.loc[highlight_indices, 'umap1'], df.loc[highlight_indices, 'umap2'], 
                   c=class_to_color[highlight_class][:3], s=dotsize[1], edgecolor='none')

    if show_legend:
        for cls in class_to_color.keys():
            ax.scatter([], [], c=class_to_color[cls], label=class_to_label[cls], s=30)
        ax.legend(bbox_to_anchor=(0.9, 0.5), loc='center left', frameon=False, fontsize=10, handletextpad=0)

    # Axis settings
    if show_axis_label:
        ax.set_xlabel('UMAP1')
        ax.set_ylabel('UMAP2')
    else:
        ax.set_xlabel('')
        ax.set_ylabel('')
    if show_axis:
        ax.grid(True, which='both', axis='both', linestyle='--', linewidth=0.5)
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(show_axis)

    plt.tight_layout()


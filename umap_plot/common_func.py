import matplotlib.pyplot as plt
import numpy as np
import csv
import cv2


# class configurations
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


def plot_umap(ax, df, show_legend=True, show_axis=False, alpha_zero=0.2, mono_color=False, weighted_alpha=True, size_highlight=[], dotsize=[1,3]):
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

    # UMAP plotting
    ax.scatter(df['umap1'], df['umap2'], c=class_indices, s=size, edgecolor='none')
    for highlight_class in size_highlight:
        highlight_indices = df['class_label'] == highlight_class
        ax.scatter(df.loc[highlight_indices, 'umap1'], df.loc[highlight_indices, 'umap2'], 
                   c=class_to_color[highlight_class][:3], s=dotsize[1], edgecolor='none')

    # legend
    if show_legend:
        for cls in class_to_color.keys():
            ax.scatter([], [], c=class_to_color[cls], label=class_to_label[cls], s=30)
        ax.legend(bbox_to_anchor=(0.9, 0.5), loc='center left', frameon=False, fontsize=10, handletextpad=0)

    # axis settings
    ax.set_xlabel('UMAP1')
    ax.set_ylabel('UMAP2')
    if show_axis:
        ax.grid(True, which='both', axis='both', linestyle='--', linewidth=0.5)
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(show_axis)

    plt.tight_layout()


def show_selected_images(imagelist, selected_id, filepath, tilesize=224, margin=5, ncols=2, nrows=2, drawscale=True):
    if len(selected_id) != nrows * ncols:
        raise ValueError(f"Selected ID length {len(selected_id)} does not match grid size {nrows}x{ncols}.")

    selected_images = [img for i, img in enumerate(imagelist) if i in selected_id]
    imageheight = (tilesize + margin) * nrows - margin
    imagewidth = (tilesize + margin) * ncols - margin 
    image = np.ones((imageheight, imagewidth, 3), dtype=np.uint8) * 255

    for c in range(ncols):
        for r in range(nrows):
            idx = c * nrows + r
            if idx < len(imagelist):
                img = selected_images[idx]
                y0 = r * (tilesize + margin)
                x0 = c * (tilesize + margin)
                image[y0:y0+tilesize, x0:x0+tilesize] = img

    if drawscale:
        mmpp = 0.218
        scale_length = 20 / mmpp
        scale_x1 = imagewidth - 10
        scale_y1 = imageheight - 15
        scale_x0 = scale_x1 - int(scale_length)
        scale_y0 = scale_y1 + 10
        cv2.rectangle(image, (scale_x0, scale_y0), (scale_x1, scale_y1), (0, 0, 0), thickness=cv2.FILLED)

    plt.imshow(image)
    plt.axis('off')
    plt.tight_layout
    plt.show()
    cv2.imwrite(filepath, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))


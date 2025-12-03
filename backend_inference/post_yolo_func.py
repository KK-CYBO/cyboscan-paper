import numpy as np
import torch
import faiss


class PostYoloFunc:
    def group_rois_faiss(self, nuclei_list, k=10, z_scale=0.2, distance_threshold=6):
        """
        nuclei_list: List of nuclei dictionaries
            Ex. [ {'z': 0, 'x': 3203, 'y': 3338, 'w': 31, 'h': 30, 'confidence': 0.5953096},
                {'z': 0, 'x': 2480, 'y': 2731, 'w': 21, 'h': 20, 'confidence': 0.51541597},
                    :
                ]
        k: Number of nearest neighbors to search
        z_scale: Z scaling factor
        distance_threshold: Euclidean distance threshold for clustering
        """

        points = []
        rois = []

        for roi in nuclei_list:
            x = roi["x"]
            y = roi["y"]
            z = roi["z"] * z_scale
            points.append([x, y, z])
            rois.append((x, y, roi["w"], roi["h"], roi["z"], roi["confidence"]))

        points_np = np.array(points).astype("float32")

        index = faiss.IndexFlatL2(3)
        index.add(points_np)

        distances, indices = index.search(points_np, k)

        class UnionFind:
            def __init__(self, size):
                self.parent = list(range(size))

            def find(self, x):
                if self.parent[x] != x:
                    self.parent[x] = self.find(self.parent[x])
                return self.parent[x]

            def union(self, x, y):
                self.parent[self.find(x)] = self.find(y)

        uf = UnionFind(len(points_np))

        for i in range(len(points_np)):
            for j, d in zip(indices[i], distances[i]):
                if i != j and d < distance_threshold**2:
                    uf.union(i, j)

        from collections import defaultdict

        groups = defaultdict(list)
        for i, roi in enumerate(rois):
            root = uf.find(i)
            groups[root].append(roi)

        clustered_rois = list(groups.values())

        return clustered_rois

    def select_focused_ROI_GPU(self, roi_groups, imstack, zrange=(5, 25), offset=10):
        """
        roi_groups: A list of ROI groups
        imstack: Z-stack image (torch tensor)
        zrange: Z-stack range to search best focused plane
        offset: Offset around ROI
        """

        nuc_focused = []
        for roi_group in roi_groups:
            if len(roi_group) < 2:
                continue

            x1 = min([int(a[0]) for a in roi_group]) - offset
            y1 = min([int(a[1]) for a in roi_group]) - offset
            x2 = max([int(a[0] + a[2]) for a in roi_group]) + offset
            y2 = max([int(a[1] + a[3]) for a in roi_group]) + offset
            zs = [a[4] for a in roi_group]
            zmin = min(zs)
            zmax = max(zs)

            vals = []
            for z in zrange:
                if zmin <= z <= zmax:
                    image = imstack[z]
                    imh, imw = image.shape
                    x1 = max(x1, 0)
                    y1 = max(y1, 0)
                    x2 = min(x2, imw)
                    y2 = min(y2, imh)
                    imcrop = image[..., y1:y2, x1:x2]
                    val = torch.std(imcrop)
                    vals.append(val.item())
                else:
                    vals.append(0)

            if len(vals) > 0:
                # Select the best focus image
                zpeak = zrange[0] + torch.argmax(torch.tensor(vals)).item()
                nuc_focused.append([zpeak, x1, y1, x2, y2])

        return nuc_focused

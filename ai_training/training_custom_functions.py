import torch
from torch.utils.data import Dataset
import lmdb
import numpy as np
import pickle
import cv2
import random
import os
import albumentations


def seed_torch(seed=516):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True


#----------------------------------------------------
# Dataset interface
#----------------------------------------------------

class LMDBdataset(Dataset):
    def __init__(self, lmdb_path, transform=None, mode="train", target_classlist=None):
        self.transform = transform
        self.mode = mode
        self.env = lmdb.open(lmdb_path, readonly=True, lock=False)
        with self.env.begin(write=False) as txn:
            self.src_classlist = pickle.loads(txn.get('classlist'.encode('utf-8')))

            if target_classlist is None:
                self.target_classlist = self.src_classlist
            else:
                self.target_classlist = list(target_classlist)

            # Name to target index mapping
            name_to_target = {name: i for i, name in enumerate(self.target_classlist)}
            self.name_to_target = {}
            for name in self.src_classlist:
                if name in name_to_target:
                    self.name_to_target[name] = name_to_target[name]
                else:
                    raise ValueError(f"[{lmdb_path}] class '{name}' not in target_classlist")

            self.classlist = self.target_classlist

            if mode == "train":
                self.num = int(txn.get('num-train'.encode('utf-8')))
                self.prefix = 't'
            elif mode == "valid":
                self.num = int(txn.get('num-val'.encode('utf-8')))
                self.prefix = 'v'
            else:
                raise ValueError(f"Unsupported mode: {mode}. Use 'train' or 'valid'.")
            
    def __len__(self):
        return self.num

    def __getitem__(self, idx):
        # データを読み込む
        with self.env.begin() as txn:
            imstream = txn.get(f'img-{self.prefix}{idx}'.encode("utf-8"))
            image = cv2.imdecode(np.frombuffer(imstream, dtype=np.uint8), cv2.IMREAD_COLOR)
            label_name = txn.get(f'class-{self.prefix}{idx}'.encode('utf-8')).decode('utf-8')

        # 変換を適用
        if self.transform:
            image = self.transform(image)
        
        image = torch.tensor(image, dtype=torch.float32).permute(2, 0, 1) / 255.0

        # convert label to tensor
        label = torch.tensor(self.name_to_target[label_name], dtype=torch.long)

        return image, label


class CustomTransform:
    def __init__(self, flip_rgb=False, coarse_dropout=False):
        self.coarse_dropout = coarse_dropout
        self.flip_rgb = flip_rgb

    def __call__(self, image):
        image = self.image_transform(image)
        if self.coarse_dropout:
            image = albumentations.CoarseDropout(num_holes_range=(1,10), hole_height_range=(2,4), hole_width_range=(2,10), p=0.5)(image=image)['image']
        return image

    def image_transform(self, image):
        flip_rgb = self.flip_rgb

        # BGR->RGB
        if flip_rgb:        
            image = image[:,:,(2,1,0)] # BGR -> RGB

        return image

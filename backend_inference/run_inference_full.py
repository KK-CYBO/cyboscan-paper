from findnuclei_yolox_batch import YoloConfig, FindNuclei
from cell_classify import CellClassifier, MaxVitConfig
from post_yolo_func import PostYoloFunc
import os
import csv
import numpy as np
import decord as de
import torch
import torch.nn.functional as F


class RunInference:
    def __init__(
        self,
        yolo_model_path,
        maxvit_model_path,
        classlist,
        gpu_device_id=0,
        gpu_mem_limit=10 * 1024 * 1024 * 1024,
    ):
        # Yolo config
        yoloconfig = YoloConfig(yolo_model_path)
        yoloconfig.target_size = 1024
        yoloconfig.score_thr = 0.1
        yoloconfig.nms_thr = 0.2
        yoloconfig.input_name = "input"
        yoloconfig.gpu_device_id = gpu_device_id
        yoloconfig.gpu_mem_limit = gpu_mem_limit
        self.yoloconfig = yoloconfig

        # Postyolo config
        self.postyolo_skip = 4

        # Maxvit config
        maxvitconfig = MaxVitConfig(maxvit_model_path)
        maxvitconfig.label_names = classlist
        maxvitconfig.crop_size = 224
        maxvitconfig.batch_size = 8
        maxvitconfig.gpu_device_id = gpu_device_id
        maxvitconfig.gpu_mem_limit = gpu_mem_limit
        self.maxvitconfig = maxvitconfig
        modelname = os.path.basename(maxvit_model_path).split(".")[0]
        exename = os.path.basename(os.path.dirname(maxvit_model_path))
        self.model_name = f"{exename}/{modelname}"
        self.classlist = classlist

        # System config
        self.gpu_device_id = gpu_device_id
        self.gpu_mem_limit = gpu_mem_limit
        self.output_csv_path = ""

    def prepare_csv(self):
        os.makedirs(os.path.dirname(self.output_csv_path), exist_ok=True)

        fixed_cols = ["slidenum", "spot", "cell", "z", "x1", "y1", "x2", "y2"]
        class_cols = self.classlist
        prob_cols = [f"{c}_prob" for c in self.classlist]
        header = fixed_cols + class_cols + prob_cols

        with open(self.output_csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)

    def append_csv(self, spot, results, imcrop_pos):
        # results: (N, num_classes) logits
        logits = results

        def scaled_sigmoid(x, k=1, s=0, a=1):
            return a / (a + np.exp(-k * (x - s)))

        sigmoid = np.vectorize(scaled_sigmoid)

        with open(self.output_csv_path, "a", newline="") as f:
            writer = csv.writer(f)

            slidenum = 0
            for cell, pos in enumerate(imcrop_pos):
                r = logits[cell]
                probs = sigmoid(r)

                row = [slidenum, spot, cell]
                row += list(pos)
                row += r.tolist()
                row += probs.tolist()
                writer.writerow(row)

    # ---------------------------------------------------------------------------------
    # Analysis
    # ---------------------------------------------------------------------------------

    def analyze_slide_gpu(self, input_video_path, output_csv_path, z_layers, num_tiles):
        fn = FindNuclei(self.yoloconfig)
        cc = CellClassifier(self.maxvitconfig)

        # Prepare to read mp4 file
        de.bridge.set_bridge("torch")

        if not os.path.exists(input_video_path):
            raise FileNotFoundError(f"File not found: {input_video_path}")

        print(f"[INFO] {output_csv_path} -- Processing file: {input_video_path}")

        self.output_csv_path = output_csv_path
        self.prepare_csv()

        vr = de.VideoReader(
            input_video_path, ctx=de.gpu(self.gpu_device_id), width=-1, height=-1
        )

        start_frame = -z_layers
        self.spotlist = []

        for spotnum in range(num_tiles):
            start_frame += z_layers
            frame_num = z_layers
            imstack_full = vr.get_batch(range(start_frame, start_frame + frame_num))
            _, original_h, original_w, _ = imstack_full.shape

            imstack_small = (
                imstack_full[:: self.postyolo_skip].float().permute(0, 3, 1, 2)
            )
            imstack_small = F.interpolate(
                imstack_small, size=(1024, 1024), mode="bilinear", align_corners=False
            )
            imstack_small = imstack_small.permute(0, 2, 3, 1).byte()

            # Find nuclei (YoloX)
            output = fn.run_gpu_batch(imstack_small, (original_h, original_w))

            # Post Yolo processing
            nuclei_list = []
            for z, tensor in enumerate(output):
                if tensor.shape[0] == 0:
                    continue

                np_tensor = tensor.cpu().numpy()
                x1, y1, x2, y2, conf = (
                    np_tensor[:, 0],
                    np_tensor[:, 1],
                    np_tensor[:, 2],
                    np_tensor[:, 3],
                    np_tensor[:, 4],
                )
                for i in range(len(x1)):
                    nuclei_list.append(
                        {
                            "z": z * self.postyolo_skip,
                            "x": x1[i],
                            "y": y1[i],
                            "w": x2[i] - x1[i],
                            "h": y2[i] - y1[i],
                            "confidence": conf[i],
                        }
                    )

            if len(nuclei_list) == 0:
                self.spotlist.append(0)
                continue

            postyolo = PostYoloFunc()
            nuc_groups = postyolo.group_rois_faiss(
                nuclei_list,
                k=10,
                z_scale=0.05 * self.postyolo_skip,
                distance_threshold=6,
            )

            imstack_b = imstack_full[..., 2].float()
            nuc_focused_list = postyolo.select_focused_ROI_GPU(
                nuc_groups, imstack_b, zrange=range(z_layers), offset=z_layers // 4
            )

            imcrop_pos = []
            for nuc in nuc_focused_list:
                z, x1, y1, x2, y2 = nuc
                x1 = (x1 + x2 - self.maxvitconfig.crop_size) // 2
                y1 = (y1 + y2 - self.maxvitconfig.crop_size) // 2
                x2 = x1 + self.maxvitconfig.crop_size
                y2 = y1 + self.maxvitconfig.crop_size

                if (
                    0 <= x1 < x2 <= imstack_full[z].shape[1]
                    and 0 <= y1 < y2 <= imstack_full[z].shape[0]
                ):
                    imcrop_pos.append((z, x1, y1, x2, y2))

            if not imcrop_pos:
                self.spotlist.append(0)
                continue

            imcrops_tensor = torch.stack(
                [imstack_full[z, y1:y2, x1:x2, :] for z, x1, y1, x2, y2 in imcrop_pos]
            )
            results = cc.run_inference_gpu(imcrops_tensor)

            imnum = len(imcrop_pos)
            self.append_csv(spotnum, results, imcrop_pos)
            self.spotlist.append(imnum)

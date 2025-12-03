import numpy as np
import onnxruntime
import torch
from torchvision.ops import batched_nms
import time


class YoloConfig:
    def __init__(self, model_path):
        """
        model_path: YOLOX model path (Ex. "/path/to/yolox_model.onnx")
        target_size: The size of the input image to be fed to the model (Ex. 1024)
        score_thr: The threshold for the confidence score (Ex. 0.1)
        nms_thr: The threshold for non-maximum suppression (Ex. 0.2)
        """
        self.model_path = model_path
        self.target_size = 1024
        self.score_thr = 0.1
        self.nms_thr = 0.2

        self.gpu_device_id = 0  # GPU device number
        self.gpu_device_type = "cuda"  # GPU device type
        self.gpu_mem_limit = (
            8 * 1024 * 1024 * 1024
        )  # GPU memory limit (For 8GB, set 8*1024*1024*1024)
        self.input_name = "images"
        self.output_name = "output"
        self.model_input_dtype = np.float32
        self.model_output_dtype = np.float32


class FindNuclei:
    """
    def __init__(self, onnx_model_path, target_size, score_thr=0.1, nms_thr=0.2):
        self.session = onnxruntime.InferenceSession(onnx_model_path, providers=['CUDAExecutionProvider'])
        self.target_size = target_size
        self.score_thr = score_thr
        self.nms_thr = nms_thr
    """

    def __init__(self, yoloconfig: YoloConfig):
        providers = [
            (
                "CUDAExecutionProvider",
                {
                    "device_id": yoloconfig.gpu_device_id,
                    "do_copy_in_default_stream": True,
                    "use_ep_level_unified_stream": True,
                    "arena_extend_strategy": "kNextPowerOfTwo",
                    "gpu_mem_limit": yoloconfig.gpu_mem_limit,
                },
            ),
            "CPUExecutionProvider",
        ]
        so = onnxruntime.SessionOptions()
        so.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_DISABLE_ALL
        so.intra_op_num_threads = 1
        so.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
        # ONNX runtime Session
        self.session = onnxruntime.InferenceSession(
            yoloconfig.model_path, providers=providers, sess_options=so
        )

        self.config = yoloconfig
        self.debug = False
        self.log = {"time_preparation": 0, "time_inference": 0, "time_postprocess": 0}

    def dtype_convert_np2torch(self, np_dtype):
        if np_dtype == np.float32:
            return torch.float32
        elif np_dtype == np.float16:
            return torch.float16
        elif np_dtype == np.float64:
            return torch.float64
        elif np_dtype == np.int32:
            return torch.int32
        elif np_dtype == np.int64:
            return torch.int64
        elif np_dtype == np.uint8:
            return torch.uint8
        else:
            return torch.uint8

    def batch_nms(self, boxes_xyxy, scores, score_thr, iou_thr):
        """
        Args:
            boxes_xyxy: (B, N, 4)
            scores: (B, N) or (B, N, num_classes)
            score_thr: Score threshold
            iou_thr: IoU threshold (default 0.5)

        Returns:
            List[Tensor] NMS results for each image (M_i, 6): [x1, y1, x2, y2, score, class]
        """
        B, N, _ = boxes_xyxy.shape
        results = []

        for b in range(B):
            boxes = boxes_xyxy[b]  # (N, 4)
            score = scores[b]  # (N,) or (N, num_classes)

            if score.ndim == 1:
                cls_scores = score
                cls_inds = torch.zeros_like(cls_scores, dtype=torch.int64)
            else:
                cls_scores, cls_inds = score.max(dim=-1)

            valid = cls_scores > score_thr
            if valid.sum() == 0:
                results.append(torch.empty((0, 6), device=boxes.device))
                continue

            boxes = boxes[valid]
            cls_scores = cls_scores[valid]
            cls_inds = cls_inds[valid]

            keep = batched_nms(boxes, cls_scores, cls_inds, iou_thr)
            final = torch.cat(
                [
                    boxes[keep],
                    cls_scores[keep].unsqueeze(1),
                    cls_inds[keep].unsqueeze(1).float(),
                ],
                dim=1,
            )  # (M, 6)

            results.append(final)

        return results

    def postprocess(self, outputs):
        target_size = self.config.target_size
        score_thr = self.config.score_thr

        img_size = (target_size, target_size)
        grids = []
        expanded_strides = []
        strides = [8, 16, 32]

        hsizes = [img_size[0] // stride for stride in strides]
        wsizes = [img_size[1] // stride for stride in strides]

        for hsize, wsize, stride in zip(hsizes, wsizes, strides):
            xv, yv = np.meshgrid(np.arange(wsize), np.arange(hsize))
            grid = np.stack((xv, yv), 2).reshape(1, -1, 2)
            grids.append(grid)
            shape = grid.shape[:2]
            expanded_strides.append(np.full((*shape, 1), stride))

        grids = np.concatenate(grids, 1)
        expanded_strides = np.concatenate(expanded_strides, 1)
        outputs[..., :2] = (outputs[..., :2] + grids) * expanded_strides
        outputs[..., 2:4] = np.exp(outputs[..., 2:4]) * expanded_strides

        predictions = outputs[0]

        boxes = predictions[:, :4]
        scores = predictions[:, 4:5] * predictions[:, 5:]

        boxes_xyxy = np.ones_like(boxes)
        boxes_xyxy[:, 0] = (
            (boxes[:, 0] - boxes[:, 2] / 2.0) * self.original_size[0] / target_size
        )
        boxes_xyxy[:, 1] = (
            (boxes[:, 1] - boxes[:, 3] / 2.0) * self.original_size[1] / target_size
        )
        boxes_xyxy[:, 2] = (
            (boxes[:, 0] + boxes[:, 2] / 2.0) * self.original_size[0] / target_size
        )
        boxes_xyxy[:, 3] = (
            (boxes[:, 1] + boxes[:, 3] / 2.0) * self.original_size[1] / target_size
        )

        cls_inds = scores.argmax(1)
        cls_scores = scores[np.arange(len(cls_inds)), cls_inds]

        valid_score_mask = cls_scores > score_thr
        if valid_score_mask.sum() > 0:
            valid_scores = cls_scores[valid_score_mask]
            valid_boxes = boxes_xyxy[valid_score_mask]
            valid_cls_inds = cls_inds[valid_score_mask]
            keep = self.nms(valid_boxes, valid_scores)
            if keep:
                dets = np.concatenate(
                    [
                        valid_boxes[keep],
                        valid_scores[keep, None],
                        valid_cls_inds[keep, None],
                    ],
                    1,
                )

                return dets
        return []

    def postprocess_batch(self, output_tensor):
        scale = torch.tensor(
            [
                self.original_size[1] / self.config.target_size,
                self.original_size[0] / self.config.target_size,
                self.original_size[1] / self.config.target_size,
                self.original_size[0] / self.config.target_size,
            ],
            device=output_tensor.device,
        )

        output_scaled = output_tensor[..., :4] * scale  # xywh
        xy = output_scaled[..., :2]
        wh = output_scaled[..., 2:]
        boxes_xyxy = torch.cat([xy - wh / 2, xy + wh / 2], dim=-1)

        # Standard YOLOX-style score: objectness * class score
        scores = output_tensor[..., 4] * output_tensor[..., 5]

        results = self.batch_nms(
            boxes_xyxy[..., :4], scores, self.config.score_thr, self.config.nms_thr
        )
        return results

    def run_gpu_batch(self, imgs, original_size):
        if self.debug:
            time0 = time.time()

        self.original_size = original_size

        # Preprocess all images
        imgs_tensor = imgs.permute(0, 3, 1, 2).contiguous().float()

        # Allocate the PyTorch tensor for the model input
        binding = self.session.io_binding()
        binding.bind_input(
            name=self.config.input_name,
            device_type=self.config.gpu_device_type,
            device_id=self.config.gpu_device_id,
            element_type=self.config.model_input_dtype,
            shape=tuple(imgs_tensor.shape),
            buffer_ptr=imgs_tensor.data_ptr(),
        )

        # Allocate the PyTorch tensor for the model output
        batch_size = imgs_tensor.shape[0]
        output_row = 32 * 32 * (1 + 4 + 16)
        output_shape = (batch_size, output_row, 6)
        output_tensor = torch.empty(
            output_shape,
            dtype=self.dtype_convert_np2torch(self.config.model_output_dtype),
            device=f"{self.config.gpu_device_type}:{self.config.gpu_device_id}",
        ).contiguous()
        binding.bind_output(
            name=self.config.output_name,
            device_type=self.config.gpu_device_type,
            device_id=self.config.gpu_device_id,
            element_type=self.config.model_output_dtype,
            shape=tuple(output_tensor.shape),
            buffer_ptr=output_tensor.data_ptr(),
        )

        if self.debug:
            time1 = time.time()
            self.log["time_preparation"] += time1 - time0

        # Run the model
        self.session.run_with_iobinding(binding)
        if self.debug:
            time2 = time.time()
            self.log["time_inference"] += time2 - time1
            print(self.session.get_providers())
            print(self.session.get_provider_options())

        # Postprocess the output
        output_processed = self.postprocess_batch(output_tensor)

        return output_processed

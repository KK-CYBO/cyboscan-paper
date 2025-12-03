import onnxruntime
import numpy as np
import torch


class MaxVitConfig:
    def __init__(self, model_path):
        """
        model_path: MaxVit model path (Ex. "/path/to/model.onnx")
        label_names: The list of class names (Ex. ["Leu", "Gran", "Epi", "KS", "Debris", "LSIL", "HSIL", "Adeno"])
        crop_size: The size of the input image crop to be fed to the model (Ex. 224)
        batch_size: The batch size for the model (Ex. 64)
        """
        self.model_path = model_path
        self.label_names = []
        self.crop_size = 224
        self.batch_size = 64
        self.gpu_device_id = 0  # GPU device number
        self.gpu_device_type = "cuda"  # GPU device type
        self.gpu_mem_limit = (
            20 * 1024 * 1024 * 1024
        )  # GPU memory limit (For 20GB, set 20*1024*1024*1024)
        self.input_name = "input"
        # If this name does not exist in the model, the classifier falls back to the last output
        self.output_name = "output"

        self.model_input_dtype = np.float32


class CellClassifier:
    def __init__(self, maxvitconfig):
        self.maxvitconfig = maxvitconfig

        providers = [
            (
                "CUDAExecutionProvider",
                {
                    "device_id": maxvitconfig.gpu_device_id,
                    "arena_extend_strategy": "kNextPowerOfTwo",
                    "gpu_mem_limit": maxvitconfig.gpu_mem_limit,
                    "cudnn_conv_algo_search": "EXHAUSTIVE",
                    "do_copy_in_default_stream": True,
                },
            ),
            (
                "CPUExecutionProvider",
                {
                    "arena_extend_strategy": "kNextPowerOfTwo",
                },
            ),
        ]

        self.session = onnxruntime.InferenceSession(
            maxvitconfig.model_path, providers=providers
        )
        self.binding = self.session.io_binding()

        # Decide which output to use
        model_outputs = self.session.get_outputs()
        output_names = [o.name for o in model_outputs]
        if maxvitconfig.output_name in output_names:
            self.output_name = maxvitconfig.output_name
        else:
            self.output_name = output_names[-1]
            self.maxvitconfig.output_name = self.output_name

        # Probe output shape and dtype
        input_data = np.random.randn(
            1, 3, maxvitconfig.crop_size, maxvitconfig.crop_size
        ).astype(self.maxvitconfig.model_input_dtype)
        results = self.session.run([self.output_name], {maxvitconfig.input_name: input_data})
        output = results[0]

        if output.ndim != 2:
            raise ValueError(
                f"Expected 2D output (batch, num_classes) from '{self.output_name}', "
                f"but got shape {output.shape}"
            )

        self.output_len = output.shape[1]
        self.output_dtype = output.dtype

    def __del__(self):
        try:
            del self.session
        except AttributeError:
            pass

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

    def run_inference_gpu(self, img_tensor):
        img_tensor = img_tensor.permute(0, 3, 1, 2).contiguous()
        dataset = torch.utils.data.TensorDataset(img_tensor)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=self.maxvitconfig.batch_size, shuffle=False
        )

        logits_list = []
        current_batch_size = -1
        output_tensor = None

        for batch in dataloader:
            batch_image_tensor = batch[0].to(
                device=f"{self.maxvitconfig.gpu_device_type}:{self.maxvitconfig.gpu_device_id}"
            )
            batch_image_tensor = batch_image_tensor / 255.0

            self.binding.bind_input(
                name=self.maxvitconfig.input_name,
                device_type=self.maxvitconfig.gpu_device_type,
                device_id=self.maxvitconfig.gpu_device_id,
                element_type=self.maxvitconfig.model_input_dtype,
                shape=tuple(batch_image_tensor.shape),
                buffer_ptr=batch_image_tensor.data_ptr(),
            )

            if batch_image_tensor.shape[0] != current_batch_size:
                current_batch_size = batch_image_tensor.shape[0]
                output_tensor = torch.empty(
                    (current_batch_size, self.output_len),
                    dtype=self.dtype_convert_np2torch(self.output_dtype),
                    device=f"{self.maxvitconfig.gpu_device_type}:{self.maxvitconfig.gpu_device_id}",
                ).contiguous()

                self.binding.bind_output(
                    name=self.output_name,
                    device_type=self.maxvitconfig.gpu_device_type,
                    device_id=self.maxvitconfig.gpu_device_id,
                    element_type=self.output_dtype,
                    shape=tuple(output_tensor.shape),
                    buffer_ptr=output_tensor.data_ptr(),
                )

            self.session.run_with_iobinding(self.binding)

            logits_list.append(output_tensor.cpu().numpy())

        if not logits_list:
            return np.zeros((0, self.output_len), dtype=self.output_dtype)

        return np.concatenate(logits_list, axis=0)

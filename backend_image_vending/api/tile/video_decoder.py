from fractions import Fraction
import json
import torch
import subprocess
import decord as de


class VideoManager:
    def __init__(self, video_path, gpu_id=0):
        self.loaded_video_path = None
        self.fps = None
        self.width = None
        self.height = None
        self.gpu_id = gpu_id
        self.num_threads = 8
        self.decoder = None

        torch.cuda.set_device(self.gpu_id)

        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate",
                "-of", "json",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            stream = data["streams"][0]

            self.width = int(stream["width"])
            self.height = int(stream["height"])
            fps_str = stream["r_frame_rate"]
            self.fps = float(Fraction(fps_str)) if fps_str != "0/0" else None

            # --- GPU decoder only ---
            de.bridge.set_bridge("torch")
            self.decoder = de.VideoReader(
                video_path,
                ctx=de.gpu(self.gpu_id),
                num_threads=self.num_threads,
                width=self.width,
                height=self.height,
            )

            self.loaded_video_path = video_path

        except Exception as e:
            print(f"[ERROR] Failed to load video {video_path}: {e}")
            raise e

    def get_tensor(self, frame_num):
        if not self.loaded_video_path:
            raise ValueError("No video loaded.")

        try:
            de.bridge.set_bridge("torch")
            frame = self.decoder[frame_num]  # GPU tensor
            return frame

        except Exception as e:
            print(f"[ERROR] Frame {frame_num} decode failed: {e}")
            raise e

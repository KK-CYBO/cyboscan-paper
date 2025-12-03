import torch
import torch.nn.functional as F
from .utils import get_cached_slidedata
from .video_decoder import VideoManager
from collections import defaultdict

video_managers = {}
video_requests = defaultdict(set)


def get_video_manager(user_id, slidename, video_path):
    video_requests[slidename].add(user_id)

    if slidename not in video_managers:
        video_managers[slidename] = VideoManager(video_path)

    return video_managers[slidename]


def remove_video_manager(user_id, slidename):
    if slidename in video_requests:
        video_requests[slidename].discard(user_id)
        if not video_requests[slidename]:
            video_requests.pop(slidename, None)
            video_managers.pop(slidename, None)


def get_processor(user_id, slidename, dzi_level):
    slidedata = get_cached_slidedata(slidename)
    video_manager = get_video_manager(user_id, slidename, slidedata.base_path)
    return BaseImageProcessor(video_manager)


class BaseImageProcessor:
    def __init__(self, video_manager):
        self.video_manager = video_manager

    def get_image(self, slidename, dzi_level, x, y, z):
        slidedata = get_cached_slidedata(slidename)

        blayer = slidedata.dzi_params["dzi_depth"] - dzi_level - 1
        blscale = 2**blayer
        basex = x * slidedata.dzi_params["dzi_block_size"] * blscale
        basey = y * slidedata.dzi_params["dzi_block_size"] * blscale
        b_tilex, b_posx = divmod(basex, slidedata.dzi_params["save_block_size"])
        b_tiley, b_posy = divmod(basey, slidedata.dzi_params["save_block_size"])

        block = slidedata.blockmap.get((b_tilex, b_tiley))
        if block is None:
            raise KeyError(f"Block not found for indices: ({b_tilex}, {b_tiley})")

        margin_added = block["margin_added"]
        margin = block["margin"]
        block_margin = [margin * m for m in margin_added]
        blmar = [int(m / blscale) for m in block_margin]

        blbw = (
            int(slidedata.dzi_params["save_block_size"] / blscale) + blmar[0] + blmar[2]
        )
        blbh = (
            int(slidedata.dzi_params["save_block_size"] / blscale) + blmar[1] + blmar[3]
        )

        x0 = max(
            0, blmar[0] + int(b_posx / blscale) - slidedata.dzi_params["dzi_margin"]
        )
        y0 = max(
            0, blmar[1] + int(b_posy / blscale) - slidedata.dzi_params["dzi_margin"]
        )
        x1 = min(
            blbw,
            x0
            + slidedata.dzi_params["dzi_block_size"]
            + 2 * slidedata.dzi_params["dzi_margin"],
        )
        y1 = min(
            blbh,
            y0
            + slidedata.dzi_params["dzi_block_size"]
            + 2 * slidedata.dzi_params["dzi_margin"],
        )

        spot_index = block.get("spotindex")
        dx = block.get("crop_dx")
        dy = block.get("crop_dy")

        if spot_index is None:
            raise ValueError(f"spot index not found for ({b_tilex},{b_tiley})")

        frame_num = spot_index * slidedata.num_layers + z
        tensor = self.video_manager.get_tensor(frame_num)

        cx0 = dx - block_margin[0]
        cy0 = dy - block_margin[1]
        cw = slidedata.dzi_params["save_block_size"] + block_margin[0] + block_margin[2]
        ch = slidedata.dzi_params["save_block_size"] + block_margin[1] + block_margin[3]

        tensor = tensor.to("cuda", non_blocking=True)

        if tensor.dtype == torch.uint8:
            tensor = tensor.float() / 255.0

        tensor = tensor[cy0 : cy0 + ch, cx0 : cx0 + cw, :].permute(2, 0, 1)

        if blscale != 1:
            tensor = F.interpolate(
                tensor.unsqueeze(0),
                size=(blbh, blbw),
                mode="bilinear",
                align_corners=False,
            ).squeeze(0)

        tensor = tensor[..., y0:y1, x0:x1]
        tensor = tensor.permute(1, 2, 0)
        img = tensor.detach().cpu().numpy()

        if img.dtype != "uint8":
            img = (img * 255).clip(0, 255).astype("uint8")

        img = img[...,::-1] # BGR to RGB
        return img

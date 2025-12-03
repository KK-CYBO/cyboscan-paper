class SlideData:
    __slots__ = (
        "num_layers",
        "base_path",
        "dzi_params",
        "blockmap",
    )

    def __init__(
        self,
        num_layers,
        base_path,
        dzi_params,
        blockmap,
    ):
        self.num_layers = num_layers
        self.base_path = base_path
        self.dzi_params = dzi_params
        self.blockmap = blockmap


def get_cached_slidedata(slidename):
    """
    Dummy implementation for illustration purposes.

    In the production system, this function retrieves slide metadata and
    block layout from the slide processing pipeline or a metadata store.
    The dummy implementation below provides only minimal metadata; the
    tile endpoint will always return 404 because `blockmap` is empty.
    """
    num_layers = 40
    base_path = "/path/to/video.mp4"
    dzi_params = {
        "dzi_depth": 10,
        "dzi_block_size": 1024,
        "save_block_size": 4096,
        "dzi_margin": 1,
        "wsi_size": (100000, 80000),  # dummy full-resolution width, height
    }
    blockmap = {}
    
    return SlideData(
        num_layers=num_layers,
        base_path=base_path,
        dzi_params=dzi_params,
        blockmap=blockmap,
    )

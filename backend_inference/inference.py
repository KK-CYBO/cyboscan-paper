from run_inference_full import RunInference

gpu_device_id = 0


## Inputs
input_video_path = "/path/to/video.mp4"
# Number of focal planes per tile
z_layers = 40
# Number of tiles
num_tiles = 100

yolo_model_path = "/path/to/yolox/model"
maxvit_model_path = "/path/to/maxvit/model"

## Output
output_csv_path = "./output/celllist.csv"


classlist = [
    "Leu",
    "Glan",
    "Squ.epi",
    "Squ.meta",
    "Debris",
    "Para.Squ",
    "Para.Clust",
    "LSIL",
    "HSIL",
    "Adenocarcinoma",
]
gpu_mem_limit = 30 * 1024 * 1024 * 1024

runInf = RunInference(
    yolo_model_path,
    maxvit_model_path,
    classlist,
    gpu_device_id,
    gpu_mem_limit,
)
runInf.yoloconfig.score_thr = 0.05  # yolo score threshold
runInf.yoloconfig.nms_thr = 0.0  # yolo nms threshold

runInf.analyze_slide_gpu(input_video_path, output_csv_path, z_layers, num_tiles)

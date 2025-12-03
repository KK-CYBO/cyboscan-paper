#ifndef IMAGING_H
#define IMAGING_H

#include <vector>
#include <mutex>
#include <thread>
#include <chrono>
#include <iostream>
#include <opencv2/opencv.hpp>
#include <cuda_runtime.h>

#include "capture.h"
#include "encoder.h" 


extern bool abort_all;
extern bool frame_miss;
extern bool new_capture;
extern bool imaging_is_free;
extern bool focus_finished;
extern unsigned int spot_count_done;
extern unsigned int desired_num_of_spots;
extern unsigned short z_map_minVal;
extern unsigned short z_map_maxVal;
extern unsigned short n_layers;
extern unsigned short n_f_layers_g;
extern unsigned short starting_layer;
extern unsigned int enc_state[];
extern int vid_stat;
extern bool video_init;
extern bool video_finished;
extern float bit_r;
extern const char* output_video_path;
extern bool logs_on;
extern std::string debug_slide_dir;

class IpexCamera;
class FocusGPU;
class Encoder;


class FocusGPU
{
public:
    unsigned char* dra_bayer_stack_8b = nullptr;
    unsigned char* one_bgr_img = nullptr;
    unsigned char* best_z_map_g = nullptr;
    unsigned int*  layer_idx = nullptr;
    unsigned char* bgr_focused_undistorted = nullptr;

    dim3 threadsPerBlock = dim3(32, 32);

    void bayer_focus_inplace_toBGR(
        unsigned char* input_8b,
        unsigned char* output_8b,
        unsigned char * best_z_map,
        unsigned int * layer_idx_,
        int img_H,
        int img_W,
        int minV,
        int maxV,
        int n_layers,
        int current_l
    );

    void convertTo8bit(
        const unsigned short *d_inBayer,
        unsigned char *d_outBayer,
        int width,
        int height
    );
};


class Focus
{
public:
    IPEXCAMImpl* ipex_cam = nullptr;
    FocusGPU* fgpu = nullptr;

    int orig_W = 0;
    int orig_H = 0;

    Encoder* encoder_obj = nullptr;

    void final_focus();
    bool final_focus_task_gpu(int spotIdx, unsigned short* stack_bayer_16bit);
    void video_encoder(); 
};

#endif // IMAGING_H

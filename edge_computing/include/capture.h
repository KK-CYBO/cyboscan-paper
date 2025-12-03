#ifndef CAPTURE_H
#define CAPTURE_H

#include <cuda_runtime.h>
#include <cuda.h>

#include <sys/ioctl.h>
#include <linux/videodev2.h>
#include <fcntl.h>

#include <stdio.h>
#include <stdlib.h>
#include <mutex>
#include <vector>
#include <atomic>
#include <condition_variable>
#include <thread>

class IPEXCAMImpl
{
public:

    bool mode_definition(unsigned int mode_)
    {
        if (mode_ == 0)
        {
            cam_current_H = 4504;
            cam_current_W = 4480;
            cam_current_P = 4608;
            FPS = 50;
        }
        else return false;

        one_img_vol        = 3ull * cam_current_H * cam_current_W;
        one_16b_bayer_vol  = 1ull * cam_current_H * cam_current_W * sizeof(uint16_t);
        return true;
    }

    IPEXCAMImpl(
        unsigned int cam_mode,
        unsigned int FrameRate,
        unsigned int num_of_imgs,
        unsigned int num_of_af_imgs,
        float expo_ms,
        float gain_val,
        bool logsOn)
    {
        if (!mode_definition(cam_mode))
        {
            printf("Camera Construction Failed.\n");
            return;
        }

        logs_on = logsOn;
        gain    = gain_val;

        finish_capturing      = false;
        consumer_ready        = false;
        IpexFrN               = 0;
        img_stk_stat          = 0;
        ipex_consumer_finished = false;

        num_of_buffer     = num_of_imgs;
        one_stk_vol       = num_of_buffer * one_img_vol;
        Stk_16b_bayer_vol = num_of_buffer * one_16b_bayer_vol;

        cudaMalloc((void**)&bayer16bStack, Stk_16b_bayer_vol);

        bg_done.resize(num_of_buffer, false);
        im_buf_idx.resize(num_of_buffer);

        background_img_H = new uint16_t[cam_current_H * cam_current_W];

        printf("IPEXCAMImpl constructed (Dummy Mode)\n");
    }

    ~IPEXCAMImpl()
    {
        cudaFree(bayer16bStack);
        delete[] background_img_H;
    }

    bool AddGainTo16bit(
        const uint16_t* input_d,
        const int h_,
        const int w_,
        const int p_,
        unsigned short* bayerTmp,
        float col_gain_red,
        float col_gain_gr1,
        float col_gain_gr2,
        float col_gain_blue,
        bool apply_bg);

    int cam_current_H, cam_current_W, cam_current_P;
    unsigned char* bayer_tmp = nullptr;
    uint16_t*      bayer16bStack = nullptr;
    uint16_t*      background_img_H = nullptr;

    unsigned int num_of_buffer = 0;
    unsigned long one_img_vol = 0;
    unsigned long one_16b_bayer_vol = 0;
    unsigned long one_stk_vol = 0;
    unsigned long Stk_16b_bayer_vol = 0;

    float col_gain_red  = 1.4f;
    float col_gain_gr1  = 1.0f;
    float col_gain_gr2  = 1.0f;
    float col_gain_blue = 2.5f;

    std::vector<bool>         bg_done;
    std::vector<unsigned int> im_buf_idx;
    std::vector<unsigned int> FPGA_FrN;

    std::atomic<bool>     finish_capturing;
    std::atomic<bool>     consumer_ready;
    std::atomic<uint64_t> IpexFrN;

    std::atomic<unsigned short> img_stk_stat{0};
    std::atomic<bool>           ipex_consumer_finished{false};

    int   current_img_idx = 0;
    bool  logs_on = false;
    int   FPS     = 50;
    float gain    = 1.0f;

    bool send_trigger()
    {
        IpexFrN++;
        return true;
    }

    unsigned short img_stack_status() const {
        return img_stk_stat;
    }

    void release_img_buff(int idx) {
        // dummy
    }

    unsigned short* get_16b_bayer_stack() {
        return bayer16bStack;
    }

    bool is_bg_done(int layer) const {
        return bg_done[layer];
    }

    void get_layers_indexes(unsigned int* out_idx) {
        for (size_t i = 0; i < im_buf_idx.size(); i++) {
            out_idx[i] = im_buf_idx[i];
        }
    }

};


class CamBayerConsumer
{
public:
    explicit CamBayerConsumer(IPEXCAMImpl* impl, int W, int H);
    ~CamBayerConsumer();

    bool threadInitialize();
    bool threadExecute();
    bool threadShutdown();

private:
    IPEXCAMImpl* ipex_cam_impl;
    int imgW, imgH;

    std::atomic<bool> stopFlag{false};
};

#endif

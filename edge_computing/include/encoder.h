#ifndef ENCODER_H
#define ENCODER_H

#include <iostream>
#include <chrono>
#include <thread>

#include <opencv2/highgui.hpp>
#include <opencv2/opencv.hpp>
#include <opencv2/core.hpp>

#include "imaging.h"

#include <cuda.h>
#include <cuda_runtime.h>
#include <cuda_runtime_api.h>
#include "NvUtils.h"
#include <semaphore.h>
#include "NvVideoEncoder.h" 
#include <linux/videodev2.h>
#include "NvBufSurface.h"
#include "NvUtils.h"
#include "cudaEGL.h"

typedef unsigned char uchar;
#define MICROSECOND_UNIT 1000000
#define NUM_IMG_PLANES 3
#define NUM_BUFFERS 30

#define CRC32_POLYNOMIAL  0xEDB88320L
#define MAX_OUT_BUFFERS 32

#define TEST_ERROR(cond, str, label) if(cond) { \
                                        cerr << str << endl; \
                                        error = 1; \
                                        goto label; }

#define TEST_PARSE_ERROR(cond, label) if(cond) { \
    cerr << "Error parsing runtime parameter changes string" << endl; \
    goto label; }

#define IS_DIGIT(c) (c >= '0' && c <= '9')
#define MICROSECOND_UNIT 1000000

typedef struct RPS_List
{
    uint32_t nFrameId;
    bool bLTRefFrame;
} RPS_List;

typedef struct RPS_param
{
    sem_t sema;
    uint32_t m_numTemperalLayers;
    uint32_t nActiveRefFrames;
    RPS_List rps_list[V4L2_MAX_REF_FRAMES];
} RPS_param;

typedef struct CrcRec
{
    unsigned int CRCTable[256];
    unsigned int CrcValue;
}Crc;

typedef struct
{
    NvVideoEncoder *enc;
    uint32_t encoder_pixfmt;
    uint32_t raw_pixfmt;

    char *in_file_path;
    std::ifstream *in_file;

    uint32_t width;
    uint32_t height;

    char *out_file_path;
    std::ofstream *out_file;

    uint32_t bitrate;
    uint32_t peak_bitrate;
    uint32_t profile;
    enum v4l2_mpeg_video_bitrate_mode ratecontrol;
    uint32_t iframe_interval;
    uint32_t idr_interval;
    uint32_t level;
    uint32_t fps_n;
    uint32_t fps_d;
    uint32_t gdr_start_frame_number;
    uint32_t gdr_num_frames;
    uint32_t gdr_out_frame_number;
    enum v4l2_enc_temporal_tradeoff_level_type temporal_tradeoff_level;
    enum v4l2_enc_hw_preset_type hw_preset_type;
    v4l2_enc_slice_length_type slice_length_type;
    uint32_t slice_length;
    uint32_t virtual_buffer_size;
    uint32_t num_reference_frames;
    uint32_t slice_intrarefresh_interval;
    uint32_t num_b_frames;
    uint32_t nMinQpI;
    uint32_t nMaxQpI;
    uint32_t nMinQpP;
    uint32_t nMaxQpP;
    uint32_t nMinQpB;
    uint32_t nMaxQpB;
    uint32_t sMaxQp;
    uint32_t sar_width;
    uint32_t sar_height;
    uint32_t IinitQP;
    uint32_t PinitQP;
    uint32_t BinitQP;
    uint32_t log2_num_av1rows;
    uint32_t log2_num_av1cols;
    uint8_t bit_depth;
    uint8_t enable_av1ssimrdo;
    uint8_t disable_av1cdfupdate;
    uint8_t chroma_format_idc;
    int output_plane_fd[32];
    bool insert_sps_pps_at_idr;
    bool enable_slice_level_encode;
    bool disable_cabac;
    bool insert_vui;
    bool enable_extended_colorformat;
    bool insert_aud;
    bool alliframes;
    bool is_semiplanar;
    bool enable_initQP;
    bool enable_ratecontrol;
    bool enable_av1tile;
    enum v4l2_memory output_memory_type;
    enum v4l2_colorspace cs;

    bool report_metadata;
    bool input_metadata;
    bool copy_timestamp;
    uint32_t start_ts;
    bool dump_mv;
    bool enableGDR;
    bool bGapsInFrameNumAllowed;
    bool bnoIframe;
    uint32_t nH265PocLsbBits;
    bool externalRCHints;
    bool enableROI;
    bool b_use_enc_cmd;
    bool enableLossless;
    bool got_eos;

    bool externalRPS;
    bool RPS_threeLayerSvc;
    RPS_param rps_par;

    bool use_gold_crc;
    char gold_crc[20];
    Crc *pBitStreamCrc;

    bool bReconCrc;
    uint32_t rl;
    uint32_t rt;
    uint32_t rw;
    uint32_t rh;

    uint64_t timestamp;
    uint64_t timestampincr;

    bool stats;

    std::stringstream *runtime_params_str;
    uint32_t next_param_change_frame;
    bool got_error;
    int  stress_test;
    uint32_t endofstream_capture;
    uint32_t endofstream_output;

    uint32_t input_frames_queued_count;
    uint32_t startf;
    uint32_t endf;
    uint32_t num_output_buffers;
    int32_t num_frames_to_encode;
    uint32_t poc_type;

    v4l2_enc_ppe_init_params ppe_init_params;

    int max_perf;
    int blocking_mode; 
    sem_t pollthread_sema;
    sem_t encoderthread_sema;
    pthread_t   enc_pollthread;
    pthread_t enc_capture_loop;
} context_t;

class Encoder
{
private:

public:
    Encoder()
    {

    };

    ~Encoder()
    {

    };

    void RGBto3ChYUV420(
        const unsigned char * d_frame_rgb,
        unsigned char * d_frame_y,
        unsigned char * d_frame_u,
        unsigned char * d_frame_v,
        int H,
        int W,
        int step,
        int ystep,
        int uvstep
    );

    unsigned int GetPitch(unsigned int width, const unsigned int stride);
    const char* get_pixfmt_string(uint32_t pixfmt);
    int setup_output_dmabuf(context_t *ctx, uint32_t num_buffers );
    int get_next_parsed_pair(context_t *ctx, char *id, uint32_t *value);
    int set_runtime_params(context_t *ctx);
    int get_next_runtime_param_change_frame(context_t *ctx);

    void set_defaults(
        context_t * ctx,
        unsigned int H_,
        unsigned int W_,
        unsigned int P_,
        unsigned int framerate,
        float bit_r,
        std::string debug_slide_dir,
        bool debug_logs_on
    );

    bool init_encoder(
        context_t& ctx, 
        unsigned int H_,
        unsigned int W_,
        unsigned int P_,
        unsigned int framerate,
        float bit_r,
        const char* output_video_path,
        std::string debug_slide_dir,
        bool debug_logs_on
    );

    void encode_frame(
        context_t& ctx,
        const unsigned char* color_img,
        unsigned int frNum,
        bool finished_frames
    );

    int enqueue_end_frame(context_t &ctx);

    bool cleanups(context_t &ctx);
};

#endif // ENCODER_H

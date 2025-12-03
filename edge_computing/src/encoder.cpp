#include "encoder.h"

using namespace cv;
using namespace std;


unsigned int Encoder::GetPitch(unsigned int width, const unsigned int stride) 
{
    int num_strides = width/stride;
    if ((width % stride) != 0)
        ++num_strides;
    return num_strides*stride;
}


void abort_enc(context_t *ctx)
{
    ctx->got_error = true;
    ctx->enc->abort();
}


const char* Encoder::get_pixfmt_string(uint32_t pixfmt)
{
    switch (pixfmt)
    {
        case V4L2_PIX_FMT_YUV420M:          return "V4L2_PIX_FMT_YUV420M";
        case V4L2_PIX_FMT_NV12M:            return "V4L2_PIX_FMT_NV12M";
        case V4L2_PIX_FMT_YUV444M:          return "V4L2_PIX_FMT_YUV444M";
        case V4L2_PIX_FMT_NV24M:            return "V4L2_PIX_FMT_NV24M";
        case V4L2_PIX_FMT_P010M:            return "V4L2_PIX_FMT_P010M";
        case V4L2_PIX_FMT_NV24_10LE:        return "V4L2_PIX_FMT_NV24_10LE";
        case V4L2_PIX_FMT_H264:             return "V4L2_PIX_FMT_H264";
        case V4L2_PIX_FMT_H265:             return "V4L2_PIX_FMT_H265";
        case V4L2_PIX_FMT_VP8:              return "V4L2_PIX_FMT_VP8";
        case V4L2_PIX_FMT_VP9:              return "V4L2_PIX_FMT_VP9";
        default:                            return "";
    }
}


int Encoder::setup_output_dmabuf(context_t *ctx, uint32_t num_buffers)
{
    int ret=0;
    NvBufSurf::NvCommonAllocateParams cParams;
    int fd;
    ret = ctx->enc->output_plane.reqbufs(V4L2_MEMORY_DMABUF,num_buffers);
    if(ret)
    {
        cerr << "reqbufs failed for output plane V4L2_MEMORY_DMABUF" << endl;
        return ret;
    }
    for (uint32_t i = 0; i < ctx->enc->output_plane.getNumBuffers(); i++)
    {
        cParams.width = ctx->width;
        cParams.height = ctx->height;
        cParams.layout = NVBUF_LAYOUT_PITCH;
        // cParams.layout = NVBUF_LAYOUT_BLOCK_LINEAR;
        
        switch (ctx->cs)
        {
            case V4L2_COLORSPACE_REC709:
                cParams.colorFormat = ctx->enable_extended_colorformat ?
                    NVBUF_COLOR_FORMAT_YUV420_709_ER : NVBUF_COLOR_FORMAT_YUV420_709;
                break;
            case V4L2_COLORSPACE_SMPTE170M:
            default:
                cParams.colorFormat = ctx->enable_extended_colorformat ?
                    NVBUF_COLOR_FORMAT_YUV420_ER : NVBUF_COLOR_FORMAT_YUV420;
        }
        if (ctx->is_semiplanar)
        {
            cParams.colorFormat = NVBUF_COLOR_FORMAT_NV12;
        }
        if (ctx->encoder_pixfmt == V4L2_PIX_FMT_H264)
        {
            if (ctx->enableLossless)
            {
                if (ctx->is_semiplanar)
                    cParams.colorFormat = NVBUF_COLOR_FORMAT_NV24;
                else
                    cParams.colorFormat = NVBUF_COLOR_FORMAT_YUV444;
            }
        }
        else if (ctx->encoder_pixfmt == V4L2_PIX_FMT_H265)
        {
            if (ctx->chroma_format_idc == 3)
            {
                if (ctx->is_semiplanar)
                    cParams.colorFormat = NVBUF_COLOR_FORMAT_NV24;
                else
                    cParams.colorFormat = NVBUF_COLOR_FORMAT_YUV444;

                if (ctx->bit_depth == 10)
                    cParams.colorFormat = NVBUF_COLOR_FORMAT_NV24_10LE;
            }
            if (ctx->profile == V4L2_MPEG_VIDEO_H265_PROFILE_MAIN10 && (ctx->bit_depth == 10))
            {
                cParams.colorFormat = NVBUF_COLOR_FORMAT_NV12_10LE;
            }
        } 
        
        cParams.memtag = NvBufSurfaceTag_VIDEO_ENC;
        cParams.memType = NVBUF_MEM_DEFAULT;
        ret = NvBufSurf::NvAllocate(&cParams, 1, &fd);
        if(ret < 0)
        {
            cerr << "Failed to create NvBuffer" << endl;
            return ret;
        }
        ctx->output_plane_fd[i]=fd;
    }
    return ret;
}


int write_encoder_output_frame(ofstream * stream, NvBuffer * buffer)
{
    stream->write((char *) buffer->planes[0].data, buffer->planes[0].bytesused);
    if(buffer->planes[0].bytesused == 0)
    {
        cerr << "Dropped frame!!!\n";
    }
    return 0;
}


bool encoder_capture_plane_dq_callback(  struct v4l2_buffer *v4l2_buf, 
                                                NvBuffer * buffer,
                                                NvBuffer * shared_buffer,
                                                void *arg
                                            )
{
    context_t *ctx = (context_t *) arg;
    NvVideoEncoder *enc = ctx->enc;
    pthread_setname_np(pthread_self(), "EncCapPlane");
    uint32_t frame_num = ctx->enc->capture_plane.getTotalDequeuedBuffers() - 1;
    uint32_t ReconRef_Y_CRC = 0;
    uint32_t ReconRef_U_CRC = 0;
    uint32_t ReconRef_V_CRC = 0;
    uint32_t num_encoded_frames = 1;
    struct v4l2_event ev;
    int ret = 0;

    if (v4l2_buf == NULL)
    {
        cout << "Error while dequeing buffer from output plane" << endl;
        abort_enc(ctx);
        return false;
    }

    if (buffer->planes[0].bytesused == 0)
    {
        cout << "Got 0 size buffer in capture, ending encoding \n";
        return false;
    }

    if (!ctx->stats)
        write_encoder_output_frame(ctx->out_file, buffer);

    num_encoded_frames++;

    if (enc->capture_plane.qBuffer(*v4l2_buf, NULL) < 0)
    {
        cerr << "Error while Qing buffer at capture plane" << endl;
        abort_enc(ctx);
        return false;
    }

    return true;
}


int Encoder::get_next_parsed_pair(context_t *ctx, char *id, uint32_t *value)
{
    char charval;

    *ctx->runtime_params_str >> *id;
    if (ctx->runtime_params_str->eof())
    {
        return -1;
    }

    charval = ctx->runtime_params_str->peek();
    if (!IS_DIGIT(charval))
    {
        return -1;
    }

    *ctx->runtime_params_str >> *value;

    *ctx->runtime_params_str >> charval;
    if (ctx->runtime_params_str->eof())
    {
        return 0;
    }

    return charval;
}


int Encoder::set_runtime_params(context_t *ctx)
{
    char charval;
    uint32_t intval;
    int ret, next;

    cout << "Frame " << ctx->next_param_change_frame << ": Changing parameters" << endl;
    while (!ctx->runtime_params_str->eof())
    {
        next = get_next_parsed_pair(ctx, &charval, &intval);
        TEST_PARSE_ERROR(next < 0, err);
        switch (charval)
        {
            case 'b':
                if (ctx->ratecontrol == V4L2_MPEG_VIDEO_BITRATE_MODE_VBR &&
                    ctx->peak_bitrate < intval) {
                    uint32_t peak_bitrate = 1.2f * intval;
                    ret = ctx->enc->setPeakBitrate(peak_bitrate);
                    if (ret < 0)
                    {
                        cerr << "Could not set encoder peak bit rate" << endl;
                        goto err;
                    }
                }
                ret = ctx->enc->setBitrate(intval);
                if (ret < 0)
                {
                    cerr << "Could not set encoder bit rate" << endl;
                    goto err;
                }
                break;
            case 'p':
                ret = ctx->enc->setPeakBitrate(intval);
                if (ret < 0)
                {
                    cerr << "Could not set encoder peak bit rate" << endl;
                    goto err;
                }
                break;
            case 'r':
            {
                int fps_num = intval;
                TEST_PARSE_ERROR(next != '/', err);

                ctx->runtime_params_str->seekg(-1, ios::cur);
                next = get_next_parsed_pair(ctx, &charval, &intval);
                TEST_PARSE_ERROR(next < 0, err);

                cout << "Framerate = " << fps_num << "/"  << intval << endl;

                ret = ctx->enc->setFrameRate(fps_num, intval);
                if (ret < 0)
                {
                    cerr << "Could not set framerate" << endl;
                    goto err;
                }
                break;
            }
            case 'i':
                if (intval > 0)
                {
                    ctx->enc->forceIDR();
                    cout << "Forcing IDR" << endl;
                }
                break;
            default:
                TEST_PARSE_ERROR(true, err);
        }
        switch (next)
        {
            case 0:
                delete ctx->runtime_params_str;
                ctx->runtime_params_str = NULL;
                return 0;
            case '#':
                return 0;
            case ',':
                break;
            default:
                break;
        }
    }
    return 0;
err:
    cerr << "Skipping further runtime parameter changes" <<endl;
    delete ctx->runtime_params_str;
    ctx->runtime_params_str = NULL;
    return -1;
}


int Encoder::get_next_runtime_param_change_frame(context_t *ctx)
{
    char charval;
    int ret;

    ret = get_next_parsed_pair(ctx, &charval, &ctx->next_param_change_frame);
    if(ret == 0)
    {
        return 0;
    }

    TEST_PARSE_ERROR((ret != ';' && ret != ',') || charval != 'f', err);

    return 0;

err:
    cerr << "Skipping further runtime parameter changes" <<endl;
    delete ctx->runtime_params_str;
    ctx->runtime_params_str = NULL;
    return -1;
}


struct ParamSet {
    float bitrate;
    int   iframe_interval;
    int   idr_interval;
    int   num_b_frames;
    int   nMinQpI;
    int   nMaxQpI;
    int   nMinQpP;
    int   nMaxQpP;
    int   nMinQpB;
    int   nMaxQpB;
    int   sMaxQp;
};

// Parameter examples
static constexpr float kBitrates[]      = { 0.1f, };
static constexpr int   kIntervals[]     = { 5, 4, 3, 2, 1};
static constexpr int   kBFrames[]       = { 0, 1, 2};
static constexpr int   kMaxQps[]        = { 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20};

#define PARAM_CASE(SET_ID, BR, INT, BF, QP) \
case SET_ID:                               \
    param_set.bitrate         = kBitrates[BR];    \
    param_set.iframe_interval = kIntervals[INT];  \
    param_set.idr_interval    = kIntervals[INT];  \
    param_set.num_b_frames    = kBFrames[BF];     \
    param_set.nMinQpI         = 0;                \
    param_set.nMaxQpI         = kMaxQps[QP];      \
    param_set.nMinQpP         = 0;                \
    param_set.nMaxQpP         = kMaxQps[QP];      \
    param_set.nMinQpB         = 0;                \
    param_set.nMaxQpB         = kMaxQps[QP];      \
    param_set.sMaxQp          = 0;                \
    break;


void setEncodingParams(ParamSet& param_set, int set_id) {
    switch (set_id) {
        // Define parameter cases here
        PARAM_CASE( 1, 0, 2, 0, 10) // example

        default:
            std::cerr << "Invalid set_id: " << set_id << std::endl;
            std::cerr << "Set default." << std::endl;
            param_set.bitrate = 0.1f;
            param_set.iframe_interval = 1;
            param_set.idr_interval = 1;
            param_set.num_b_frames = 1;
            param_set.nMinQpI = 0;
            param_set.nMaxQpI = 51;
            param_set.nMinQpP = 0;
            param_set.nMaxQpP = 51;
            param_set.nMinQpB = 0;
            param_set.nMaxQpB = 51;
            param_set.sMaxQp = 0;
            break;
    }
}


void Encoder::set_defaults(
    context_t * ctx,
    unsigned int H_,
    unsigned int W_,
    unsigned int P_,
    unsigned int framerate,
    float bit_r,
    std::string debug_slide_dir,
    bool debug_logs_on
)
{
    cout <<  "H = " << H_ << ", W = " << W_ << ", P = " << P_ << "\n";
    memset(ctx, 0, sizeof(context_t));
    int set_id = 0;

    ParamSet param_set;
    setEncodingParams(param_set, set_id);

    bit_r = param_set.bitrate;
    ctx->bitrate = int(bit_r * H_ * W_ * 4);
    ctx->peak_bitrate = 2 * ctx->bitrate;

    cout<< "input bit_r = " << bit_r << "\n";
    cout<< "total bit_r = " << ctx->bitrate << "\n";
    cout<< "peak_bitrate = " << ctx->peak_bitrate << "\n";

    std::cout << "Set #" << set_id << " loaded.\n";
    std::cout << "iframe_interval = " << param_set.iframe_interval << "\n";
    std::cout << "idr_interval = " << param_set.idr_interval << "\n";
    std::cout << "num_b_frames = " << param_set.num_b_frames << "\n";
    std::cout << "Min QP I = " << param_set.nMinQpI << "\n";
    std::cout << "Max QP I = " << param_set.nMaxQpI << "\n";
    std::cout << "Min QP P = " << param_set.nMinQpP << "\n";
    std::cout << "Max QP P = " << param_set.nMaxQpP << "\n";
    std::cout << "Min QP B = " << param_set.nMinQpB << "\n";
    std::cout << "Max QP B = " << param_set.nMaxQpB << "\n";
    std::cout << "Session Max QP = " << param_set.sMaxQp << "\n";

    ctx->insert_vui = true;
    ctx->stats = false;
    ctx->enableGDR = false;
    ctx->enableROI = false;
    ctx->bnoIframe = false;
    ctx->bReconCrc = false;
    ctx->externalRPS = false;
    ctx->use_gold_crc = false;
    ctx->is_semiplanar = false;
    ctx->enable_initQP = true;
    ctx->enable_av1tile = false;
    ctx->enableLossless = false;
    ctx->externalRCHints = false;
    ctx->bGapsInFrameNumAllowed = false;
    ctx->ppe_init_params.enable_ppe = false;
    ctx->ppe_init_params.wait_time_ms = -1;
    ctx->ppe_init_params.feature_flags = V4L2_PPE_FEATURE_NONE;
    ctx->ppe_init_params.enable_profiler = 0;
    ctx->ppe_init_params.taq_max_qp_delta = 5;
    ctx->cs = V4L2_COLORSPACE_RAW;
    ctx->raw_pixfmt = V4L2_PIX_FMT_YUV420M;
    ctx->encoder_pixfmt = V4L2_PIX_FMT_H265;
    ctx->output_memory_type = V4L2_MEMORY_DMABUF;
    ctx->ratecontrol = V4L2_MPEG_VIDEO_BITRATE_MODE_VBR;
    ctx->level =  V4L2_MPEG_VIDEO_H265_LEVEL_6_2_HIGH_TIER; 
    ctx->profile = V4L2_MPEG_VIDEO_H265_PROFILE_MAINSTILLPICTURE;

    if (!bit_r) ctx->enableLossless = true;
    ctx->gdr_num_frames = 1;
    ctx->gdr_out_frame_number = 0xffffffff;
    ctx->gdr_start_frame_number = 1;
    ctx->nH265PocLsbBits = 128;
    ctx->iframe_interval = param_set.iframe_interval;
    ctx->idr_interval = param_set.idr_interval;
    ctx->level = -1;
    ctx->fps_n = framerate;
    ctx->fps_d = 1;
    ctx->num_b_frames = param_set.num_b_frames;
    ctx->nMinQpI = param_set.nMinQpI;
    ctx->nMaxQpI = param_set.nMaxQpI;
    ctx->nMinQpP = param_set.nMinQpP;
    ctx->nMaxQpP = param_set.nMaxQpP;
    ctx->nMinQpB = param_set.nMinQpB;
    ctx->nMaxQpB = param_set.nMaxQpB;
    ctx->sMaxQp = param_set.sMaxQp;
    ctx->input_metadata = true;
    ctx->stress_test = 0;
    ctx->output_memory_type = V4L2_MEMORY_DMABUF;
    ctx->cs = V4L2_COLORSPACE_SMPTE170M;
    ctx->copy_timestamp = true;
    ctx->sar_width = 0;
    ctx->sar_height = 0;
    ctx->start_ts = 0;
    ctx->max_perf = 0;
    ctx->blocking_mode = 1;
    ctx->startf = 0;
    ctx->num_output_buffers = 1;
    ctx->num_frames_to_encode = -1;
    ctx->poc_type = 0;
    ctx->chroma_format_idc = -1;
    ctx->bit_depth = 8;

    ctx->IinitQP = 0;
    ctx->PinitQP = 0;
    ctx->BinitQP = 0;
    ctx->enable_ratecontrol = true;
    ctx->log2_num_av1rows = 0;
    ctx->log2_num_av1cols = 0;
    ctx->enable_av1ssimrdo = (uint8_t)-1;
    ctx->disable_av1cdfupdate = (uint8_t)-1;
}


bool Encoder::init_encoder(
    context_t& ctx, 
    unsigned int H_,
    unsigned int W_,
    unsigned int P_,
    unsigned int framerate,
    float bit_r,
    const char* output_video_path,
    std::string debug_slide_dir,
    bool debug_logs_on
)
{
    int ret = 0;
    int error = 0;
    bool eos = false;

    set_defaults(&ctx, H_, W_, P_, framerate, bit_r, debug_slide_dir, debug_logs_on);
    ctx.width = W_;
    ctx.height = H_;
    ctx.out_file_path = strdup(output_video_path);
    pthread_setname_np(pthread_self(),"EncOutPlane");
    if (ctx.encoder_pixfmt == V4L2_PIX_FMT_H265)
    {
        if (ctx.width < 144 || ctx.height < 144)
        {
            cout << "Height/Width should be > 144 for H.265\n";
            return false;
        }
    }

    if (!ctx.stats)
    {
        /* Open output file for encoded bitstream */
        ctx.out_file = new ofstream(ctx.out_file_path);
        if (!ctx.out_file->is_open())
        {   
            cout<< "Could not open output file\n";
            return false;
        }
    }

    if (ctx.blocking_mode)
    {
        cout << "Creating Encoder in blocking mode \n";
        ctx.enc = NvVideoEncoder::createVideoEncoder("enc0");
    }

    if (ctx.stats)
    {
        ctx.enc->enableProfiling();
    }

    if (log_level >= LOG_LEVEL_DEBUG)
            cout << "Encode pixel format :" << get_pixfmt_string(ctx.encoder_pixfmt) << endl;

    ret = ctx.enc->setCapturePlaneFormat(ctx.encoder_pixfmt, ctx.width, ctx.height, 2 * ctx.peak_bitrate);

    if(ret < 0)
    {
        cout<<"Could not set capture plane format\n";
        return false;
    }

    if (ctx.encoder_pixfmt == V4L2_PIX_FMT_H265)
    {
        switch (ctx.profile)
        {
            case V4L2_MPEG_VIDEO_H265_PROFILE_MAIN10:
            {
                ctx.raw_pixfmt = V4L2_PIX_FMT_P010M;
                ctx.is_semiplanar = true;
                ctx.bit_depth = 10;
                break;
            }
            case V4L2_MPEG_VIDEO_H265_PROFILE_MAIN:
            {
                if (ctx.is_semiplanar)
                    ctx.raw_pixfmt = V4L2_PIX_FMT_NV12M;
                else
                    ctx.raw_pixfmt = V4L2_PIX_FMT_YUV420M;
                if (ctx.chroma_format_idc == 3)
                {
                    if (ctx.bit_depth == 10 && ctx.is_semiplanar)
                        ctx.raw_pixfmt = V4L2_PIX_FMT_NV24_10LE;
                    if (ctx.bit_depth == 8)
                    {
                        if (ctx.is_semiplanar)
                            ctx.raw_pixfmt = V4L2_PIX_FMT_NV24M;
                        else
                            ctx.raw_pixfmt = V4L2_PIX_FMT_YUV444M;
                    }
                }
            }
                break;
            default:
                ctx.raw_pixfmt = V4L2_PIX_FMT_YUV420M;
        }
    }
    if (log_level >= LOG_LEVEL_DEBUG)
            cout << "Raw pixel format :" << get_pixfmt_string(ctx.raw_pixfmt) << endl;
    ret = ctx.enc->setOutputPlaneFormat(ctx.raw_pixfmt, ctx.width, ctx.height);

    if(ret < 0)
    {
        cout<< "Could not set output plane format\n";
        return false;
    }

    if (ctx.num_frames_to_encode)
    {
        ret = ctx.enc->setFramesToEncode(ctx.num_frames_to_encode);
        TEST_ERROR(ret < 0, "Could not set frames to encode", cleanup);
    }

    ret = ctx.enc->setBitrate(ctx.bitrate);
    TEST_ERROR(ret < 0, "Could not set encoder bit rate", cleanup);

    if (ctx.encoder_pixfmt == V4L2_PIX_FMT_H265)
    {
        ret = ctx.enc->setProfile(ctx.profile);
        TEST_ERROR(ret < 0, "Could not set encoder profile", cleanup);

        if (ctx.level != (uint32_t)-1)
        {
            ret = ctx.enc->setLevel(ctx.level);
            TEST_ERROR(ret < 0, "Could not set encoder level", cleanup);
        }

        if (ctx.chroma_format_idc != (uint8_t)-1)
        {
            ret = ctx.enc->setChromaFactorIDC(ctx.chroma_format_idc);
            TEST_ERROR(ret < 0, "Could not set chroma_format_idc", cleanup);
        }
    }

    if (ctx.enable_initQP)
    {
        cout << "Setting init QP values\n";
        ret = ctx.enc->setInitQP(ctx.IinitQP, ctx.PinitQP, ctx.BinitQP);
        TEST_ERROR(ret < 0, "Could not set encoder init QP", cleanup);
    }

    if (ctx.enableLossless)
    {
        ret = ctx.enc->setLossless(ctx.enableLossless);
        TEST_ERROR(ret < 0, "Could not set lossless encoding", cleanup);
    }
    else if (!ctx.enable_ratecontrol)
    {
        ret = ctx.enc->setConstantQp(ctx.enable_ratecontrol);
        TEST_ERROR(ret < 0, "Could not set encoder constant QP", cleanup);
    }
    else
    {
        ret = ctx.enc->setRateControlMode(ctx.ratecontrol);
        TEST_ERROR(ret < 0, "Could not set encoder rate control mode", cleanup);
        if (ctx.ratecontrol == V4L2_MPEG_VIDEO_BITRATE_MODE_VBR) {
            uint32_t peak_bitrate;
            if (ctx.peak_bitrate < ctx.bitrate)
                peak_bitrate = 1.2f * ctx.bitrate;
            else
                peak_bitrate = ctx.peak_bitrate;
            ret = ctx.enc->setPeakBitrate(peak_bitrate);
            TEST_ERROR(ret < 0, "Could not set encoder peak bit rate", cleanup);
        }
    }

    if (ctx.poc_type)
    {
        ret = ctx.enc->setPocType(ctx.poc_type);
        TEST_ERROR(ret < 0, "Could not set Picture Order Count value", cleanup);
    }

    cout << "IDR interval = " << ctx.idr_interval << endl;
    ret = ctx.enc->setIDRInterval(ctx.idr_interval);
    TEST_ERROR(ret < 0, "Could not set encoder IDR interval", cleanup);

    cout << "I-Frame interval = " << ctx.iframe_interval << endl;
    ret = ctx.enc->setIFrameInterval(ctx.iframe_interval);
    TEST_ERROR(ret < 0, "Could not set encoder I-Frame interval", cleanup);

    ret = ctx.enc->setFrameRate(ctx.fps_n, ctx.fps_d);
    TEST_ERROR(ret < 0, "Could not set framerate", cleanup);

    if (ctx.temporal_tradeoff_level)
    {
        ret = ctx.enc->setTemporalTradeoff(ctx.temporal_tradeoff_level);
        TEST_ERROR(ret < 0, "Could not set temporal tradeoff level", cleanup);
    }

    if (ctx.slice_length)
    {
        ret = ctx.enc->setSliceLength(ctx.slice_length_type,
                ctx.slice_length);
        TEST_ERROR(ret < 0, "Could not set slice length params", cleanup);
    }

    if (ctx.enable_slice_level_encode)
    {
        /* Enable slice level encode for encoder */
        ret = ctx.enc->setSliceLevelEncode(true);
        TEST_ERROR(ret < 0, "Could not set slice level encode", cleanup);
    }

    if (ctx.hw_preset_type)
    {
        ret = ctx.enc->setHWPresetType(ctx.hw_preset_type);
        TEST_ERROR(ret < 0, "Could not set encoder HW Preset Type", cleanup);
    }

    if (ctx.virtual_buffer_size)
    {
        ret = ctx.enc->setVirtualBufferSize(ctx.virtual_buffer_size);
        TEST_ERROR(ret < 0, "Could not set virtual buffer size", cleanup);
    }

    if (ctx.slice_intrarefresh_interval)
    {
        ret = ctx.enc->setSliceIntrarefresh(ctx.slice_intrarefresh_interval);
        TEST_ERROR(ret < 0, "Could not set slice intrarefresh interval", cleanup);
    }

    if (ctx.insert_sps_pps_at_idr)
    {
        ret = ctx.enc->setInsertSpsPpsAtIdrEnabled(true);
        TEST_ERROR(ret < 0, "Could not set insertSPSPPSAtIDR", cleanup);
    }

    if (ctx.disable_cabac)
    {
        ret = ctx.enc->setCABAC(false);
        TEST_ERROR(ret < 0, "Could not set disable CABAC", cleanup);
    }

    if (ctx.sar_width)
    {
        ret = ctx.enc->setSampleAspectRatioWidth(ctx.sar_width);
        TEST_ERROR(ret < 0, "Could not set Sample Aspect Ratio width", cleanup);
    }

    if (ctx.sar_height)
    {
        ret = ctx.enc->setSampleAspectRatioHeight(ctx.sar_height);
        TEST_ERROR(ret < 0, "Could not set Sample Aspect Ratio height", cleanup);
    }

    if (ctx.insert_vui)
    {
        ret = ctx.enc->setInsertVuiEnabled(true);
        TEST_ERROR(ret < 0, "Could not set insertVUI", cleanup);
    }

    if (ctx.enable_extended_colorformat)
    {
        ret = ctx.enc->setExtendedColorFormat(true);
        TEST_ERROR(ret < 0, "Could not set extended color format", cleanup);
    }

    if (ctx.insert_aud)
    {
        ret = ctx.enc->setInsertAudEnabled(true);
        TEST_ERROR(ret < 0, "Could not set insertAUD", cleanup);
    }

    if (ctx.alliframes)
    {
        ret = ctx.enc->setAlliFramesEncode(true);
        TEST_ERROR(ret < 0, "Could not set Alliframes encoding", cleanup);
    }

    cout << "Num B frames = " << ctx.num_b_frames << endl;
    if (ctx.num_b_frames != (uint32_t) -1)
    {
        cout << "Setting number of B frames\n";
        ret = ctx.enc->setNumBFrames(ctx.num_b_frames);
        TEST_ERROR(ret < 0, "Could not set number of B Frames", cleanup);
    }

    if ((ctx.nMinQpI != (uint32_t)QP_RETAIN_VAL) ||
        (ctx.nMaxQpI != (uint32_t)QP_RETAIN_VAL) ||
        (ctx.nMinQpP != (uint32_t)QP_RETAIN_VAL) ||
        (ctx.nMaxQpP != (uint32_t)QP_RETAIN_VAL) ||
        (ctx.nMinQpB != (uint32_t)QP_RETAIN_VAL) ||
        (ctx.nMaxQpB != (uint32_t)QP_RETAIN_VAL))
    {
        cout << "Setting QP range values for I/P/B frames." << endl;
        cout << "Min QP I: " << ctx.nMinQpI << " Max QP I: " << ctx.nMaxQpI << endl;
        cout << "Min QP P: " << ctx.nMinQpP << " Max QP P: " << ctx.nMaxQpP << endl;
        cout << "Min QP B: " << ctx.nMinQpB << " Max QP B: " << ctx.nMaxQpB << endl;
        ret = ctx.enc->setQpRange(ctx.nMinQpI, ctx.nMaxQpI, ctx.nMinQpP,
                ctx.nMaxQpP, ctx.nMinQpB, ctx.nMaxQpB);
        TEST_ERROR(ret < 0, "Could not set quantization parameters", cleanup);
    }

    if (ctx.max_perf)
    {
        ret = ctx.enc->setMaxPerfMode(ctx.max_perf);
        TEST_ERROR(ret < 0, "Error while setting encoder to max perf", cleanup);
    }

    if (ctx.dump_mv)
    {
        ret = ctx.enc->enableMotionVectorReporting();
        TEST_ERROR(ret < 0, "Could not enable motion vector reporting", cleanup);
    }

    if (ctx.bnoIframe) {
        ctx.iframe_interval = ((1<<31) + 1);
        ret = ctx.enc->setIFrameInterval(ctx.iframe_interval);
        TEST_ERROR(ret < 0, "Could not set encoder I-Frame interval", cleanup);
    }

    if (ctx.enableROI) {
        v4l2_enc_enable_roi_param VEnc_enable_ext_roi_ctrl;
        VEnc_enable_ext_roi_ctrl.bEnableROI = ctx.enableROI;
        ret = ctx.enc->enableROI(VEnc_enable_ext_roi_ctrl);
        TEST_ERROR(ret < 0, "Could not enable ROI", cleanup);
    }

    if (ctx.bReconCrc) {
        v4l2_enc_enable_reconcrc_param VEnc_enable_recon_crc_ctrl;
        VEnc_enable_recon_crc_ctrl.bEnableReconCRC = ctx.bReconCrc;
        ret = ctx.enc->enableReconCRC(VEnc_enable_recon_crc_ctrl);
        TEST_ERROR(ret < 0, "Could not enable Recon CRC", cleanup);
    }

    if (ctx.externalRPS)
    {
        v4l2_enc_enable_ext_rps_ctr VEnc_enable_ext_rps_ctrl;
        VEnc_enable_ext_rps_ctrl.bEnableExternalRPS = ctx.externalRPS;
        if (ctx.encoder_pixfmt == V4L2_PIX_FMT_H265) {
            VEnc_enable_ext_rps_ctrl.nH265PocLsbBits = ctx.nH265PocLsbBits;
        }
        ret = ctx.enc->enableExternalRPS(VEnc_enable_ext_rps_ctrl);
        TEST_ERROR(ret < 0, "Could not enable external RPS", cleanup);
    }

    if (ctx.num_reference_frames)
    {
        ret = ctx.enc->setNumReferenceFrames(ctx.num_reference_frames);
        TEST_ERROR(ret < 0, "Could not set num reference frames", cleanup);
    }

    if (ctx.externalRCHints) {
        v4l2_enc_enable_ext_rate_ctr VEnc_enable_ext_rate_ctrl;
        VEnc_enable_ext_rate_ctrl.bEnableExternalPictureRC = ctx.externalRCHints;
        VEnc_enable_ext_rate_ctrl.nsessionMaxQP = ctx.sMaxQp;
        ret = ctx.enc->enableExternalRC(VEnc_enable_ext_rate_ctrl);
        TEST_ERROR(ret < 0, "Could not enable external RC", cleanup);
    }

    switch(ctx.output_memory_type)
    {
        case V4L2_MEMORY_MMAP:
            ret = ctx.enc->output_plane.setupPlane(V4L2_MEMORY_MMAP, ctx.num_output_buffers, true, false);
            TEST_ERROR(ret < 0, "Could not setup output plane", cleanup);
            break;

        case V4L2_MEMORY_USERPTR:
            ret = ctx.enc->output_plane.setupPlane(V4L2_MEMORY_USERPTR, ctx.num_output_buffers, false, true);
            TEST_ERROR(ret < 0, "Could not setup output plane", cleanup);
            break;

        case V4L2_MEMORY_DMABUF:
            ret = setup_output_dmabuf(&ctx, ctx.num_output_buffers);
            TEST_ERROR(ret < 0, "Could not setup plane", cleanup);
            break;
        default :
            TEST_ERROR(true, "Not a valid plane", cleanup);
    }

    ret = ctx.enc->capture_plane.setupPlane(V4L2_MEMORY_MMAP, ctx.num_output_buffers,
        true, false);
    TEST_ERROR(ret < 0, "Could not setup capture plane", cleanup);

    ret = ctx.enc->subscribeEvent(V4L2_EVENT_EOS,0,0);
    TEST_ERROR(ret < 0, "Could not subscribe EOS event", cleanup);

    printf("=============> ctx.b_use_enc_cmd: %i\n", ctx.b_use_enc_cmd);
    
    ret = ctx.enc->output_plane.setStreamStatus(true);
    TEST_ERROR(ret < 0, "Error in output plane streamon", cleanup);

    ret = ctx.enc->capture_plane.setStreamStatus(true);
    TEST_ERROR(ret < 0, "Error in capture plane streamon", cleanup);

    if (ctx.blocking_mode)
    {
        ctx.enc->capture_plane.setDQThreadCallback(encoder_capture_plane_dq_callback);
        ctx.enc->capture_plane.startDQThread(&ctx);
    }

    for (uint32_t i = 0; i < ctx.enc->capture_plane.getNumBuffers(); i++)
    {
        struct v4l2_buffer v4l2_buf;
        struct v4l2_plane planes[MAX_PLANES];

        memset(&v4l2_buf, 0, sizeof(v4l2_buf));
        memset(planes, 0, MAX_PLANES * sizeof(struct v4l2_plane));

        v4l2_buf.index = i;
        v4l2_buf.m.planes = planes;

        ret = ctx.enc->capture_plane.qBuffer(v4l2_buf, NULL);
        if (ret < 0)
        {
            cerr << "Error while queueing buffer at capture plane" << endl;
            abort_enc(&ctx);
            goto cleanup;
        }
    }

    if (ctx.copy_timestamp)
    {
        ctx.timestamp = (ctx.start_ts * MICROSECOND_UNIT);
        ctx.timestampincr = (MICROSECOND_UNIT * 16) / ((uint32_t) (ctx.fps_n * 16));
    }

    if(ctx.ppe_init_params.enable_ppe)
    {
        ret = ctx.enc->setPPEInitParams(ctx.ppe_init_params);
        if (ret < 0){
            cerr << "Error calling setPPEInitParams" << endl;
        }
    }

    return true;

cleanup:
    if (ctx.enc && ctx.enc->isInError())
    {
        cerr << "Encoder is in error" << endl;
        error = 1;
    }
    if (ctx.got_error)
    {
        error = 1;
    }

    if(ctx.output_memory_type == V4L2_MEMORY_DMABUF && ctx.enc)
    {
        for (uint32_t i = 0; i < ctx.enc->output_plane.getNumBuffers(); i++)
        {
            ret = ctx.enc->output_plane.unmapOutputBuffers(i, ctx.output_plane_fd[i]);
            if (ret < 0)
            {
                cerr << "Error while unmapping buffer at output plane" << endl;
                goto cleanup;
            }

            ret = NvBufSurf::NvDestroy(ctx.output_plane_fd[i]);
            ctx.output_plane_fd[i] = -1;
            if(ret < 0)
            {
                cerr << "Failed to Destroy NvBuffer\n" << endl;
            }
        }
    }

    delete ctx.out_file;
    return true;
}


void Encoder::encode_frame(
    context_t& ctx,
    const unsigned char* color_img,
    unsigned int frNum,
    bool finished_frames
)
{
    int ret = 0;
    int error = 0;
    bool eos = false;
    unsigned char * tmp_arr;

    uint32_t i = frNum;

    if ( i < ctx.enc->output_plane.getNumBuffers() )
    {
        struct v4l2_buffer v4l2_buf;
        struct v4l2_plane planes[MAX_PLANES];
        NvBuffer *buffer = ctx.enc->output_plane.getNthBuffer(i);

        memset(&v4l2_buf, 0, sizeof(v4l2_buf));
        memset(planes, 0, MAX_PLANES * sizeof(struct v4l2_plane));

        v4l2_buf.index = i;
        v4l2_buf.m.planes = planes;
        
        if(ctx.output_memory_type == V4L2_MEMORY_DMABUF)
        {
            v4l2_buf.type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
            v4l2_buf.memory = V4L2_MEMORY_DMABUF;
            ret = ctx.enc->output_plane.mapOutputBuffers(v4l2_buf, ctx.output_plane_fd[i]);

            if (ret < 0)
            {
                cerr << "Error while mapping buffer at output plane" << endl;
                abort_enc(&ctx);
                goto cleanup;
            }
        }

        if(ctx.startf)
        {
            uint32_t i = 0, frame_size = 0;

            for (i = 0; i < buffer->n_planes; i++)
            {
                frame_size += buffer->planes[i].fmt.bytesperpixel * buffer->planes[i].fmt.width * buffer->planes[i].fmt.height;
            }
            frame_size = frame_size * ctx.startf;
            ctx.startf = 0;
        }

        if(ctx.output_memory_type == V4L2_MEMORY_DMABUF || ctx.output_memory_type == V4L2_MEMORY_MMAP)
        {
            NvBufSurface *nvbuf_surf = 0;
            ret = NvBufSurfaceFromFd(buffer->planes[0].fd, (void**)(&nvbuf_surf));
            if (ret < 0)
            {
                cerr << "Error while NvBufSurfaceFromFd" << endl;
                abort_enc(&ctx);
                goto cleanup;
            }

            ret = NvBufSurfaceMapEglImage(nvbuf_surf, -1);
            if (ret != CUDA_SUCCESS) std::cerr << "Error in NvBufSurfaceMapEglImage: " << ret << std::endl;
            
            NvBufSurfaceParams *sfparams = &nvbuf_surf->surfaceList[0];
            NvBufSurfacePlaneParams *nvspp = &nvbuf_surf->surfaceList[0].planeParams;
            CUgraphicsResource pResource;
            CUresult result = cuGraphicsEGLRegisterImage(&pResource, sfparams->mappedAddr.eglImage, CU_GRAPHICS_MAP_RESOURCE_FLAGS_WRITE_DISCARD);
            if (result != CUDA_SUCCESS) std::cerr << "Error in cuGraphicsEGLRegisterImage: " << result << std::endl;
    
            CUeglFrame eglFrame;
            result = cuGraphicsResourceGetMappedEglFrame( &eglFrame, pResource, 0, 0 );
            if (result != CUDA_SUCCESS) std::cerr << "Error in cuGraphicsResourceGetMappedEglFrame: " << result << std::endl;

            RGBto3ChYUV420(
                color_img,
                reinterpret_cast<unsigned char*>(eglFrame.frame.pPitch[0]),
                reinterpret_cast<unsigned char*>(eglFrame.frame.pPitch[1]),
                reinterpret_cast<unsigned char*>(eglFrame.frame.pPitch[2]),
                nvspp->height[0],
                nvspp->width[0],
                nvspp->width[0],
                nvspp->pitch[0],
                nvspp->pitch[0] / 2
            );

            for (uint32_t j = 0 ; j < buffer->n_planes; j++)
            {    
                NvBuffer::NvBufferPlane &plane = buffer->planes[j];
                plane.bytesused = 0;
                plane.data = reinterpret_cast<unsigned char*>(eglFrame.frame.pPitch[j]);
                plane.bytesused = nvspp->pitch[j] * nvspp->height[j];
            }
           
            cuGraphicsUnregisterResource(pResource);
            NvBufSurfaceUnMapEglImage(nvbuf_surf, -1);

            ret = NvBufSurfaceSyncForDevice(nvbuf_surf, 0, -1);
            if (ret < 0)
            {
                cerr << "Error while NvBufSurfaceSyncForDevice at output plane for V4L2_MEMORY_DMABUF" << endl;
                abort_enc(&ctx);
                goto cleanup;
            }
        }
        
        if (ctx.copy_timestamp)
        {
            v4l2_buf.flags |= V4L2_BUF_FLAG_TIMESTAMP_COPY;
            ctx.timestamp += ctx.timestampincr;
            v4l2_buf.timestamp.tv_sec = ctx.timestamp / (MICROSECOND_UNIT);
            v4l2_buf.timestamp.tv_usec = ctx.timestamp % (MICROSECOND_UNIT);
        }

        if(ctx.output_memory_type == V4L2_MEMORY_DMABUF)
        {
            for (uint32_t j = 0 ; j < buffer->n_planes ; j++)
            {
                v4l2_buf.m.planes[j].bytesused = buffer->planes[j].bytesused;
            }
        }
        /* encoder qbuffer for output plane */
        ret = ctx.enc->output_plane.qBuffer(v4l2_buf, NULL);
        if (ret < 0)
        {
            cerr << "Error while queueing buffer at output plane" << endl;
            abort_enc(&ctx);
            goto cleanup;
        }
        if(ctx.num_frames_to_encode > 0)
        {
            ctx.num_frames_to_encode--;
        }
        if (v4l2_buf.m.planes[0].bytesused == 0)
        {
            cerr << "File read complete." << endl;
            eos = true;
            goto cleanup;
        }
        ctx.input_frames_queued_count++;
    }
    // if (ctx.blocking_mode)
    else
    {
        eos = true;
        ctx.got_eos = true;

        struct v4l2_buffer v4l2_buf;
        struct v4l2_plane planes[MAX_PLANES];
        NvBuffer *buffer;

        memset(&v4l2_buf, 0, sizeof(v4l2_buf));
        memset(planes, 0, sizeof(planes));

        v4l2_buf.m.planes = planes;

        if (ctx.enc->output_plane.dqBuffer(v4l2_buf, &buffer, NULL, 10) < 0)
        {
            cerr << "ERROR while DQing buffer at output plane" << endl;
            abort_enc(&ctx);
            goto cleanup;
        }

        if(ctx.output_memory_type == V4L2_MEMORY_DMABUF || ctx.output_memory_type == V4L2_MEMORY_MMAP)
        {
            NvBufSurface *nvbuf_surf = 0;
            ret = NvBufSurfaceFromFd(buffer->planes[0].fd, (void**)(&nvbuf_surf));
            if (ret < 0)
            {
                cerr << "Error while NvBufSurfaceFromFd" << endl;
                abort_enc(&ctx);
                goto cleanup;
            }

            ret = NvBufSurfaceMapEglImage(nvbuf_surf, -1);
            if (ret != CUDA_SUCCESS) std::cerr << "Error in NvBufSurfaceMapEglImage: " << ret << std::endl;
            NvBufSurfaceParams *sfparams = &nvbuf_surf->surfaceList[0];
            NvBufSurfacePlaneParams *nvspp = &nvbuf_surf->surfaceList[0].planeParams;
        
            CUgraphicsResource pResource;
            CUresult result = cuGraphicsEGLRegisterImage(&pResource, sfparams->mappedAddr.eglImage, CU_GRAPHICS_MAP_RESOURCE_FLAGS_WRITE_DISCARD);
            if (result != CUDA_SUCCESS) std::cerr << "Error in cuGraphicsEGLRegisterImage 2: " << result << std::endl;
            CUeglFrame eglFrame;
            result = cuGraphicsResourceGetMappedEglFrame( &eglFrame, pResource, 0, 0 );
            if (result != CUDA_SUCCESS) std::cerr << "Error in cuGraphicsResourceGetMappedEglFrame 2: " << result << std::endl;

            ret = NvBufSurfaceSyncForDevice(nvbuf_surf, 0, -1);
            if (ret < 0)
            {
                cerr << "Error while NvBufSurfaceSyncForDevice at output plane for V4L2_MEMORY_DMABUF" << endl;
                abort_enc(&ctx);
                goto cleanup;
            }

            RGBto3ChYUV420(
                color_img,
                reinterpret_cast<unsigned char*>(eglFrame.frame.pPitch[0]),
                reinterpret_cast<unsigned char*>(eglFrame.frame.pPitch[1]),
                reinterpret_cast<unsigned char*>(eglFrame.frame.pPitch[2]),
                nvspp->height[0],
                nvspp->width[0],
                nvspp->width[0],
                nvspp->pitch[0],
                nvspp->pitch[0] / 2
            );

            for (uint32_t j = 0 ; j < buffer->n_planes; j++)
            {    
                NvBuffer::NvBufferPlane &plane = buffer->planes[j];
                plane.bytesused = 0;
                plane.data = reinterpret_cast<unsigned char*>(eglFrame.frame.pPitch[j]);
                plane.bytesused = nvspp->pitch[j] * nvspp->height[j];
            }

            cuGraphicsUnregisterResource(pResource);
            NvBufSurfaceUnMapEglImage(nvbuf_surf, -1);
        }

        if (ctx.copy_timestamp)
        {
          v4l2_buf.flags |= V4L2_BUF_FLAG_TIMESTAMP_COPY;
          ctx.timestamp += ctx.timestampincr;
          v4l2_buf.timestamp.tv_sec = ctx.timestamp / (MICROSECOND_UNIT);
          v4l2_buf.timestamp.tv_usec = ctx.timestamp % (MICROSECOND_UNIT);
        }

        if(!ctx.num_frames_to_encode)
        {
            buffer->planes[0].bytesused = buffer->planes[1].bytesused = buffer->planes[2].bytesused = 0;
        }

        if(ctx.output_memory_type == V4L2_MEMORY_DMABUF)
        {
            for (uint32_t j = 0 ; j < buffer->n_planes ; j++)
            {
                v4l2_buf.m.planes[j].bytesused = buffer->planes[j].bytesused;
            }
        }
        /* encoder qbuffer for output plane */
        ret = ctx.enc->output_plane.qBuffer(v4l2_buf, NULL);
        if (ret < 0)
        {
            cerr << "Error while queueing buffer at output plane" << endl;
            abort_enc(&ctx);
            goto cleanup;
        }
        if(ctx.num_frames_to_encode > 0)
        {
            ctx.num_frames_to_encode--;
        }
        ctx.input_frames_queued_count++;
        if (v4l2_buf.m.planes[0].bytesused == 0)
        {
            cerr << "File read complete." << endl;
            eos = true;
            ctx.got_eos = true;
        }
    }

    if (ctx.stats)
    {
        ctx.enc->printProfilingStats(cout);
    }

    if(!finished_frames) return;

cleanup:
    if (ctx.enc && ctx.enc->isInError())
    {
        cerr << "Encoder is in error" << endl;
        error = 1;
    }
    if (ctx.got_error)
    {
        error = 1;
    }

    if(ctx.output_memory_type == V4L2_MEMORY_DMABUF && ctx.enc)
    {
        for (uint32_t i = 0; i < ctx.enc->output_plane.getNumBuffers(); i++)
        {
            ret = ctx.enc->output_plane.unmapOutputBuffers(i, ctx.output_plane_fd[i]);
            if (ret < 0)
            {
                cerr << "Error while unmapping buffer at output plane" << endl;
                goto cleanup;
            }
            ret = NvBufSurf::NvDestroy(ctx.output_plane_fd[i]);
            ctx.output_plane_fd[i] = -1;
            if(ret < 0)
            {
                cerr << "Failed to Destroy NvBuffer\n" << endl;
            }
        }
    }
    delete ctx.out_file;
}

int Encoder::enqueue_end_frame(context_t &ctx)
{
    struct v4l2_buffer v4l2_buf;
    struct v4l2_plane planes[MAX_PLANES];
    NvBuffer *buffer;
    int ret = 0;

    memset(&v4l2_buf, 0, sizeof(v4l2_buf));
    memset(planes, 0, sizeof(planes));

    v4l2_buf.m.planes = planes;
    if (ctx.enc->output_plane.dqBuffer(v4l2_buf, &buffer, NULL, 10) < 0)
    {
        cerr << "ERROR while DQing buffer at output plane" << endl;
        abort_enc(&ctx);
        return -1;
    }
    for (uint32_t j = 0 ; j < buffer->n_planes ; j++)
    {        
        NvBufSurface *nvbuf_surf = 0;
        ret = NvBufSurfaceFromFd(buffer->planes[j].fd, (void**)(&nvbuf_surf));
        if (ret < 0)
        {
            cerr << "Error while NvBufSurfaceFromFd" << endl;
            abort_enc(&ctx);
            return -1;
        }
        ret = NvBufSurfaceSyncForDevice(nvbuf_surf, 0, j);
        if (ret < 0)
        {
            cerr << "Error while NvBufSurfaceSyncForDevice at output plane for V4L2_MEMORY_DMABUF" << endl;
            abort_enc(&ctx);
            return -1;
        }
    }

    for (uint32_t j = 0 ; j < buffer->n_planes ; j++)
    {
        v4l2_buf.m.planes[j].bytesused = buffer->planes[j].bytesused;
    }
    
    ret = ctx.enc->output_plane.qBuffer(v4l2_buf, NULL);
    if (ret < 0)
    {
        cerr << "Error while queueing buffer at output plane" << endl;
        abort_enc(&ctx);
        return -1;
    }
    ctx.input_frames_queued_count++;
    if (v4l2_buf.m.planes[0].bytesused == 0)
    {
        cerr << "Input frames have all been generated and placed in buffers." << endl;
        ctx.got_eos = true;
        return 0;
    }
}

void CloseCrc(Crc **phCrc)
{
    if (*phCrc)
        free (*phCrc);
}

bool Encoder::cleanups(context_t &ctx)
{
    if (ctx.enc && ctx.enc->isInError())
    {
        cerr << "Encoder is in error  1" << endl;
    }
    if (ctx.got_error)
    {
        cerr << "Encoder is in error  2" << endl;
    }

    if (ctx.pBitStreamCrc)
    {
        char *pgold_crc = ctx.gold_crc;
        Crc *pout_crc= ctx.pBitStreamCrc;
        char StrCrcValue[20];
        snprintf (StrCrcValue, 20, "%u", pout_crc->CrcValue);
        do {
               unsigned int len = strlen(pgold_crc);
               if (len == 0) break;
               if (pgold_crc[len-1] == '\n')
                   pgold_crc[len-1] = '\0';
               else if (pgold_crc[len-1] == '\r')
                   pgold_crc[len-1] = '\0';
               else
                   break;
        } while(1);

        if (strcmp (StrCrcValue, pgold_crc))
        {
            cout << "Error + Encoded CRC: " << StrCrcValue << " Gold CRC: " << pgold_crc << endl;
        }
        CloseCrc(&ctx.pBitStreamCrc);
    }
    int ret = 0;
    if(ctx.output_memory_type == V4L2_MEMORY_DMABUF && ctx.enc)
    {
        for (uint32_t i = 0; i < ctx.enc->output_plane.getNumBuffers(); i++)
        {
            ret = ctx.enc->output_plane.unmapOutputBuffers(i, ctx.output_plane_fd[i]);
            if (ret < 0)
            {
                cerr << "Error while unmapping buffer at output plane" << endl;
            }
            ret = NvBufSurf::NvDestroy(ctx.output_plane_fd[i]);
            ctx.output_plane_fd[i] = -1;
            if(ret < 0)
            {
                cerr << "Failed to Destroy NvBuffer\n" << endl;
                return ret;
            }
        }
    }
    delete ctx.enc;
    delete ctx.out_file;

    free(ctx.out_file_path);

    return true;
}


void Focus::video_encoder()
{    
    encoder_obj = new Encoder();

    context_t ctx;
    int height = orig_H;
    int width = orig_W;
    int pitch = encoder_obj->GetPitch(width, 256);
    
    int num_of_buffers = 40; 
    int framerate = 10;

    bool ret = encoder_obj->init_encoder(ctx, height, width, pitch, framerate, bit_r, output_video_path, debug_slide_dir, logs_on);
    unsigned long int y__siz = orig_H * orig_W * sizeof(unsigned char);
    unsigned long int u__siz = 0.25 * y__siz;
    unsigned long int yuv_siz = 1.5 * y__siz;
    unsigned char * yuv_tmp_img;
    cudaMalloc((void**)&yuv_tmp_img, yuv_siz);

    std::this_thread::sleep_for(std::chrono::milliseconds(1000)); 
    unsigned int vid_spot_count = 1;
    int all_frames_count = 0;
    float all_scanning_time = 0;
    vid_stat = 0;
    video_init = true;

    while(true)
    {
        if (abort_all) break;
        for (ushort j = 0 ; j < n_f_layers_g; j++)
        {
            long int col_adj_pt = j * 3 * orig_H * orig_W;
            unsigned char* colSrcPtr = fgpu->bgr_focused_undistorted + col_adj_pt;

            encoder_obj->encode_frame(
                ctx,
                colSrcPtr,
                all_frames_count,
                false
            );            
            all_frames_count++;
            enc_state[j] = 0;
        }

        cudaDeviceSynchronize();

        vid_spot_count++;

        if (vid_spot_count > desired_num_of_spots) break;
    }
    encoder_obj->enqueue_end_frame(ctx);
    ctx.enc->capture_plane.waitForDQThread(-1);
    encoder_obj->cleanups(ctx);

    cudaFree(yuv_tmp_img);
    delete encoder_obj;

    video_finished = true;
}

import traceback
from flask import make_response, jsonify, Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required
from turbojpeg import TurboJPEG
from .models import get_processor, remove_video_manager
from .utils import get_cached_slidedata

tile = Blueprint("tile", __name__)

tjpeg = TurboJPEG()


@tile.route("/unload/<slidename>", methods=["POST"])
@jwt_required(locations=["headers", "cookies"])
def unload_video(slidename):
    user_id = get_jwt_identity()
    remove_video_manager(user_id, slidename)
    return "Removed", 200


@tile.route("/metadata/<slidename>")
@jwt_required(locations=["headers", "cookies"])
def get_metadata(slidename):
    try:
        slidedata = get_cached_slidedata(slidename)
        dzi_margin = slidedata.dzi_params["dzi_margin"]
        dzi_block_size = slidedata.dzi_params["dzi_block_size"]
        width, height = slidedata.dzi_params["wsi_size"]

        response = make_response(
            jsonify(
                {
                    "tile_size": dzi_block_size,
                    "overlap": dzi_margin,
                    "width": width,
                    "height": height,
                }
            )
        )
        response.cache_control.private = True
        response.cache_control.max_age = 86400  # 1 day.
        return response
    except KeyError as e:
        return jsonify({"error": "Key error", "details": str(e)}), 404
    except FileNotFoundError as e:
        return jsonify({"error": "File not found", "details": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@tile.route("/tile/<slidename>/z<int:z>/dzi<int:dzi_level>/y<int:y>-x<int:x>")
@jwt_required(locations=["headers", "cookies"])
def get_tile_image(slidename, z, dzi_level, y, x):
    try:
        slidedata = get_cached_slidedata(slidename)
        if z < 0 or z > slidedata.num_layers - 1:
            error = f"z layer out of range. Expected 0 to {slidedata.num_layers - 1}. Got {z}"
            print(error)
            return jsonify({"error": error}), 400

        user_id = get_jwt_identity()

        processor = get_processor(user_id, slidename, dzi_level)
        image = processor.get_image(slidename, dzi_level, x, y, z)

        if image is None or image.size == 0:
            return "Tile empty.", 404

        jpeg = tjpeg.encode(image, quality=90)

        response = make_response(jpeg)
        response.headers["Content-Type"] = "image/jpeg"
        response.cache_control.private = True
        response.cache_control.max_age = 86400  # 1 day.
        return response
    except ValueError as e:
        print(f"[ERROR] ValueError: {e}")
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        print(f"[ERROR] KeyError: {e}")
        return jsonify({"error": str(e)}), 404
    except FileNotFoundError as e:
        print(f"[ERROR] FileNotFoundError: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        tr_txt = traceback.format_exc()
        print(f"[ERROR] Exception: {e}\nTraceback: {tr_txt}")
        return jsonify(
            {
                "error": "Internal server error",
                "details": str(e),
                "traceback": str(tr_txt),
            }
        ), 500

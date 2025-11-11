from pathlib import Path
from typing import Tuple

from napari_cci_annotator._settigns import Settings

#MODELS_DIR = "models"
MYELIN_MODEL_FILENAME = "latest_model.pt"
MYELIN_MODEL_PATH = 'myelin/' + MYELIN_MODEL_FILENAME

AXON_MODEL_FILENAME = "axon_model_20250512.pt"
AXON_MODEL_PATH = 'axons/' + AXON_MODEL_FILENAME
#AXON_MODEL_NAME = "stardist"

UNAXON_MODEL_FILENAME = "unaxon_model_1125.pt"
UNAXON_MODEL_PATH = 'unmyelinated_axons/' + UNAXON_MODEL_FILENAME


OPENVINO_MYELIN_MODEL_DIR_NAME = "latest_model_openvino_model/"
OPENVINO_MYELIN_MODEL_PATH = 'myelin/' + OPENVINO_MYELIN_MODEL_DIR_NAME

OPENVINO_AXON_MODEL_DIR_NAME = "axon_model_20250512_openvino_model/"
OPENVINO_AXONS_MODEL_PATH = 'axons/' + OPENVINO_AXON_MODEL_DIR_NAME

OPENVINO_UNAXON_MODEL_DIR_NAME = "unaxon_model_1125_openvino_model/"
OPENVINO_UNAXONS_MODEL_PATH = 'unmyelinated_axons/' + OPENVINO_AXON_MODEL_DIR_NAME

AXON_IMG_SIZE = 1024
MYELIN_IMG_SIZE = 1024
UNAXON_IMG_SIZE = 1024

OPENVINO_BACKEND_PREFIX = "OpenVINO"
OPENVINO_BACKEND_GPU = OPENVINO_BACKEND_PREFIX + "-GPU"
OPENVINO_BACKEND_CPU = OPENVINO_BACKEND_PREFIX + "-CPU"


def get_image_size(cell_type: str) -> int:
    cell_type_low = cell_type.lower()
    if cell_type_low == "axons":
        return AXON_IMG_SIZE
    elif cell_type_low == "unmyelinated_axons":
        return UNAXON_IMG_SIZE
    else:
        return MYELIN_IMG_SIZE


def get_model_path(cell_type: str, backend: str) -> Tuple[bool, str]:
    Settings_instance = Settings()
    cell_type_low = cell_type.lower()
        
    if cell_type_low != "axons" and cell_type_low != "myelin" and cell_type_low != "unmyelinated axons":
        return False, ""
    
    #rdir = os.path.dirname(os.path.realpath(__file__)) 
    model_file_path = Settings_instance.model_path
    if not model_file_path:
        return False, ""

    if backend.startswith(OPENVINO_BACKEND_PREFIX):
        if cell_type_low == "axons":
            res_path = model_file_path.joinpath(OPENVINO_AXON_MODEL_DIR_NAME)
        elif cell_type_low == "unmyelinated axons":
            res_path = model_file_path.joinpath(OPENVINO_UNAXON_MODEL_DIR_NAME)
        else:
            res_path = model_file_path.joinpath(OPENVINO_MYELIN_MODEL_DIR_NAME)
    else:
        if cell_type_low == "axons":
            res_path = model_file_path.joinpath(AXON_MODEL_PATH)
        elif cell_type_low == "unmyelinated axons":
            res_path = model_file_path.joinpath(UNAXON_MODEL_PATH)
        else:
            res_path = model_file_path.joinpath(MYELIN_MODEL_PATH)
        
    return True, str(res_path)

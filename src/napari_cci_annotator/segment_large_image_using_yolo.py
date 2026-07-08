import random
import threading
from collections import defaultdict
from functools import partial
from timeit import default_timer as timer
from skimage.measure import label, regionprops, find_contours
from pathlib import Path
import dask.array as da
import numpy as np
import skimage.color
import skimage.segmentation
from ultralytics import YOLO
from ultralytics.utils.ops import scale_masks
from matplotlib.pyplot import imsave

import napari_cci_annotator._id_table as id_table
from napari_cci_annotator import _settigns
from skimage.measure import find_contours
import numpy as np

def has_cut_bbox_edge(mask, min_edge_len=25, fill_frac=0.75, band=4):
    ys, xs = np.where(mask)

    if len(xs) == 0:
        return False

    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()

    h = y1 - y0 + 1
    w = x1 - x0 + 1

    if h < min_edge_len and w < min_edge_len:
        return False

    top = mask[y0:y0 + band, x0:x1 + 1]
    bottom = mask[max(y0, y1 - band + 1):y1 + 1, x0:x1 + 1]
    left = mask[y0:y1 + 1, x0:x0 + band]
    right = mask[y0:y1 + 1, max(x0, x1 - band + 1):x1 + 1]

    if w >= min_edge_len and top.mean() >= fill_frac:
        return True
    if w >= min_edge_len and bottom.mean() >= fill_frac:
        return True
    if h >= min_edge_len and left.mean() >= fill_frac:
        return True
    if h >= min_edge_len and right.mean() >= fill_frac:
        return True

    return False

def get_clean_masks(masks):
    clean_masks = []

    for mask in masks:
        mask = mask > 0
        labels = label(mask)
        regions = regionprops(labels)

        if len(regions) == 0:
            continue

        largest = max(regions, key=lambda x: x.area)

        mask_bool = labels == largest.label
        if has_cut_bbox_edge(mask_bool, min_edge_len=25, fill_frac=0.65):
            continue
        clean_masks.append(mask_bool)

    if len(clean_masks) == 0:
        return np.empty((0, masks.shape[1], masks.shape[2]), dtype=bool)

    return np.stack(clean_masks, axis=0)

class IntGenerator:
    def __init__(self, startValue = 100):
        self.lock = threading.Lock()
        self.cnt = 0
        self.startValue = startValue

    def setStartValue(self, startValue):
        with self.lock:
            self.startValue = startValue

    def getNext(self):
        with self.lock:
            self.cnt += 1
            return self.startValue + self.cnt


class AbstractSegmenter:
    def __init__(self, img_size):
        self.model_mutex = threading.Lock()
        self.image_size = img_size
        
    def getImageSize(self):
        return self.image_size


class YoloSegmenter(AbstractSegmenter):
    
    def __init__(self, model_path, image_dim, conf =0.25):
        super().__init__(image_dim)
        self.intGen = IntGenerator()
        self.model = YOLO(model_path, task='segment')
        self.conf = conf

    def segment(self, data):
        input_data = np.ascontiguousarray(data)
        result = self.model.predict(source=input_data,
                                    imgsz=self.getImageSize(),
                                    verbose=False,
                                    conf=self.conf,
                                    retina_masks=True)
        return result
    
    def segment_wrapper(self, data, block_id):
        with self.model_mutex:
            #print(f"segment chunk {block_id}, {data.shape}, {dimension}")
            rgb_data = skimage.color.gray2rgb(data)
            input_data = np.ascontiguousarray(rgb_data)

            #Remember to remove just debugging now
            debug_dir = Path("/home/noema/code/gisela_workflow/debug_tiles")
            debug_dir.mkdir(exist_ok=True)

            #imsave(
            #    debug_dir / f"tile_{block_id}.png",
            #    data.astype(np.uint8)
            #)

            np.save(debug_dir / f"tile_{block_id}.npy", data)

            result = self.model.predict(source=input_data,
                                        imgsz=self.getImageSize(),
                                        verbose=False,
                                        conf=self.conf,
                                        retina_masks=True,
                                        device='cpu' #remember to remove this this is just to test test_crop.py
                                         )
 
        computed_result = result  #[0].compute()
        all_masks = np.zeros(shape=data.shape, dtype=np.uint32)
        if computed_result is None or computed_result[0].masks is None:
            return all_masks
        
        result_masks = computed_result[0].masks
        
        masks = result_masks.data.cpu()

        if data.shape[0] != self.getImageSize() or data.shape[1] != self.getImageSize():
            if masks.ndim == 2:
                masks = masks.unsqueeze(0).unsqueeze(0)  # Now shape is (1, 1, H, W)
            elif masks.ndim == 3:
                masks = masks.unsqueeze(0)  # (1, C, H, W)
                
            masks = scale_masks(masks, result_masks.orig_shape)
            masks = masks.squeeze(0)
        
        masks = masks.numpy()

        clean_masks = get_clean_masks(masks)
        segments = clean_masks.shape[0]
        
        sh1 = all_masks.shape[0]
        sh2 = all_masks.shape[1]

        for n in range(segments):
            #res = masks[n]
            res = clean_masks[n]
            mask = res.astype("uint32") * self.intGen.getNext()
            all_masks[:sh1, :sh2] = np.where(all_masks[:sh1, :sh2] == 0, mask[:sh1, :sh2], all_masks[:sh1, :sh2])

        return all_masks


class LargeImageSegmenter:

    def __init__(self):

        self.model_mutex = threading.Lock()
        random.seed()
        self.tableOfIds = id_table.EquivalenceList()

    def caclulate_neighbour_equivalence_ids(self,data, block_id, img_size, scan_vertical, scan_far_side = False):

        print(f"calulating eq ids from {block_id}")
        x = 1 if not scan_far_side else data.shape[0] #img_size
        y = 1 if not scan_far_side else data.shape[1]

        neighbour_mod = -1 if not scan_far_side else 1

        if scan_vertical:
            neighbour_coords_mod = (neighbour_mod,0)
            scan_size = data.shape[1]
        else:
            neighbour_coords_mod = (0, neighbour_mod)
            scan_size = data.shape[0]

        connected_table = defaultdict(lambda: defaultdict(int))
        max_neighbour_local_table = defaultdict(lambda: defaultdict(int))
        for coord in range(scan_size):
            if scan_vertical:
                y = coord
            else:
                x = coord

            #construct table that holds which structures have most connecting pixels to the neighbour structure
            local_indices = (x, y)
            neighbour_indices = (x + neighbour_coords_mod[0], y + neighbour_coords_mod[1])
            id_local = data[local_indices]
            id_neighbour = data[neighbour_indices]
            if id_local != 0 and id_neighbour != 0 and id_neighbour != id_local:
                connected_table[id_local][id_neighbour] += 1
                max_neighbour_local_table[id_neighbour][id_local] += 1

        #only keep the maximum values per neighbour
        neighbour_max = {}
        for outer_key in max_neighbour_local_table:
            max_cnt = 0
            nid = max_neighbour_local_table[outer_key]
            nid = {k: v for k, v in nid.items() if v == max(nid.values())}
            neighbour_max[outer_key] = list(nid.keys())[0]

        for n in neighbour_max:
            loc = neighbour_max[n]
            for ll in connected_table:
                if ll != loc:  # we know this is NOT the local id that should be set to neighbour
                    connected_table[ll][n] = 0

        filtered = []
        for idx, outer_key in enumerate(connected_table.keys()):
            max_cnt = 0
            filtered.append((outer_key,0))
            for inner_key in connected_table[outer_key]:
                value = connected_table[outer_key][inner_key]
                if value > max_cnt:
                    max_cnt = value
                    filtered[idx] = (outer_key,inner_key)

        #merge data in local and neighbour structures
        for (ll, n) in filtered:
            id_l = ll
            id_n = n
            self.tableOfIds.add_eqvivalence_pair(id_l, id_n)

        return data

    def find_and_change_ids_along_border(self, data, block_info=None):
        
        d1 = data.shape[0]
        d2 = data.shape[1]
        id_set = set()
        
        for y in [0, d2 - 1]:
            for x in range(d1):
                local_indices = (x, y)
                id_local = data[local_indices]
                if id_local != 0:
                    id_set.add(id_local)
            
        for x in [0, d1 - 1]:
            for y in range(d2):
                local_indices = (x, y)
                id_local = data[local_indices]
                if id_local != 0:
                    id_set.add(id_local)
            
        for sid in id_set:
            eq_id = self.tableOfIds.get_equivalent_id(sid)
            if sid != eq_id:
                print(f"setting id: {sid} to eq_id: {eq_id}")
                idxs = np.where(data == sid)
                data[idxs] = eq_id
        
        return data

    def calculate_chunk_size(self, imgsize, overlap):
        return int(imgsize - (2 * overlap))

    def segment_large_image_crop_to_match_model_size(self, concrete_segmenter, imageData, imgSize=1024, overlap=100, clearBorders=False):
        chunk_size = self.calculate_chunk_size(imgSize,overlap)
        img_width = imageData.shape[0]
        crop_width = (img_width // chunk_size) * chunk_size
        
        img_height = imageData.shape[1]
        crop_height = (img_height // chunk_size) * chunk_size
        
        return self.segment_large_image_data(concrete_segmenter, imageData[:crop_width,:crop_height], imgSize=concrete_segmenter.getImageSize(), clearBorders=clearBorders)

    def segment_large_image(self, concrete_segmenter, imagePath, clearBorders=False):

        img_data = da.image.imread(imagePath)
        return self.segment_large_image_data(concrete_segmenter, img_data, imgSize=concrete_segmenter.getImageSize(), clearBorders=clearBorders)

    def segment_large_image_data(self, concrete_segmenter, imageData, imgSize=1024, overlap=100, clearBorders=False):

        large_image_tmp = da.from_array(imageData)
        s = large_image_tmp.shape
        chunk_size = self.calculate_chunk_size(imgSize, overlap)
        
        large_image = large_image_tmp.reshape((s[0],s[1])).rechunk((chunk_size,chunk_size,1))

        meta = np.empty((chunk_size, chunk_size), dtype=np.uint32)
        segment_results = da.map_overlap(concrete_segmenter.segment_wrapper, large_image, meta=meta, chunks=(chunk_size,chunk_size) ,depth=overlap, boundary='reflect', trim=True, allow_rechunk=True)

        dep = 1
        merge_horizontal = partial(self.caclulate_neighbour_equivalence_ids,img_size = chunk_size, scan_vertical = False)
        h1_result = segment_results.map_overlap(merge_horizontal,dtype=np.uint32,depth=dep, boundary='reflect', trim=True, allow_rechunk=True)

        merge_vertical = partial(self.caclulate_neighbour_equivalence_ids,img_size = chunk_size, scan_vertical = True)
        v1_result = h1_result.map_overlap(merge_vertical,dtype=np.uint32,depth=dep, boundary='reflect', trim=True, allow_rechunk=True)

        res = v1_result.compute(scheduler="threads")

        self.tableOfIds.group_ids()

        new_dask_array = da.from_array(res)
        
        final_dask = new_dask_array.reshape((s[0],s[1])).rechunk((chunk_size,chunk_size,1))
    
        end_result = final_dask.map_blocks(self.find_and_change_ids_along_border,dtype=np.uint32)

        print("starting...")
        
        start = timer()
        result = end_result.compute()
        end = timer()
        
        print("stopping: ",end - start)

        if clearBorders:
            print("Clearing borders")
            result = skimage.segmentation.clear_border(result)
        
        return result

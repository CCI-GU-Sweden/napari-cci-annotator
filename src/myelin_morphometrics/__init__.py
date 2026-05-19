# myelin_morphometrics/__init__.py

import numpy as np
from math import atan2, pi
from scipy.signal import savgol_filter

from skimage.morphology import medial_axis, binary_opening, disk

def get_BW_from_lbl(lbl_data, obj_idx):
    """
    Extract a single object from a labeled image.

    Args:
        lbl_data (numpy.ndarray): A 2-dimensional NumPy array containing labeled data, where each unique value represents a different object.
        obj_idx (int): The label value (index) of the object to be extracted.

    Returns:
        numpy.ndarray: A 2-dimensional binary NumPy array representing the extracted object, where True values correspond to the object pixels, and False values correspond to the background.

    Raises:
        AssertionError: If lbl_data is not a 2-dimensional NumPy array with integer data type.

    Example:
        >>> import numpy as np
        >>> lbl_data = np.array([[0, 1, 1, 0],
        ...                      [0, 1, 0, 2],
        ...                      [3, 0, 0, 2]])
        >>> obj_mask = get_BW(lbl_data, 1)
        >>> print(obj_mask)
        [[False  True  True False]
         [False  True False False]
         [False False False False]]
    """
    # Assert that input_array is a NumPy array
    assert isinstance(lbl_data, np.ndarray), "Input must be a NumPy array"
    # Assert that input_array has 2 dimensions
    assert lbl_data.ndim == 2, "Input array must be 2-dimensional"
    # Assert that input_array has integer data type
    assert np.issubdtype(lbl_data.dtype, np.integer), "Input array must have integer data type"
    
    BW_out = lbl_data==obj_idx
    return BW_out

def get_width(BW, disk_diam=5):
    """
    Calculate the median width of objects in a binary image using the medial axis and distance transform.

    Args:
        BW (numpy.ndarray): A 2-dimensional binary NumPy array of logical values (True/False) representing the objects of interest.
        disk_diam (int, optional): The diameter of the disk-shaped structuring element used for binary opening. Default is 5.

    Returns:
        float: The median width of the objects in the binary image.

    Raises:
        AssertionError: If BW is not a 2-dimensional NumPy array of logical values, or if disk_diam is not an integer.

    Notes:
        - The function first performs a binary opening operation on the input binary image using a disk-shaped structuring element.
        - It then computes the medial axis (skeleton) and the distance transform of the opened binary image.
        - The distance values on the skeleton pixels are extracted, and the non-zero values represent the width at those locations.
        - The median of these non-zero width values is calculated and multiplied by 2 to obtain the final median width.

    Example:
        >>> import numpy as np
        >>> BW = np.array([[True, True, False, False],
        ...                [True, True, True, False],
        ...                [False, True, True, True],
        ...                [False, False, True, True]])
        >>> median_width = get_width(BW)
        >>> print(f"Median width: {median_width:.2f}")
        Median width: 2.83
    """

    # Assert that BW is a 2-dimensional NumPy array of logical values
    assert isinstance(BW, np.ndarray), "BW must be a NumPy array"
    assert BW.ndim == 2, "BW must be a 2-dimensional array"
    assert np.issubdtype(BW.dtype, np.bool_), "BW must be a logical array"

    # Assert that disk_diam is an integer
    assert isinstance(disk_diam, int), "disk_diam must be an integer"

    # simple calculation of with based of skeleton and distance transform
    footprint = disk(disk_diam)
    opened = binary_opening(BW, footprint)
    # Compute the medial axis (skeleton) and the distance transform
    skel, distance = medial_axis(opened, return_distance=True)

    # Distance to the background for pixels of the skeleton
    dist_on_skel = distance * skel
    w = dist_on_skel[dist_on_skel>0]

    return np.median(w)*2

def smoothBoundary(boundary, window_length=10, polyorder=2):
    """
    Smooth a closed contour boundary using the Savitzky-Golay filter.

    Args:
        boundary (numpy.ndarray): A 2D NumPy array representing the boundary points.
            The array should have the shape (n, 2), where n is the number of boundary points.
            The first and last points should be the same to represent a closed contour.
        window_length (int, optional): The length of the filter window (i.e., the number of coefficients).
            It must be less than or equal to the size of the input boundary. Default is 10.
        polyorder (int, optional): The order of the polynomial used to fit the samples.
            It must be less than `window_length`. Default is 2.

    Returns:
        numpy.ndarray: A 2D NumPy array representing the smoothed boundary points.
            The array has the same shape as the input `boundary`.

    Raises:
        ValueError: If the input `boundary` is not a 2D array with 2 columns.
        ValueError: If the input `boundary` has fewer than 3 points.
        ValueError: If `window_length` is greater than the size of the input `boundary`.
        ValueError: If `polyorder` is greater than or equal to `window_length`.
        Warning: If the input `boundary` is not closed (first and last points are not the same).
    """
    # Check if the boundary has the expected format
    assert boundary.ndim == 2 and boundary.shape[1] == 2, "Boundary must be a 2D array with 2 columns"
    assert boundary.shape[0] >= 3, "Boundary must consist of more than 2 points"
    if window_length > boundary.shape[0]:
        raise ValueError("window_length must be less than or equal to the size of the input boundary")
    if polyorder >= window_length:
        raise ValueError("polyorder must be less than window_length")

    # Check if the boundary is closed
    if np.array_equal(boundary[0], boundary[-1]):
        b = boundary[:-1]
    else:
        b = boundary

    # Calculate the number of boundary points
    points_n_i = len(b)

    # Calculate how much to extend the array
    margin = int(np.round(points_n_i / 10))

    # Extend the boundary to avoid edge effects on smoothing
    extend_1 = b[-margin:]
    extend_2 = b[:margin]
    extended_b = np.concatenate((extend_1, b, extend_2))

    # Smooth the contour
    #extended_b[:, 0] = np.smooth(extended_b[:, 0])
    #extended_b[:, 1] = np.smooth(extended_b[:, 1])

    extended_b[:, 0] = savgol_filter(extended_b[:, 0], window_length, polyorder)
    extended_b[:, 1] = savgol_filter(extended_b[:, 1], window_length, polyorder)

    # Select only the correct part of the array (remove extension)
    boundary_S = extended_b[margin:-margin]

    return boundary_S

def tmatrix(angle):
    """
    Calculate the 2D rotation matrix for a given angle.

    Args:
        angle (float): The rotation angle in radians.

    Returns:
        numpy.ndarray: A 2x2 NumPy array representing the rotation matrix.

    Raises:
        TypeError: If the input `angle` is not a float or int.
    """
    # Check input type
    if not isinstance(angle, (float, int)):
        raise TypeError("Input angle must be a float or int")

    rotation_matrix = np.array([[np.cos(angle), -np.sin(angle)],
                                 [np.sin(angle), np.cos(angle)]]).T

    return rotation_matrix


def rotate_points(points, rot_matrix_2D):
    """
    Rotate a set of 2D points using a given 2D rotation matrix.

    Args:
        points (numpy.ndarray): A 2D NumPy array representing the points to be rotated.
            The array should have the shape (n, 2), where n is the number of points.
            The data type of the array should be int or float.
        rot_matrix_2D (numpy.ndarray): A 2x2 NumPy array representing the 2D rotation matrix.

    Returns:
        numpy.ndarray: A 2D NumPy array representing the rotated points.
            The array has the same shape as the input `points`.

    Raises:
        TypeError: If the input `points` is not a NumPy array.
        ValueError: If the input `points` does not have the shape (n, 2) or has fewer than 4 points.
        ValueError: If the data type of the input `points` is neither int nor float.
        ValueError: If the input `rot_matrix_2D` is not a 2x2 NumPy array.
    """
    # Check input types and shapes
    if not isinstance(points, np.ndarray):
        raise TypeError("Input points must be a NumPy array.")
    if points.ndim != 2 or points.shape[1] != 2 or points.shape[0] < 4:
        raise ValueError("Input points must have shape (n, 2) with n >= 4.")
    if not np.issubdtype(points.dtype, np.integer) and not np.issubdtype(points.dtype, np.floating):
        raise ValueError("Input points must have data type int or float.")
    if not isinstance(rot_matrix_2D, np.ndarray) or rot_matrix_2D.shape != (2, 2):
        raise ValueError("Input rot_matrix_2D must be a 2x2 NumPy array.")

    # Perform rotation
    rotated_points = np.dot(rot_matrix_2D, points.T).T

    return rotated_points


def bbox_dimenssions(points_2D):
    """
    Calculate the bounding box (minimum and maximum coordinates) of a set of 2D points.

    Args:
        points_2D (numpy.ndarray): A 2D NumPy array representing the points.
            The array should have the shape (n, 2), where n is the number of points.
            The data type of the array should be int or float.

    Returns:
        numpy.ndarray: A 1D NumPy array of length 2, representing the width and height of the bounding box.

    Raises:
        TypeError: If the input `points_2D` is not a NumPy array.
        ValueError: If the input `points_2D` does not have the shape (n, 2) or has fewer than 4 points.
        ValueError: If the data type of the input `points_2D` is neither int nor float.
    """
    # Check input types and shapes
    if not isinstance(points_2D, np.ndarray):
        raise TypeError("Input points_2D must be a NumPy array.")
    if points_2D.ndim != 2 or points_2D.shape[1] != 2 or points_2D.shape[0] < 4:
        raise ValueError("Input points_2D must have shape (n, 2) with n >= 4.")
    if not np.issubdtype(points_2D.dtype, np.integer) and not np.issubdtype(points_2D.dtype, np.floating):
        raise ValueError("Input points_2D must have data type int or float.")

    # Calculate the bounding box
    min_coords = np.min(points_2D, axis=0)
    max_coords = np.max(points_2D, axis=0)
    bbox_dimensions = max_coords - min_coords

    return bbox_dimensions


def minBoundingBox(convex_hull, metric='width'):
    """
    Computes the minimum bounding box of a set of 2D points forming a convex hull.

    This function implements the rotating calipers algorithm to find the minimum bounding box
    of a convex polygon. The algorithm is based on the observation that a side of the minimum
    bounding box must be collinear with an edge of the convex polygon.

    Args:
        convex_hull (numpy.ndarray): A 2D NumPy array of shape (n, 2), where n > 3, representing
            the convex hull points. The dtype of the array must be either int or float.
        metric (str, optional): The metric to use for determining the minimum bounding box.
            Accepted values are 'area' (default) and 'width'. If 'area' is chosen, the minimum
            bounding box is the one with the smallest area. If 'width' is chosen, the minimum
            bounding box is the one with the smallest width (short axis).

    Returns:
        tuple: A tuple containing two NumPy arrays:
            - min_bbox_corners (numpy.ndarray): A 2D NumPy array of shape (4, 2) representing
              the corner points of the minimum bounding box.
            - min_area_bbox (numpy.ndarray): A 1D NumPy array of shape (2,) representing
              the width and height of the minimum bounding box.

    Raises:
        TypeError: If convex_hull is not a NumPy array.
        ValueError: If the shape of convex_hull is not (n, 2) with n > 3.
        ValueError: If the data type of convex_hull is not int or float.
        TypeError: If metric is not a string or not one of 'area' or 'width'.

    Example:
        >>> convex_hull = convex_hull = np.array([[1, 1], [1, 4], [1.5, 5], [2,4], [2,1]], dtype=float)
        >>> min_bbox_corners, min_area_bbox = minBoundingBox(convex_hull)
        >>> print(min_bbox_corners)
        [[1. 1.]
        [2. 1.]
        [2. 5.]
        [1. 5.]]
        >>> print(min_area_bbox)
        [1. 4.]
    """
    
    # Check if convex_hull is a NumPy array
    if not isinstance(convex_hull, np.ndarray):
        raise TypeError("Input convex_hull must be a NumPy array.")
    # Check the shape of convex_hull
    if convex_hull.ndim != 2 or convex_hull.shape[1] != 2 or convex_hull.shape[0] < 4:
        raise ValueError("Input convex_hull must have shape (n, 2) with n > 3.")
    # Check the data type of convex_hull
    if not np.issubdtype(convex_hull.dtype, np.integer) and not np.issubdtype(convex_hull.dtype, np.floating):
        raise ValueError("Input convex_hull must have data type int or float.")
    
    # Convert convex_hull to float data type
    convex_hull = convex_hull.astype(float)
    
    # center of mass, used to later translate point cloud to same ref frame
    #c_mass = np.mean(convex_hull, axis=0)
    # bcause it is not equaly sampled
    c_mass = ((np.max(convex_hull, axis=0)-np.min(convex_hull, axis=0))/2)+np.min(convex_hull, axis=0)

    # Calculate the edge vectors of the convex hull
    edges = np.roll(convex_hull, -1, axis=0) - convex_hull

    # Calculate the angles of the edge vectors
    angles = np.apply_along_axis(lambda edge: atan2(edge[1], edge[0]), 1, edges)

    # Get the unique angles in the first quadrant
    unique_angles = np.unique(angles % (pi))

    # Create rotation matrices for all unique angles
    rotations = [tmatrix(angle) for angle in unique_angles]

    # Rotate the convex hull points by all unique angles
    rotated_hulls = [rotate_points(convex_hull, R) for R in rotations]
    
    # Calculate the bounding box size and area for each rotation
    bounding_boxes = [bbox_dimenssions(rotated_hull) for rotated_hull in rotated_hulls]

    # Find the minimum area bounding box
    if metric=='area':
        # calculate the areas of all bboxes
        areas = [bbox[0] * bbox[1] for bbox in bounding_boxes]
        min_metric_index = np.argmin(areas)
    elif metric=='width':
        short_axis = [np.min(bbox) for bbox in bounding_boxes]
        min_metric_index = np.argmin(short_axis)
    else:
        raise TypeError("metric must be 'area' or 'width'")
    
    min_area_bbox = bounding_boxes[min_metric_index]

    # Rotate the minimum bounding box back to the original frame
    rotation_matrix = rotations[min_metric_index].T
    #   get a box based on the area/shape
    min_bbox_points = np.array([
        [0, 0],
        [min_area_bbox[0], 0],
        [min_area_bbox[0], min_area_bbox[1]],
        [0, min_area_bbox[1]]
    ])
    #   rotate the box
    min_bbox_corners = rotate_points(min_bbox_points, rotation_matrix)
    #   move the box to 0,0
    min_bbox_corners = min_bbox_corners - np.mean(min_bbox_corners, axis=0)
    #   move the box to the same reference as the inpurt convex hull
    min_bbox_corners = min_bbox_corners + c_mass

    return min_bbox_corners, min_area_bbox, rotation_matrix
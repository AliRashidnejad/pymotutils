# vim: expandtab:ts=4:sw=4
"""
This module contains an image viewer and drawing routines based on OpenCV.
"""
import numpy as np
import cv2
import time
import pymotutils


def is_in_bounds(mat, roi):
    """Check if ROI is fully contained in the image.

    Parameters
    ----------
    mat : ndarray
        An ndarray of ndim>=2.
    roi : (int, int, int, int)
        Region of interest (x, y, width, height) where (x, y) is the top-left
        corner.

    Returns
    -------
    bool
        Returns true if the ROI is contain in mat.

    """
    if roi[0] < 0 or roi[0] + roi[2] >= mat.shape[1]:
        return False
    if roi[1] < 0 or roi[1] + roi[3] >= mat.shape[0]:
        return False
    return True


def view_roi(mat, roi):
    """Get sub-array.

    The ROI must be valid, i.e., fully contained in the image.

    Parameters
    ----------
    mat : ndarray
        An ndarray of ndim=2 or ndim=3.
    roi : (int, int, int, int)
        Region of interest (x, y, width, height) where (x, y) is the top-left
        corner.

    Returns
    -------
    ndarray
        A view of the roi.

    """
    sx, ex = roi[0], roi[0] + roi[2]
    sy, ey = roi[1], roi[1] + roi[3]
    if mat.ndim == 2:
        return mat[sy:ey, sx:ex]
    else:
        return mat[sy:ey, sx:ex, :]


def copy_to(src, dst_roi, dst):
    """ Copy src to dst[roi].

    The dst_roi must be fully contained in dst and of the same shape as
    the src image.

    Parameters
    ----------
    src : ndarray
        Image that should be copied (ndim=2 or ndim=3).
    dst_roi : (int, int, int, int)
        Region of interest (x, y, width, height) where (x, y) is the top-left
        corner.
    dst : ndarray
        The target image of same ndim as src.

    """
    sx, ex = dst_roi[0], dst_roi[0] + dst_roi[2]
    sy, ey = dst_roi[1], dst_roi[1] + dst_roi[3]
    if dst.ndim == 2:
        dst[sy:ey, sx:ex] = src
    else:
        dst[sy:ey, sx:ex, :] = src


class ImageViewer(object):
    """An image viewer with drawing routines and video capture capabilities.

    Key Bindings:

    * 'SPACE' : pause
    * 'ESC' : quit

    Parameters
    ----------
    update_ms : int
        Number of milliseconds between frames (1000 / frames per second).
    window_shape : (int, int)
        Shape of the window (width, height).
    caption : Optional[str]
        Title of the window.

    Attributes
    ----------
    image : ndarray
        Color image of shape (height, width, 3). You may directly manipulate
        this image to change the view. Otherwise, you may call any of the
        drawing routines of this class. Internally, the image is treated as
        beeing in BGR color space.

        Note that the image is resized to the the image viewers window_shape
        just prior to visualization. Therefore, you may pass differently sized
        images and call drawing routines with the appropriate, original point
        coordinates.
    color : (int, int, int)
        Current BGR color code that applies to all drawing routines.
        Values are in range [0-255].
    text_color : (int, int, int)
        Current BGR text color code that applies to all text rendering routines.
        Values are in range [0-255].
    thickness : int
        Stroke width in pixels that applies to all drawing routines.

    """

    def __init__(self, update_ms, window_shape=(640, 480), caption="Figure 1"):
        self._window_shape = window_shape
        self._caption = caption
        self._update_ms = update_ms
        self._video_writer = None
        self._user_fun = lambda: None
        self._keypress_fun = lambda key: None
        self._terminate = False

        self.image = np.zeros(self._window_shape + (3, ), dtype=np.uint8)
        self._color = (0, 0, 0)
        self.text_color = (255, 255, 255)
        self.thickness = 1

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        if len(value) != 3:
            raise ValueError("color must be tuple of 3")
        self._color = tuple(int(c) for c in value)

    def rectangle(self, x, y, w, h, label=None, alpha=None):
        """Draw a rectangle.

        Parameters
        ----------
        x : float | int
            Top left corner of the rectangle (x-axis).
        y : float | int
            Top let corner of the rectangle (y-axis).
        w : float | int
            Width of the rectangle.
        h : float | int
            Height of the rectangle.
        label : Optional[str]
            A text label that is placed at the top left corner of the rectangle.
        alpha : Optional[float]
            Transparency between 0 and 1.

        """
        if alpha is None:
            pt1 = int(x), int(y)
            pt2 = int(x + w), int(y + h)
            cv2.rectangle(self.image, pt1, pt2, self._color, self.thickness)
            if label is not None:
                text_size = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_PLAIN, 1, self.thickness)

                center = pt1[0] + 5, pt1[1] + 5 + text_size[0][1]
                pt2 = (
                    pt1[0] + 10 + text_size[0][0],
                    pt1[1] + 10 + text_size[0][1])
                cv2.rectangle(self.image, pt1, pt2, self._color, -1)
                cv2.putText(
                    self.image, label, center, cv2.FONT_HERSHEY_PLAIN, 1,
                    self.text_color, self.thickness)
            return

        padding = max(0, self.thickness)
        roi = (
            int(x - padding), int(y - padding), int(w + 2. * padding),
            int(h + 2 * padding))
        if not is_in_bounds(self.image, roi):
            return

        image_roi = view_roi(self.image, roi)
        image = image_roi.copy()

        pt1 = int(padding), int(padding)
        pt2 = int(padding + w), int(padding + h)
        cv2.rectangle(image, pt1, pt2, self._color, self.thickness)
        if label is not None:
            text_size = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_PLAIN, 1, self.thickness)

            center = pt1[0] + 5, pt1[1] + 5 + text_size[0][1]
            pt2 = pt1[0] + 10 + text_size[0][0], pt1[1] + 10 + text_size[0][1]
            cv2.rectangle(image, pt1, pt2, self._color, -1)
            cv2.putText(
                image, label, center, cv2.FONT_HERSHEY_PLAIN, 1,
                (255, 255, 255), self.thickness)

        blended = cv2.addWeighted(image, alpha, image_roi, 1. - alpha, 0)
        copy_to(blended, roi, self.image)

    def circle(self, x, y, radius, label=None, alpha=None):
        """Draw a circle.

        Parameters
        ----------
        x : float | int
            Center of the circle (x-axis).
        y : float | int
            Center of the circle (y-axis).
        radius : float | int
            Radius of the circle in pixels.
        label : Optional[str]
            A text label that is placed at the center of the circle.
        alpha : Optional[float]
            Transparency between 0 and 1.

        """
        image_size = int(radius + self.thickness + 1.5)  # actually half size
        roi = (
            int(x - image_size), int(y - image_size), int(2 * image_size),
            int(2 * image_size))
        if not is_in_bounds(self.image, roi):
            return

        image_roi = view_roi(self.image, roi)
        image = image_roi if alpha is None else image_roi.copy()

        center = image.shape[1] // 2, image.shape[0] // 2
        cv2.circle(
            image, center, int(radius + .5), self._color, self.thickness)
        if label is not None:
            cv2.putText(
                self.image, label, center, cv2.FONT_HERSHEY_PLAIN, 2,
                self.text_color, 2)

        if alpha is not None:
            blended = cv2.addWeighted(image, alpha, image_roi, 1. - alpha, 0)
            copy_to(blended, roi, self.image)

    def line_strip(self, xs, ys):
        """Draw line strip.

        Parameters
        ----------
        xs : array_like
            Line strip vertex x-coordinates.
        ys : array_like
            Line strip vertex y-coordinates.

        """
        x_pairs = zip(xs[0:], xs[1:])
        y_pairs = zip(ys[0:], ys[1:])

        for x_pair, y_pair in zip(x_pairs, y_pairs):
            pt1 = int(x_pair[0]), int(y_pair[0])
            pt2 = int(x_pair[1]), int(y_pair[1])
            cv2.line(self.image, pt1, pt2, self.color, self.thickness)

    def arrow(self, start, end):
        """Draw arrow from start to end.

        Parameters
        ----------
        start : array_like
            Vector of length 2 which contains the arrow starting position.
        end : array_like
            Vector of length 2 which contains the arrow end position.

        """
        start = tuple(int(x) for x in start)
        end = tuple(int(x) for x in end)
        cv2.arrowedLine(self.image, start, end, self.color, self.thickness)

    def gaussian(self, mean, covariance, alpha=None, label=None):
        """Draw 95% confidence ellipse of a 2-D Gaussian distribution.

        Parameters
        ----------
        mean : array_like
            The mean vector of the Gaussian distribution (ndim=1).
        covariance : array_like
            The 2x2 covariance matrix of the Gaussian distribution.
        label : Optional[str]
            A text label that is placed at the center of the ellipse.
        alpha : Optional[float]
            Transparency between 0 and 1.

        """
        # chi2inv(0.95, 2) = 5.9915
        vals, vecs = np.linalg.eigh(5.9915 * covariance)
        indices = vals.argsort()[::-1]
        vals, vecs = np.sqrt(vals[indices]), vecs[:, indices]
        vals = np.clip(vals, 0, np.max(self.image.shape))

        if alpha is None:
            center = int(mean[0] + .5), int(mean[1] + .5)
            axes = int(vals[0] + .5), int(vals[1] + .5)
            angle = 180. * np.arctan2(vecs[1, 0], vecs[0, 0]) / np.pi
            cv2.ellipse(
                self.image, center, axes, angle, 0, 360, self._color, 2)
            if label is not None:
                cv2.putText(
                    self.image, label, center, cv2.FONT_HERSHEY_PLAIN, 2,
                    self.text_color, 2)
            return

        padding = max(0, self.thickness)
        mini, maxi = mean - vals - padding, mean + vals + padding
        roi = tuple(mini.astype(int)) + tuple((maxi - mini + 1.).astype(int))
        if not is_in_bounds(self.image, roi):
            return

        image_roi = view_roi(self.image, roi)
        image = image_roi.copy()

        center = tuple((mean - mini).astype(int))
        axes = int(vals[0] + .5), int(vals[1] + .5)
        angle = int(180. * np.arctan2(vecs[1, 0], vecs[0, 0]) / np.pi)
        cv2.ellipse(image, center, axes, angle, 0, 360, self._color, 2)
        if label is not None:
            cv2.putText(
                image, label, center, cv2.FONT_HERSHEY_PLAIN, 2,
                self.text_color, 2)

        blended = cv2.addWeighted(image, alpha, image_roi, 1. - alpha, 0)
        copy_to(blended, roi, self.image)

    def annotate(self, x, y, text):
        """Draws a text string at a given location.

        Parameters
        ----------
        x : int | float
            Bottom-left corner of the text in the image (x-axis).
        y : int | float
            Bottom-left corner of the text in the image (y-axis).
        text : str
            The text to be drawn.

        """
        cv2.putText(
            self.image, text, (int(x), int(y)), cv2.FONT_HERSHEY_PLAIN, 2,
            self.text_color, 2)

    def colored_points(self, points, colors=None, skip_index_check=False):
        """Draw a collection of points.

        The point size is fixed to 1.

        Parameters
        ----------
        points : ndarray
            The Nx2 array of image locations, where the first dimension is
            the x-coordinate and the second dimension is the y-coordinate.
        colors : Optional[ndarray]
            The Nx3 array of colors (dtype=np.uint8). If None, the current
            color attribute is used.
        skip_index_check : Optional[bool]
            If True, index range checks are skipped. This is faster, but
            requires all points to lie within the image dimensions.

        """
        if not skip_index_check:
            cond1, cond2 = points[:, 0] >= 0, points[:, 0] < 480
            cond3, cond4 = points[:, 1] >= 0, points[:, 1] < 640
            indices = np.logical_and.reduce((cond1, cond2, cond3, cond4))
            points = points[indices, :]
        if colors is None:
            colors = np.repeat(self._color,
                               len(points)).reshape(3, len(points)).T
        indices = (points + .5).astype(np.int)
        self.image[indices[:, 1], indices[:, 0], :] = colors

    def polyline(self, points, alpha=None):
        """Draw a line

        Parameters
        ----------
        points : ndarray
            The Nx2 array of image locations, where the first dimension is
            the x-coordinate and the second dimension is the y-coordinate.
        alpha : Optional[float]
            Transparency between 0 and 1.

        Returns
        -------

        """
        if alpha is None:
            cv2.polylines(
                self.image, [points], False, self._color, self.thickness)
            return

        padding = max(0, self.thickness)
        x1, y1 = np.amin(points, axis=0)
        x2, y2 = np.amax(points, axis=0)

        x = min(self.image.shape[1] - 1 - padding, max(0 + padding, x1))
        y = min(self.image.shape[0] - 1 - padding, max(0 + padding, y1))
        w = min(self.image.shape[1] - 1 - padding, max(0 + padding, x2)) - x
        h = min(self.image.shape[0] - 1 - padding, max(0 + padding, y2)) - y

        roi = (
            int(x - padding), int(y - padding), int(w + 2 * padding),
            int(h + 2 * padding))

        if not is_in_bounds(self.image, roi):
            return

        image_roi = view_roi(self.image, roi)
        image = image_roi.copy()
        points = points - roi[:2]
        cv2.polylines(image, [points], False, self._color, self.thickness)

        blended = cv2.addWeighted(image, alpha, image_roi, 1. - alpha, 0)
        copy_to(blended, roi, self.image)

    def enable_videowriter(
            self, output_filename, fourcc_string="MJPG", fps=None):
        """ Write images to video file.

        Parameters
        ----------
        output_filename : str
            Output filename.
        fourcc_string : str
            The OpenCV FOURCC code that defines the video codec (check OpenCV
            documentation for more information).
        fps : Optional[float]
            Frames per second. If None, configured according to current
            parameters.

        """
        fourcc = cv2.VideoWriter_fourcc(*fourcc_string)
        if fps is None:
            fps = int(1000. / self._update_ms)
        self._video_writer = cv2.VideoWriter(
            output_filename, fourcc, fps, self._window_shape)

    def disable_videowriter(self):
        """ Disable writing videos.
        """
        self._video_writer = None

    def run(self, update_fun=None, keypress_fun=None):
        """Start the image viewer.

        This method blocks until the user requests to close the window.

        Parameters
        ----------
        update_fun : Optional[Callable[] -> None]
            An optional callable that is invoked at each frame. May be used
            to play an animation/a video sequence.
        keypress_fun : Optional[Callable[int] -> None]
            An optional callable that is invoked when the user presses a
            button.

        """
        if update_fun is not None:
            self._user_fun = update_fun
        if keypress_fun is not None:
            self._keypress_fun = keypress_fun

        self._terminate, is_paused = False, True
        print("ImageViewer is paused, press space to start.")
        while not self._terminate:
            t0 = time.time()
            if not is_paused:
                self._user_fun()
                if self._video_writer is not None:
                    self._video_writer.write(
                        cv2.resize(self.image, self._window_shape))
            t1 = time.time()
            remaining_time = max(1, int(self._update_ms - 1e3 * (t1 - t0)))
            cv2.imshow(
                self._caption, cv2.resize(self.image, self._window_shape))
            key = cv2.waitKey(remaining_time)
            if key & 255 == 27:  # ESC
                print("terminating")
                self._terminate = True
            elif key & 255 == 32:  # ' '
                print("toggeling pause: " + str(not is_paused))
                is_paused = not is_paused
            elif key & 255 == 115:  # 's'
                print("stepping")
                self._user_fun()
                is_paused = True
            elif key != -1:
                self._keypress_fun(key)

        # Due to a bug in OpenCV we must call imshow after destroying the
        # window. This will make the window appear again as soon as waitKey
        # is called.
        #
        # see https://github.com/Itseez/opencv/issues/4535
        self.image[:] = 0
        cv2.destroyWindow(self._caption)
        cv2.waitKey(1)
        cv2.imshow(self._caption, self.image)

    def stop(self):
        """Stop the control loop.

        After calling this method, the viewer will stop execution before the
        next frame and hand over control flow to the user.

        Parameters
        ----------

        """
        self._terminate = True


class ImageVisualization(pymotutils.Visualization):
    """
    This is an abstract base class for image-based visualization.
    It implements a simple control loop based on :class:`ImageViewer`.

    Parameters
    ----------
    update_ms : int
        Number of milliseconds between frames (1000 / frames per second).
    window_shape : (int, int)
        Shape of the window (width, height).
    caption : Optional[str]
        Title of the window.

    Attributes
    ----------

    """

    def __init__(self, update_ms, window_shape=None, caption="Figure 1"):
        self._viewer = ImageViewer(update_ms, window_shape, caption)
        self._frame_idx, self._end_idx = None, None
        self._user_callback = lambda frame_idx: None

    def enable_videowriter(
            self, video_filename, fourcc_string="FMP4", fps=None):
        """Write output to video.

        Parameters
        -----------
        video_filename : str
            Output vidoe filename.
        fourcc_string : Optional[str]
            The OpenCV fourcc encoding string (see OpenCV docs)
        fps : Optional[float]
            Frames per second. If None, configured according to current
            visualization parameters.

        """
        self._viewer.enable_videowriter(video_filename, fourcc_string, fps)

    def disable_videowriter(self):
        """Disable writing videos.
        """
        self._viewer.disable_videowriter()

    def run(self, start_idx, end_idx, frame_callback):
        self._frame_idx = start_idx
        self._end_idx = end_idx
        self._user_callback = frame_callback
        self._viewer.run(self._next_frame, self.on_keypress)

    def _next_frame(self):
        if self._end_idx is not None and self._frame_idx >= self._end_idx:
            self._viewer.stop()
            return
        self._user_callback(self._frame_idx)
        self._frame_idx += 1

    def on_keypress(self, key):
        """ Callback function for key-press events.

        Parameters
        ----------
        key : int
            An OpenCV key press code.

        """
        pass

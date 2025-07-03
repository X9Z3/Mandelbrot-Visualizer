from vpython import *
#Web VPython 3.2

"""
Created by Maximillian DeMarr.
Future work ideas:
- Improve floating point resolution
- Implement other Mandelbrot sets (e.g. Julia)
- Pan around region feature

Last major update 2025/06/26.
"""

# ================================= Canvas =====================================

scene = display(width = 900, height = 600)
scene.bind('mousedown', resize_box)
scene.bind('mouseup', release_mouse_1)
scene.userzoom = False
scene.userspin = False
scene.userpan = False
scene.autoscale = False

about_me = """
            Highlight an area to zoom using <b>left-click and drag</b>. To go back to the 
    previous view, click <b>Undo</b>, or use <b>Redo</b> to step forward again. Higher image
    resolutions are computationally expensive. If loading takes too long, try selecting a 
    lower resolution for faster rendering. You can also adjust the <b>Depth</b>, which sets
    how many iterations are used to determine whether a point escapes the Mandelbrot set. 
    Higher values reveal finer detail but increase render time—though not as drastically as
    higher resolutions do. When zooming, the white frame represents the new region which 
    will be zoomed into.

            I've recreated some of my favorite MATLAB colormaps here. One of them—my 
    "spectral" scheme—is custom made and looks especially vivid at high iteration 
    depths. As you continue zooming, you'll eventually reach a limit where the image 
    breaks into large pixels, followed by a smooth, empty void. This boundary is due 
    to floating-point precision limits. I've implemented a few techniques to extend 
    this range, but a more robust fix would require a high-precision JS math library. 
    Since that would slow everything down and isn't the goal of this project, I've 
    left it out for now. I would be open to implementing this as well as the option
    to view other types of Mandelbrot sets.

    I'll add a GitHub link here later.

                -<i>Created by Maximillian DeMarr</i>
"""

scene.caption = about_me
MathJax.Hub.Queue(["Typeset", MathJax.Hub, scene.caption])  # LaTeX formatting
scene.append_to_title("<div id='fps'/>")











# ================================ Methods =====================================

def colormaps(colors=vec(0, 0, 0), cmap='default'):
    """
    Converts a 3D vector of normalized values into an RGB color using one of several
    visually distinct colormap styles.

    Parameters:
        colors (vec): A vector where x, y, and z components typically correspond to 
                      iteration-based values normalized to [0, 1].
        cmap (str):   The name of the colormap to apply. Options include:
                      'spectral', 'inferno', 'viridis', 'plasma', or 'default'.

    Returns:
        vec: A vector representing RGB values in the range [0, 1].

    Colormap Notes:
        - Most colormaps are inspired by MATLAB's built-in visual styles.
        - 'spectral' is a custom, high-frequency psychedelic palette which I stumbled
          upon, trying to make these.
        - 'default' resembles a blue-to-orange gradient with a bright white midpoint and 
          deep blacks at the extremes, giving strong contrast and dynamic range.
    """
    if cmap == 'spectral':
        # Custom high-frequency sinusoidal colormap for vivid, psychedelic transitions
        R = abs(sin(100 * colors.x + 1))
        G = sin(100 * colors.y + 2)
        B = sin(100 * colors.z + 3)
        return vec(R, G, B)

    elif cmap == 'inferno':
        # Deep warm red-yellow highlights 
        R = sqrt(colors.x)
        G = colors.y**2
        B = -5 * (colors.z - 0.2)**2 + 0.2
        return vec(R, G, B)

    elif cmap == 'viridis':
        # Cool and smooth gradient with greenish mids and bluish lows
        R = sin(colors.x + 0.5)**16
        G = colors.y
        B = -3 * (colors.z - 0.38)**2 + 0.6
        return vec(R, G, B)

    elif cmap == 'plasma':
        # Bright purple-yellow transitions with nonlinearity for punch
        R = sin(colors.x)
        G = colors.y**10 + colors.y**(1/6) - 0.8
        B = -colors.z + 1
        return vec(R, G, B)

    else:  # cmap == 'default'
        # Blue-black to orange-black gradient with a white-hot center
        R = sin(colors.x + 0.9)**30
        G = sin(colors.y + 0.97)**80 * 0.9
        B = -((colors.z + 0.5)**6 - 0.8)**2 + 1
        return vec(R, G, B)


def split(string=None, separator=' '):
    """
    Splits a string into a list of substrings using the specified separator.

    Parameters:
        string (str): The input string to split. Defaults to None.
        separator (str): The character to split on. Defaults to a single space (' ').

    Returns:
        list: A list of substrings split by the given separator.

    Example:
        split("apple,banana,pear", separator=',')
        → ['apple', 'banana', 'pear']

    Notes:
        - Does not handle consecutive separators the way Python's built-in split() does.
        - This is a minimal version and does not support advanced behavior like regex or max splits.
    """
    if string is None:
        return []

    split_string = []
    current_word = ''

    for s in string:
        if s == separator:
            split_string.append(current_word)
            current_word = ''
        else:
            current_word += s

    # Append the final word after the loop ends
    split_string.append(current_word)
    return split_string









# ============================= Widget Methods =================================

def resize_box(evt):
    """
    Handles interactive zoom box resizing with the left mouse button held down.

    Behavior:
        - User clicks and drags to draw a rectangular selection box.
        - The selection box is constrained to a 3:2 aspect ratio to prevent distortion.
        - On mouse release, the complex plane coordinates corresponding to the selected
          box are computed.
        - Mandelbrot view is updated to zoom into the selected region.
        - Live visual feedback is given by red and white curves outlining the selection box.

    Notes:
        - Uses VPython's scene.mouse.project to get 2D coordinates in the scene plane.
        - Adds half-width and half-height offsets when converting to pixel coordinates.
        - Aspect ratio locking uses conditional logic to adjust either width or height accordingly.
    """
    global mouse_1_up, mandelbrot

    if not mandelbrot.loaded:  # Wait until the Mandelbrot is fully rendered
        return

    mouse_1_up = False

    # Record the starting point of the mouse drag (projected onto Z=0 plane)
    starting_mouse_pos = scene.mouse.project(normal=vec(0, 0, 1), point=vec(1, 1, 0))
    opposite_corner_pos = starting_mouse_pos  # Initialize opposite corner

    # Create two curve objects for live visual feedback of the box edges
    mouse_window_curve = curve(
        pos=[starting_mouse_pos]*5,
        color=color.red,
        radius=0
    )
    highlighting_curve = curve(
        pos=[starting_mouse_pos]*5,
        color=color.white,
        radius=0
    )

    while True:
        rate(10)  # Limit loop to 60fps for smooth visuals

        current_mouse_pos = scene.mouse.project(normal=vec(0, 0, 1), point=vec(1, 1, 0))

        # Break loop on mouse release
        if mouse_1_up:
            # Hide visual box outlines
            mouse_window_curve.visible = False
            highlighting_curve.visible = False

            # Calculate selected pixel bounds, correcting for mandelbrot's center origin
            x_min = min(starting_mouse_pos.x, opposite_corner_pos.x) + mandelbrot.width / 2
            x_max = max(starting_mouse_pos.x, opposite_corner_pos.x) + mandelbrot.width / 2
            y_min = min(starting_mouse_pos.y, opposite_corner_pos.y) + mandelbrot.height / 2
            y_max = max(starting_mouse_pos.y, opposite_corner_pos.y) + mandelbrot.height / 2

            # Convert pixel bounds to complex plane coordinates
            image_width = mandelbrot.x_max - mandelbrot.x_min
            image_height = mandelbrot.y_max - mandelbrot.y_min

            x_min = (image_width / mandelbrot.width) * x_min + mandelbrot.x_min
            x_max = (image_width / mandelbrot.width) * x_max + mandelbrot.x_min
            y_min = (image_height / mandelbrot.height) * y_min + mandelbrot.y_min
            y_max = (image_height / mandelbrot.height) * y_max + mandelbrot.y_min

            # Update the Mandelbrot view parameters to zoom in on selected box
            mandelbrot.change_parameters(
                max_iter=mandelbrot.max_iter,
                image_dimensions=[x_min, x_max, y_min, y_max],
                resolution=[mandelbrot.height, mandelbrot.width],
                colormap=mandelbrot.colormap
            )

            # Highlight undo button to show zoom is reversible
            undo_dimension_change_button.background = color.white
            break  # Exit the while loop, ending the drag operation

        # --- Live update box dimensions with aspect ratio locking ---

        current_box_width = abs(current_mouse_pos.x - starting_mouse_pos.x)
        current_box_height = abs(current_mouse_pos.y - starting_mouse_pos.y)

        # Determine drag direction for correct corner positioning (+/- signs)
        corner_sign_x = 1 if current_mouse_pos.x > starting_mouse_pos.x else -1
        corner_sign_y = 1 if current_mouse_pos.y > starting_mouse_pos.y else -1

        # Aspect ratio locking: maintain height/width = 2/3 (3:2 ratio)
        if current_box_height / current_box_width > 3 / 2:
            # Too flat, adjust width based on height to maintain ratio
            opposite_corner_pos = vec(
                starting_mouse_pos.x + corner_sign_x * current_box_height * 3 / 2,
                current_mouse_pos.y,
                0
            )
        else:
            # Too tall, adjust height based on width
            opposite_corner_pos = vec(
                current_mouse_pos.x,
                starting_mouse_pos.y + corner_sign_y * current_box_width * 2 / 3,
                0
            )

        # Update red box (mouse drag area) vertices (closing loop for rectangle)
        mouse_window_curve.modify(1, pos=vec(current_mouse_pos.x, starting_mouse_pos.y, 0))
        mouse_window_curve.modify(2, pos=current_mouse_pos)
        mouse_window_curve.modify(3, pos=vec(starting_mouse_pos.x, current_mouse_pos.y, 0))
        mouse_window_curve.modify(4, pos=starting_mouse_pos)

        # Update white box (aspect-ratio-corrected selection box)
        highlighting_curve.modify(1, pos=vec(opposite_corner_pos.x, starting_mouse_pos.y, 0))
        highlighting_curve.modify(2, pos=opposite_corner_pos)
        highlighting_curve.modify(3, pos=vec(starting_mouse_pos.x, opposite_corner_pos.y, 0))
        highlighting_curve.modify(4, pos=starting_mouse_pos)


def release_mouse_1(evt):
    """
    Handles mouse button release events for node interaction.
    
    Sets a global flag to indicate the left mouse button has been released,
    which terminates any active node dragging operations in the move_node function.
    
    Args:
        evt: The mouse event object (unused but required for event handler signature)
        
    Global Dependencies:
        mouse_1_up (bool): Flag tracking left mouse button state (True when released)
    """
    global mouse_1_up
    mouse_1_up = True


def recall_mandelbrot_dimensions(evt):
    """
    Shared callback for Undo and Redo buttons.

    Parameters:
        evt (button): The button event object. Must include a custom `redo` attribute
                      (True for redo, False for undo), and a reference to the complementary button.

    Behavior:
        - If redo: restores a dimension from the redo stack and pushes current to undo.
        - If undo: restores a dimension from the undo stack and pushes current to redo.
        - Triggers a re-render via `load_recent_dimensions`.
        - Dynamically updates the button background color to indicate availability.
    """
    global mandelbrot
    if not mandelbrot.loaded:
        return
    elif len(mandelbrot.dimensions_undo_list) == 1 and len(mandelbrot.dimensions_redo_list) == 0:
        # Nothing to undo or redo
        return

    # Preserve current settings except dimensions
    max_iter = mandelbrot.max_iter
    resolution = [mandelbrot.height, mandelbrot.width]
    colormap = mandelbrot.colormap

    # Load previous or forward dimensions
    mandelbrot.load_recent_dimensions(
        redo=evt.redo,
        max_iter=max_iter,
        resolution=resolution,
        colormap=colormap
    )
    sleep(0.1)  # Allow rendering to catch up

    # === UI Feedback (Button Highlighting) ===
    if evt.redo:
        # Disable redo if no forward states left
        if len(mandelbrot.dimensions_redo_list) == 0:
            evt.background = vec(0.8, 0.8, 0.8)  # Gray
            evt.pointer_to_undo.background = color.white
        else:
            evt.background = color.white
            evt.pointer_to_undo.background = color.white
    else:
        # Disable undo if only one state left (initial zoom)
        if len(mandelbrot.dimensions_undo_list) < 2:
            evt.background = vec(0.8, 0.8, 0.8)  # Gray
            evt.pointer_to_redo.background = color.white
        else:
            evt.background = color.white
            evt.pointer_to_redo.background = color.white


def change_resolution(evt):
    """
    Widget callback to update the rendering resolution based on a dropdown selection.

    Parameters:
        evt (event): Event object with an `index` field, corresponding to a resolution 
                     preset in the global `resolution_choices` list.

    Behavior:
        - Grabs current max_iter and colormap settings.
        - Pops the latest image dimensions from the undo stack to maintain view consistency.
        - Applies the new resolution via `mandelbrot.change_parameters`.
    """
    global mandelbrot
    if not mandelbrot.loaded:
        return

    max_iter = mandelbrot.max_iter
    image_dimensions = mandelbrot.dimensions_undo_list.pop()
    resolution = resolution_choices[evt.index]
    colormap = mandelbrot.colormap

    mandelbrot.change_parameters(
        max_iter=max_iter,
        image_dimensions=image_dimensions,
        resolution=resolution,
        colormap=colormap
    )


def change_colormap(evt):
    """
    Widget callback to update the Mandelbrot color scheme based on a dropdown selection.

    Parameters:
        evt (event): Event object with a `selected` field containing the new colormap name.

    Behavior:
        - Keeps current resolution and max_iter.
        - Pops the most recent image frame to preserve the viewport.
        - Triggers a full redraw with the new colormap applied.
    """
    global mandelbrot
    if not mandelbrot.loaded:
        return

    max_iter = mandelbrot.max_iter
    image_dimensions = mandelbrot.dimensions_undo_list.pop()
    resolution = [mandelbrot.height, mandelbrot.width]
    colormap = evt.selected

    mandelbrot.change_parameters(
        max_iter=max_iter,
        image_dimensions=image_dimensions,
        resolution=resolution,
        colormap=colormap
    )


def change_search_depth(evt):
    """
    Widget callback to change the maximum number of iterations (search depth) used to 
    determine whether a point escapes the Mandelbrot set.

    Parameters:
        evt (event): Event object with a `number` field representing the new max iteration value.

    Behavior:
        - Validates that the number is in the accepted range [1, 1000].
        - Pops the last image dimensions to preserve the zoom level.
        - Keeps current resolution and colormap.
        - Re-renders with the new iteration depth.
    """
    global mandelbrot
    if not mandelbrot.loaded:
        return

    if evt.number < 1 or evt.number > 1000:
        print("Please enter a number between 1 - 1000")
        return

    max_iter = int(evt.number)
    image_dimensions = mandelbrot.dimensions_undo_list.pop()
    resolution = [mandelbrot.height, mandelbrot.width]
    colormap = mandelbrot.colormap

    mandelbrot.change_parameters(
        max_iter=max_iter,
        image_dimensions=image_dimensions,
        resolution=resolution,
        colormap=colormap
    )


def change_image_dimensions(evt):
    """
    Updates the Mandelbrot view to new user-specified image dimensions.

    Expects the user to enter a string in the format:
        x_min, x_max, y_min, y_max

    Example:
        evt.text = "-2.5, 1.0, -1.25, 1.25"

    Behavior:
        - Parses the input string using the custom split() function.
        - Converts the elements to floats and validates the bounds.
        - Rejects input if there aren't exactly four numbers,
          or if any min bound is greater than or equal to its max counterpart.
        - Calls mandelbrot.change_parameters() to re-render the fractal
          using the new view window.

    Parameters:
        evt: An event object passed by the winput field (must have a .text attribute).
    """
    global mandelbrot
    if not mandelbrot.loaded:
        return

    try:
        # Split input string and attempt to parse as floats
        split_elements = split(evt.text, ',')
        split_elements = [float(item) for item in split_elements]

        # Validate input: must be 4 numbers, and min < max for both x and y
        if len(split_elements) != 4:
            raise ValueError("Must provide exactly four numbers.")
        if split_elements[0] >= split_elements[1] or split_elements[2] >= split_elements[3]:
            raise ValueError("Invalid bounds: x_min ≥ x_max or y_min ≥ y_max.")
    except:
        print("Invalid dimensions.")
        return

    # Apply new dimensions and trigger a re-render
    mandelbrot.change_parameters(
        max_iter=mandelbrot.max_iter,
        image_dimensions=split_elements,
        resolution=[mandelbrot.height, mandelbrot.width],
        colormap=mandelbrot.colormap
    )


def screen_capture(evt):
    """
    Save a PNG file of the currently viewed Mandelbrot.
    """
    scene.capture("mandelbrot_screenshot")
    










# ================================ Classes =====================================

class Mandelbrot:
    def __init__(self, imaginary_function=None, max_iter=100, image_dimensions=[-2, 0.5, -1, 1], resolution=[30, 45], colormap='default'):
        """
        Initializes the Mandelbrot object with user-defined or default parameters.

        Parameters:
            imaginary_function (callable or None): Reserved for future use (e.g., Julia sets). 
                                                   Currently unused in Mandelbrot rendering.
            max_iter (int): Maximum number of iterations for escape-time algorithm.
            image_dimensions (list of float): [x_min, x_max, y_min, y_max] specifying the 
                                              viewing window in the complex plane.
            resolution (list of int): [height, width] defining the image grid resolution.
            colormap (str): Name of the colormap to apply to rendered points.

        Notes:
            - A two-stage rendering approach is used:
              1. `__load_fresh_objects()` preallocates VPython objects (quads, vertices) 
                 to improve performance during updates.
              2. `__load_new_mandelbrot()` calculates the escape-time data and applies 
                 actual position and color information to the preallocated objects.
            - Undo/redo lists track zoom history by storing previous image dimensions.
        """
        # === Parameters ===
        self.max_iter = max_iter                       # Max iterations per point
        self.x_min = image_dimensions[0]               # Real axis min
        self.x_max = image_dimensions[1]               # Real axis max
        self.y_min = image_dimensions[2]               # Imaginary axis min
        self.y_max = image_dimensions[3]               # Imaginary axis max
        self.height = resolution[0]                    # Grid height
        self.width = resolution[1]                     # Grid width
        self.colormap = colormap                       # Selected color scheme

        # === Object Recycling Buffers ===
        # These are reused to minimize VPython object creation overhead
        self.rendered_vertices = []                    # Currently rendered vertices
        self.existing_vertices = []                    # Pool of available vertex objects
        self.rendered_quads = []                       # Currently rendered quads
        self.existing_quads = []                       # Pool of available quad objects

        # === Zoom History Management ===
        self.dimensions_undo_list = [image_dimensions] # Tracks previous zoom states
        self.dimensions_redo_list = []                 # Tracks forward zoom history

        # === Initialization ===
        self.__load_fresh_objects(self.height * self.width)  # Preload empty geometry
        self.__load_new_mandelbrot()                         # Populate with actual data
        
    def __load_new_mandelbrot(self):
        """
        Calculates the Mandelbrot escape-time values for each pixel, assigns colors, 
        and updates preallocated vertex and quad objects accordingly.

        Notes:
            - This method maps screen-space pixels to points in the complex plane.
            - Instead of assigning positions in the complex plane directly (which can 
            lose precision in VPython's `vec`), pixel coordinates are mapped to a 
            normalized visual grid (e.g., [-80, 80] × [-60, 60]).
            - Colors are mapped based on iteration counts using the selected colormap.
            - Vertices are written to column buffers to construct quads on the fly.
        """
        self.loaded = False  # Disable interactions while building

        # === Derived Viewport Info ===
        center_x = (self.x_min + self.x_max) / 2
        center_y = (self.y_min + self.y_max) / 2
        view_width = self.x_max - self.x_min
        view_height = self.y_max - self.y_min

        # Pixel-to-complex step size
        zoom_x = view_width / self.width
        zoom_y = view_height / self.height

        # === Double Column Buffers for Quad Linking ===
        current_col = [None] * self.height
        previous_col = current_col[:]

        # === Main Rendering Loop ===
        for px in range(self.width):
            for py in range(self.height):
                # Map pixel to complex plane
                x = center_x + (px - self.width / 2) * zoom_x
                y = center_y + (py - self.height / 2) * zoom_y

                # Escape-time algorithm (Z_n+1 = Z_n^2 + C)
                c_re, c_im = x, y
                z_re, z_im = 0, 0
                n = 0
                while sqrt(z_re**2 + z_im**2) <= 2 and n < self.max_iter:
                    z_re_old = z_re
                    z_re = z_re_old * z_re_old - z_im * z_im + c_re
                    z_im = 2 * z_re_old * z_im + c_im
                    n += 1

                # Color assignment based on escape depth
                if n == self.max_iter:
                    pixel_color = vec(0, 0, 0)  # Inside set = black
                else:
                    color_value = vec(1, 1, 1) * (n / self.max_iter)
                    pixel_color = colormaps(colors=color_value, cmap=self.colormap)

                # Recycle a vertex and assign its position/color
                old_vertex = self.existing_vertices.pop()
                old_vertex.pos = vec(px - self.width / 2, py - self.height / 2, 0)
                old_vertex.color = pixel_color
                current_col[py] = old_vertex
                self.rendered_vertices.append(old_vertex)

                # Update quad connections using previous and current column buffers
                if px > 0 and py > 0:
                    pixel = self.existing_quads.pop()
                    pixel.v0 = current_col[py]
                    pixel.v1 = current_col[py - 1]
                    pixel.v2 = previous_col[py - 1]
                    pixel.v3 = previous_col[py]
                    pixel.visible = True
                    self.rendered_quads.append(pixel)

            # Roll current column to previous
            previous_col = current_col[:]

        # === Finalization ===
        self.loaded = True
        loading_text.visible = False
        scene.range = self.height / 2
        sleep(0.1)  # Allow VPython to visually update the scene

    def change_parameters(self, max_iter=100, image_dimensions=[-2, 0.5, -1, 1], resolution=[30, 45], colormap='default'):
        """
        Updates Mandelbrot parameters and triggers a full redraw.

        Parameters:
            max_iter (int): Maximum iterations for escape-time calculation.
            image_dimensions (list): [x_min, x_max, y_min, y_max] defining the view in the complex plane.
            resolution (list): [height, width] pixel resolution of the output grid.
            colormap (str): Name of the color scheme to apply.

        Behavior:
            - Recycles all currently rendered objects to the reuse pool.
            - Applies new parameters (zoom window, resolution, iterations, etc.).
            - Calculates how many new objects (if any) need to be created.
            - Preloads additional geometry if needed.
            - Re-renders the Mandelbrot set with the updated settings.
        """
        self.loaded = False  # Disable interactions while building
        self.__recycle_old_vertices()  # Move active objects to reusable pools

        # === Apply New Parameters ===
        self.max_iter = max_iter
        self.x_min = image_dimensions[0]
        self.x_max = image_dimensions[1]
        self.y_min = image_dimensions[2]
        self.y_max = image_dimensions[3]
        self.height = resolution[0]
        self.width = resolution[1]
        self.colormap = colormap
        self.dimensions_undo_list.append(image_dimensions)

        # === Display Current Image Dimensions ===
        dimensions_display_winput.text = f'{self.x_min}, {self.x_max}, {self.y_min}, {self.y_max}'

        # === Load Geometry If Needed ===
        previous_load_size = len(self.existing_vertices)
        fresh_load_size = self.height * self.width - previous_load_size
        self.__load_fresh_objects(fresh_load_size)

        # === Render New Image ===
        self.__load_new_mandelbrot()

    def __recycle_old_vertices(self):
        """
        Moves all currently rendered vertices and quads into their respective reuse pools.

        Notes:
            - Ensures memory-efficient redraws by avoiding creation of redundant VPython objects.
            - Marks quads as invisible to hide them during the next frame.
            - Clears the active render buffers.
        """
        # Recycle all rendered vertices
        for vertex in self.rendered_vertices:
            self.existing_vertices.append(vertex)

        # Recycle all rendered quads and hide them
        for quad in self.rendered_quads:
            self.existing_quads.append(quad)
            quad.visible = False

        # Clear active render buffers
        self.rendered_vertices = []
        self.rendered_quads = []

    def load_recent_dimensions(self, redo=False, max_iter=100, image_dimensions=[-2, 0.5, -1, 1], resolution=[30, 45], colormap='default'):
        """
        Loads a previously viewed Mandelbrot frame, supporting both undo and redo actions.

        Parameters:
            redo (bool): If True, performs a redo action (forward in history).
                        If False, performs an undo (backward in history).
            max_iter (int): Maximum number of iterations to apply during redraw.
            image_dimensions (list): Placeholder (ignored — actual value is taken from history stacks).
            resolution (list): Current image resolution to maintain display scale.
            colormap (str): Current colormap to maintain visual consistency.

        Behavior:
            - If `redo` is True and the redo stack has entries, loads the most recent one.
            - If `redo` is False and the undo stack has more than one entry,
            pushes the current frame to the redo stack and loads the previous frame.
            - Calls `change_parameters()` to re-render the scene.
            - If neither case is valid (stacks are empty), does nothing.
        """
        self.loaded = False  # Disable interactions while building
        
        if redo:
            if len(self.dimensions_redo_list) > 0:
                image_dimensions_to_load = self.dimensions_redo_list.pop()
            else:
                return  # No redo state available
        else:
            if len(self.dimensions_undo_list) <= 1:
                return  # Can't undo beyond the initial view
            self.dimensions_redo_list.append(self.dimensions_undo_list.pop())
            image_dimensions_to_load = self.dimensions_undo_list.pop()

        # Trigger redraw with restored parameters
        self.change_parameters(
            max_iter=max_iter,
            image_dimensions=image_dimensions_to_load,
            resolution=resolution,
            colormap=colormap
        )


    def __load_fresh_objects(self, fresh_load_size):
        """
        Preallocates a pool of invisible vertex and quad objects to speed up rendering.

        Parameters:
            fresh_load_size (int): Number of vertices to generate. Typically equal to 
                                height × width of the grid.

        Notes:
            - This method avoids the overhead of creating objects on demand during rendering.
            - All objects are initialized with placeholder values and stored in recyclable lists.
            - Quads are only allocated once for each 2×2 cell in the grid (i.e., (height - 1) × width).
            - The external `loading_text` object is assumed to be a VPython text label that provides 
            UI feedback and must be created before calling this method.
            - A short sleep allows VPython to visually update the loading message before blocking.
        """
        scene.range = 10  # Reset scene zoom for clarity during loading
        loading_text.visible = True  # Show the "Loading..." label
        sleep(0.1)  # Allow a visual update before intensive work begins

        for i in range(fresh_load_size):
            # Create a dummy vertex with neutral values
            blank_vertex = vertex(
                pos=vec(0, 0, 0),         # Temporary placeholder position
                color=vec(0, 0, 0),       # Will be updated later in rendering
                normal=vec(0, 0, 1),      # Default normal (perpendicular to screen)
                emmisive=True,           # Ensures color is unaffected by lighting
                shininess=0              # No specular reflection
            )
            self.existing_vertices.append(blank_vertex)

            # Only create quads where needed (each quad spans a 2×2 vertex region)
            if len(self.existing_quads) < (self.height - 1) * self.width:
                blank_quad = quad(
                    v0=blank_vertex,     # Temporarily use the same vertex for all corners
                    v1=blank_vertex,
                    v2=blank_vertex,
                    v3=blank_vertex,
                    visible=False        # Will be updated and made visible later
                )
                self.existing_quads.append(blank_quad)

        sleep(0.01)  # Yield control so browser doesn't freeze during long allocation









# ================================ Simulation Globals ==========================

# Available resolution presets for rendering (width x height)
resolution_choices = [
    [30, 45], [60, 90], [120, 180], [180, 270], [240, 360], [480, 720]
]
resolution_choices_str = [
    '30x45', '60x90', '120x180', '180x270', '240x360', '480x720'
]

# Available colormaps supported by the project
colormap_choices = ['default', 'inferno', 'viridis', 'spectral', 'plasma']

# Track mouse state: True means left mouse button is released, False means pressed
mouse_1_up = True

# Loading text indicator, hidden initially
loading_text = text(text='Loading :)', align='center', color=color.white, visible=False)

# Create the main Mandelbrot instance with a default mid-range resolution preset
mandelbrot = Mandelbrot(resolution=resolution_choices[3])  # 120x160 pixels


# ============================== Interactive Widgets ===========================
# Screenshot Button: Capture a PNG of the currently viewed Mandelbrot, named "mandelbrot_screenshot.png"
screenshot_button = button(
    text='Screenshot',
    pos=scene.title_anchor,
    background=color.white,
    bind=screen_capture
)

# Undo Button: Step back to previous zoom/view parameters
undo_dimension_change_button = button(
    text='Undo',
    pos=scene.title_anchor,
    background=vec(0.8, 0.8, 0.8),   # Gray background (disabled look initially)
    bind=recall_mandelbrot_dimensions,  # Shared callback for undo/redo
    button_title=wtext(text='  ', pos=scene.title_anchor),
    redo=False,                     # Custom attribute: False for undo behavior
    pointer_to_redo=None            # Will be linked to redo button below
)

# Redo Button: Step forward to a view undone previously
redo_dimension_change_button = button(
    text='Redo',
    pos=scene.title_anchor,
    background=vec(0.8, 0.8, 0.8),  # Gray background (disabled look initially)
    bind=recall_mandelbrot_dimensions,
    button_title=wtext(text='  ', pos=scene.title_anchor),
    redo=True,                      # Custom attribute: True for redo behavior
    pointer_to_undo=undo_dimension_change_button
)

# Link undo button to redo button so they can update each other’s state/color
undo_dimension_change_button.pointer_to_redo = redo_dimension_change_button


# Colormap selection dropdown menu
colormap_menu = menu(
    choices=colormap_choices,
    selected=colormap_choices[0],  # Default: 'default'
    pos=scene.title_anchor,
    bind=change_colormap,
    menu_title=wtext(text='<b> Colormap:</b> ', pos=scene.title_anchor)
)

# Resolution selection dropdown menu
image_resolution_menu = menu(
    choices=resolution_choices_str,
    selected=resolution_choices_str[3],  # Default: '120x160'
    pos=scene.title_anchor,
    bind=change_resolution,
    menu_title=wtext(text='<b> Resolution:</b> ', pos=scene.title_anchor)
)

# Numeric input widget for Mandelbrot iteration depth (search depth)
mandel_search_depth_winput = winput(
    type='numeric',
    width=30,
    height=20,
    text=mandelbrot.max_iter,
    pos=scene.title_anchor,
    bind=change_search_depth,
    title_wtext_obj=wtext(text='  <b>Depth:</b>', pos=scene.title_anchor),
    suffix_wtext_obj=None,  # Populated below to add iteration label
    obj_type='winput'
)

# Add "iterations" suffix label next to numeric input field
mandel_search_depth_winput.suffix_wtext_obj = wtext(
    text=' iterations',
    pos=scene.title_anchor
)

# Create coordinate wtext readout for the current image center and zoom level
dimensions_display_winput = winput(
    type='string',
    width=650,
    height=20,
    text=f'{mandelbrot.x_min}, {mandelbrot.x_max}, {mandelbrot.y_min}, {mandelbrot.y_max}',
    pos=scene.title_anchor,
    bind=change_image_dimensions,
    title_wtext_obj=wtext(
        text='\n<b>Current image dimensions (x min/max, y min/max):</b> ',
        pos=scene.title_anchor
    )
)
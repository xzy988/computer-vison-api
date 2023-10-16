import colorsys
import random
import numpy as np
import tempfile
import imageio
import shutil
from PIL import Image, ImageDraw, ImageFont
from skimage.transform import resize
from keras import backend as K
from functools import reduce
from streamlit_modules.button_style import button_style

def preprocess_image(img_path, model_image_size, done : bool = False):
    #image_type = imghdr.what(img_path)
    if done is False : image           = Image.open(img_path)
    else: image = img_path

    shape           = np.array(image).shape
    resized_image   = image.resize(tuple(reversed(model_image_size)), Image.BICUBIC)
    image_data      = np.array(resized_image, dtype='float32')
    image_data /= 255.
    # Add batch dimension.
    image_data      = np.expand_dims(image_data, 0) 

    return image.resize(model_image_size), image_data, shape

def compose(*funcs):
    """Compose arbitrarily many functions, evaluated left to right.

    Reference: https://mathieularose.com/function-composition-in-python/
    """
    # return lambda x: reduce(lambda v, f: f(v), funcs, x)
    if funcs:
        return reduce(lambda f, g: lambda *a, **kw: g(f(*a, **kw)), funcs)
    else:
        raise ValueError('Composition of empty sequence not supported.')

def read_classes(classes_path : str = './data/coco_classes.txt'):

    with open(classes_path) as f:
        class_names = f.readlines()
    class_names = [c.strip() for c in class_names]
    return class_names

def read_anchors(anchors_path : str = './data/yolo_anchors.txt'):

    with open(anchors_path) as f:
        anchors = f.readline()
        anchors = [float(x) for x in anchors.split(',')]
        anchors = np.array(anchors).reshape(-1, 2)
    return anchors

def scale_boxes(boxes, image_shape):
    """ Scales the predicted boxes in order to be drawable on the image"""
    height = float(image_shape[0])
    width = float(image_shape[1])
    image_dims = K.stack([height, width, height, width])
    image_dims = K.reshape(image_dims, [1, 4])
    boxes = boxes * image_dims
    return boxes

def get_colors_for_classes(num_classes):
    """Return list of random colors for number of classes given."""
    # Use previously generated colors if num_classes is the same.
    if (hasattr(get_colors_for_classes, "colors") and
            len(get_colors_for_classes.colors) == num_classes):
        return get_colors_for_classes.colors

    hsv_tuples = [(x / num_classes, 1., 1.) for x in range(num_classes)]
    colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
    colors = list(
        map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)),
            colors))
    random.seed(10101)  # Fixed seed for consistent colors across runs.
    random.shuffle(colors)  # Shuffle colors to decorrelate adjacent classes.
    random.seed(None)  # Reset seed to default.
    get_colors_for_classes.colors = colors  # Save colors for future calls.

    return colors

def draw_boxes(image, boxes, box_classes, class_names, scores=None, use_classes : list = [], df = {}):
    """
    Draw bounding boxes on image.

    Draw bounding boxes with class name and optional box score on image.

    Args:
        image: An `array` of shape (width, height, 3) with values in [0, 1].
        boxes: An `array` of shape (num_boxes, 4) containing box corners as
            (y_min, x_min, y_max, x_max).
        box_classes: A `list` of indicies into `class_names`.
        class_names: A `list` of `string` class names.
        `scores`: A `list` of scores for each box.

    Returns:
        A copy of `image` modified with given bounding boxes.
    """

    
    font = ImageFont.truetype(
        font='font/FiraMono-Medium.otf',
        size=np.floor(3e-2 * image.size[1] + 0.5).astype('int32'))
    thickness   = (image.size[0] + image.size[1]) // 300
    colors      = get_colors_for_classes(len(class_names))

    for i, c in list(enumerate(box_classes)):
        box_class   = class_names[c]
        box         = boxes[i]
        
        if isinstance(scores.numpy(), np.ndarray):
            score   = scores.numpy()[i]
            label   = '{} {:.2f}'.format(box_class, score)
        else: label = '{}'.format(box_class)

        if label.split()[0] in use_classes:
            
            draw        = ImageDraw.Draw(image)
            label_size  = draw.textlength(text=label, font=font)
            top, left, bottom, right = box
            top         = max(0, np.floor(top + 0.5).astype('int32'))
            left        = max(0, np.floor(left + 0.5).astype('int32'))
            bottom      = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
            right       = min(image.size[0], np.floor(right + 0.5).astype('int32'))

            df['top'].append(top)
            df['left'].append(left)
            df['bottom'].append(bottom)
            df['right'].append(right)
            df['score'].append(float(label.split()[1]))
            df['label'].append(label.split()[0])


            """
            if top -  >= 0: #label_size[1] >= 0:
                text_origin = np.array([left, top - label_size]) # label_size[1]])
            else:  text_origin = np.array([left, top + 1])
            """

            text_origin = np.array([left, top - 20])
            # My kingdom for a good redistributable image drawing library.
            for i in range(thickness):
                draw.rectangle(
                    [left + i, top + i, right - i, bottom - i], outline=colors[c]
                    )
            draw.rectangle(
                [tuple(text_origin), tuple(text_origin + (label_size, 20))],
                fill=colors[c]
                )
            draw.text(text_origin, label, fill=(0, 0, 0), font=font)
            del draw
        else : pass 

    return np.array(image)

def read_video(image):
    import imageio
    video_reader    = imageio.get_reader(image, mode='?')
    fps             = video_reader.get_meta_data()['fps']
    video_frame     = video_reader.count_frames()
    duration        = float(video_frame / fps)

    return video_reader, [fps, video_frame, duration]

def total_precess(st, prediction, estimator, video, df, details, **kwargs):
    import time 

    storage             = []
    frame_count         = 0
    fps                 = video.get_meta_data()['fps']
    (start, end, step)  = details

    run = button_style(st=st, name='run')

    if run:   
        # progress bar 
        progress_text   = "Operation in progress. Please wait."
        my_bar          = st.progress(0, text=progress_text)
   
        for i, frame in enumerate(video):
            if i in range(start, end, step):
                frame                       = Image.fromarray(frame, mode='RGB')
                frame, frame_data, shape    = preprocess_image(img_path=frame, model_image_size = (608, 608), done=True)        
                frame_count                += 1
                
                image_predicted = prediction(yolo_model=estimator, use_classes=kwargs['class_names'],
                                    image_file=[(frame, frame_data)], anchors=kwargs['anchors'], 
                                    class_names=kwargs['Class_names'], img_size=(608, 608),
                                    max_boxes=kwargs['max_boxes'], score_threshold=kwargs['score_threshold'], 
                                    iou_threshold=kwargs['iou_threshold'], data_dict=df,shape=shape[:-1], file_type='video')
                
                storage.append(image_predicted)

                if i <= 100:
                    time.sleep(0.01)
                    my_bar.progress(i, text=progress_text)
            else: pass
        else: pass

        storage = np.array(storage).astype('float32')

        # Définir le chemin de sortie pour la vidéo
        #output_video_path = 'video_output2.mp4'
        temp_video_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")

        # Écrire le tableau NumPy dans une vidéo avec imageio
        with imageio.get_writer(temp_video_file.name, mode='?', fps=fps) as writer:
            for image in storage:
                writer.append_data(image)

        # Ouvrir le fichier temporaire en mode lecture binaire (rb)
        with open(temp_video_file.name, 'rb') as temp_file:
            # Lire le contenu du fichier temporaire
            video_data = temp_file.read()

        shutil.rmtree(temp_video_file.name, ignore_errors=True)
        my_bar.empty()

        return video_data, fps
    
    else: return None, None
import tensorflow as tf  
import pandas as pd 
from yolo.utils.tools import total_precess
from streamlit_modules.file_read import file_read, online_link
from yolo.utils.tools import read_classes, read_anchors
from yolo.predictions import prediction
from streamlit_modules.button_style import button_style
import plotly.express as px
import logging
from yolo import video_settings as vs 
from yolov8_ops import ocr_yolov8, ocr, yolov8, yolov8_seg

def pred(st):
    st.write('<style>{}</style>'.format(styles()), unsafe_allow_html=True)
    st.write(f'<h1 class="header-text">Welcome in prediction section</h1>', unsafe_allow_html=True)

    yolo_model_path = './yolo_model/' 

    # three columns for local file, show file updated, image scale factor 
    col1, col2, col3 = st.columns(3)
    
    with col1:
        label_select = st.selectbox('Local or Online File', options=('Local', 'Online'), index=None)
    with col2:
        show = st.checkbox('Show files uploaded')
        st.write('state', show)
    with col3:
        #if show : desable_scale = False 
        desable_scale  = False
        model_type = st.selectbox(label='Select models', options=('yolov8', "yolov5", 'yolov8-seg', 'ocr', 'ocr+yolov8', 'yolov8-pose', 'my model'), disabled=desable_scale)

    if model_type == 'ocr+yolov8': factor = True 
    else: factor = False 

    if label_select:
        if label_select == 'Local':
            if label_select: 
                uploaded_file = st.file_uploader("upload local image or video", 
                                                type=["jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "avi", "mkv"],
                                                accept_multiple_files=True
                                                )
                if uploaded_file:
                    if show : show = True 
                    # get the informations about the video or image s
                    # video, image, image shape, and more ...
                    if model_type == 'my model': locked = False 
                    else: locked = True 

                    all_files = file_read(st, uploaded_file=uploaded_file, show=False, factor=factor)
                    [iou_threshold, score_threshold, max_boxes] = vs.slider_model(st=st, locked=locked)

                    # classses and anchors 
                    Class_names         = read_classes()
                    anchors             = read_anchors()

                    # five columns for use all classes, class probabilitiess etc....
                    cp_col1, cp_col2, cp_col3, cp_col4, cp_col5 = st.columns(5)

                    with cp_col2:
                        cp_check = st.checkbox("Use all classes")
                        st.write('state', cp_check)

                    with cp_col1:
                        # if use all is true cp_disable become True 
                        if cp_check :  cp_disable = True  
                        else: cp_disable  = False 

                        # select multi-classs probabilities 
                        class_names = st.multiselect("Classes", options=Class_names, disabled=cp_disable)

                        if class_names: pass 
                        else: 
                            # Class_names can be different ro class_name 
                            if cp_check : class_names = Class_names
                            else: pass 
                            
                    if class_names:
                        with cp_col3:
                            # select file type (video or image)
                            file_type = st.radio('File Types', options=('image', 'video'))
                        
                        if file_type:
                            # index of one file (video or image)
                            if all_files[f'{file_type}']: indexes = range(len( all_files[f'{file_type}']))
                            else: indexes = None 

                            if indexes: 
                                with cp_col4:
                                    # select iindex of file
                                    index = st.selectbox('Select file index', options=indexes)
                                
                                if index >= 0:
                                    items  = {
                                    'class_names' : class_names,
                                    'anchors' : anchors,
                                    'Class_names' : Class_names,
                                    'max_boxes' : max_boxes,
                                    'score_threshold' : score_threshold,
                                    'iou_threshold' : iou_threshold 
                                    }
                                    
                                    tf.get_logger().setLevel(logging.ERROR)
                                    yolo_model = tf.keras.models.load_model(yolo_model_path, compile=False)
                                    df = {'label' : [], 'score':[], 'top':[], "left":[], "bottom":[], 'right':[]}

                                    if file_type == 'image':
                                        items['image_file'] = [all_files['image'][index]]
                                        shape = all_files['image_shape'][index][:-1]
                                        Image(st=st, yolo_model_path=yolo_model_path, df=df, col=cp_col5, 
                                              shape=shape, model_type=model_type, show=show, **items)
                                    else:
                                        details = all_files['details'][index]
                                        details = vs.slider_video(st, *details)
                                        video   = all_files['video_reader'][index]
                                        Video(st=st, prediction=prediction, yolo_model=yolo_model, video=video, model_type=model_type,
                                                                             df=df, details=details, show=show, **items)
                                else: pass
                            else: pass
                        else: pass 
                    else: pass
                else: pass
            else: pass 
        elif label_select == 'Online': 
            if show : show = True 

            type_of_file = st.selectbox('File type', options=('image', 'video'), index=None)

            if type_of_file:
                url = st.text_input("Insert your url here please :")
            else: url = ""

            if url:
                if type_of_file == 'image':
                    image, image_data, shape,  error = online_link(st=st, url=url)

                    if error is None:
                        [iou_threshold, score_threshold, max_boxes] = vs.slider_model(st=st)

                        # classses and anchors 
                        Class_names         = read_classes()
                        anchors             = read_anchors()

                        # five columns for use all classes, class probabilitiess etc....
                        cp_col1, cp_col2, cp_col3 = st.columns(3)

                        with cp_col2:
                            cp_check = st.checkbox("use all classes")

                        with cp_col1  :
                            # if use all is true cp_disable become True 
                            if cp_check :  cp_disable = True  
                            else: cp_disable  = False 

                            # select multi-classs probabilities 
                            class_names = st.multiselect("class probabilities", options=Class_names, disabled=cp_disable)

                            if class_names: pass 
                            else: 
                                # Class_names can be different ro class_name 
                                if cp_check : class_names = Class_names
                                else: pass 

                        if class_names: 
                            items  = {
                                'class_names' : class_names,
                                'anchors' : anchors,
                                'Class_names' : Class_names,
                                'max_boxes' : max_boxes,
                                'score_threshold' : score_threshold,
                                'iou_threshold' : iou_threshold,
                                'image_file'   : [(image, image_data)]
                                }
                            if file_type == 'image':
                                tf.get_logger().setLevel(logging.ERROR)
                                yolo_model = tf.keras.models.load_model(yolo_model_path, compile=False)
                                df = {'label' : [], 'score':[], 'top':[], "left":[], "bottom":[], 'right':[]}
                                Image(st=st, yolo_model_path=yolo_model_path, df=df, col=cp_col3, shape=shape, model_type=model_type,
                                    show=show, **items) 
                            else: pass
                        else: pass
                    else: pass 

                elif type_of_file == 'video':
                    if url:
                        st.write(f'<video width="640" height="360" controls><source src="{url}" type="video/mp4"></video>', unsafe_allow_html=True)
                else: pass
            else: pass
            #st.video()
    else: pass

def Image(st, yolo_model_path, df, col, shape, model_type, show, **kwargs):
    import numpy as np 

    with col:
        response = st.checkbox('With scores')
        st.write('state', response)
    if button_style(st=st, name='run'):

        if model_type == 'my model':
            tf.get_logger().setLevel(logging.ERROR)
            yolo_model = tf.keras.models.load_model(yolo_model_path, compile=False)
            df = {'label' : [], 'score':[], 'top':[], "left":[], "bottom":[], 'right':[]}

            image_predicted = prediction(
                yolo_model=yolo_model, use_classes=kwargs['class_names'],
                image_file=kwargs['image_file'], anchors=kwargs['anchors'], class_names=kwargs['Class_names'], img_size=(608, 608),
                max_boxes=kwargs['max_boxes'], score_threshold=kwargs['score_threshold'], iou_threshold=kwargs['iou_threshold'], data_dict=df,
                shape=shape, file_type='image', with_score=response
            )
            resume(st=st, df=df, show=show, **{"image_predicted" : image_predicted})
        
        if model_type == 'yolov8':
            yolov8.yolov8(st, df, shape, show, response, resume, False, **kwargs)
        
        if model_type == 'yolov8-seg':
            yolov8_seg.yolov8_seg(st, df, shape, show, response, resume, **kwargs)
        
        if model_type == 'yolov8-pose':
            st.wrilte("YOLOV8 for pose detection is not yet implimented.")
        
        if model_type == 'yolov5':
            st.wrilte("YOLOV5 for object detection is not yet implimented.")
        
        if model_type == 'ocr+yolov8':
            ocr_yolov8.ocr_yolov8(st, df, shape, show, response, resume, scaling, **kwargs)

        if model_type == 'ocr':
            ocr.ocr(st, df, shape, show, response, resume, scaling, **kwargs)

    else: pass

def scaling(image = None, shape = (608, 608), boxes = None, S = None):
    import cv2

    # Mettez à l'échelle l'image
    scaled_image    = image.resize(shape)
    new_width       = shape[0]
    new_height      = shape[1]
    # Mettez à l'échelle les boîtes englobantes
    scaling_factor_x = new_width / S[0]
    scaling_factor_y = new_height / S[1]

    scaled_boxes = []
    for box in boxes:
        x_min, y_min, x_max, y_max = box
        scaled_x_min = int(x_min * scaling_factor_x)
        scaled_y_min = int(y_min * scaling_factor_y)
        scaled_x_max = int(x_max * scaling_factor_x)
        scaled_y_max = int(y_max * scaling_factor_y)
        scaled_boxes.append([scaled_x_min, scaled_y_min, scaled_x_max, scaled_y_max])

    return scaled_boxes, scaled_image

def Video(st, prediction, yolo_model, video, df, details, show, model_type, **kwargs):
    if model_type == 'my model':
        items           = {
                        'class_names' : kwargs['class_names'],
                        'anchors' : kwargs['anchors'],
                        'Class_names' : kwargs['Class_names'],
                        'max_boxes' : kwargs['max_boxes'],
                        'score_threshold' : kwargs['score_threshold'],
                        'iou_threshold' : kwargs['iou_threshold'] 

                    }
        video_reader, fps = total_precess(st=st, prediction=prediction, 
                            estimator=yolo_model, video=video, df=df, details=details, **items)

        if video_reader:
            resume(st=st, df=df, file_type='video', show=show, **{'fps' : fps, 'video_reader' : video_reader})
        else: pass 
    
    if model_type == 'yolov8':
        yolov8.yolovo_video(st, video, df, details, show, resume, **items)

def resume(st, df : dict, file_type: str='image', img=None, show=True, **kwargs):
    with st.expander("MODEL PERFORMANCES"):
        st.write("""
            You can observe the chosen predicted classes at the top, and it's 
            important to note that these class predictions are influenced by 
            factors like the IoU threshold, score threshold, and the quantity 
            of boxes. Adjusting these parameters allows you to fine-tune your 
            predictions for improving accuracy.

            Great job, you've done excellently!
        """)

        if file_type == 'image': 
            if show is False : st.image(kwargs['image_predicted'])
            else:
                c1, c2 = st.columns(2)
                pred = kwargs['image_predicted']
                with c1:
                    st.image(img.resize((pred.shape[1], pred.shape[0])))
                with c2:
                    st.image(pred)
        else :
            st.write(f"frame rate per second : {kwargs['fps']}") 
            st.video(kwargs['video_reader'])

        if df['label']:
            #fig_col1, fig_col2 = st.columns(2)
            data_frame = pd.DataFrame(df)
            data_frame.rename(columns={'label':'classes'}, inplace=True)
            data_frame['label'] = [1 for i in range(len(data_frame.iloc[:, 0]))]

            #with fig_col1:
            
            st.dataframe(data=data_frame.style.highlight_max(axis=0, color='skyblue', subset=['classes', 'score']))
            fig = px.pie(data_frame, names='classes', values='label', title='pie chart')

            #with fig_col2:                                                
            st.plotly_chart(fig, use_container_width=True)

        else: pass 

def styles():
     
    custom_css_title = """
        .header-text {
            color: black; /* Couleur du texte */
            /*background-color: white; Couleur de l'arrière-plan */
            font-size: 25px; /* Taille de police */
            font-weight: bolder; /* Gras */
            text-decoration: none; /* Souligné underline overline */
            font-family: Arial, sans-serif; /* font family*/
            text-align: justify;
            background-image: darkgray;
            border-radius: 5px; /* Coins arrondis */
            margin: 3px; /* Marge extérieure */
            border: 2px solid #555; /* Bordure */
            padding: 5px; /* Marge intérieure pour le texte */
            display: inline-block;
        }
        """
    return custom_css_title
import cv2
# pyrefly: ignore [missing-import]
import mediapipe as mp
import numpy as np
import math
import os

def remove_hair(frame, category_mask):
    # category_mask is a mediapipe Image. Get numpy array.
    mask_np = category_mask.numpy_view()
    
    # In MediaPipe hair segmenter, class 1 is hair.
    # Create a binary mask where hair is 255, else 0
    hair_mask = (mask_np == 1).astype(np.uint8) * 255
    
    if cv2.countNonZero(hair_mask) == 0:
        return frame
        
    # Expand the mask slightly to cover edges
    kernel = np.ones((15, 15), np.uint8)
    hair_mask = cv2.dilate(hair_mask, kernel, iterations=1)
    
    # Use OpenCV inpainting to remove the hair and fill it with surrounding pixels
    blended = cv2.inpaint(frame, hair_mask, 15, cv2.INPAINT_TELEA)
    
    return blended

def load_hat_image(path):
    if not os.path.exists(path):
        print(f"Hat image not found at {path}")
        return None
        
    img = cv2.imread(path)
    if img is None:
        return None
        
    # Convert to BGRA
    img_bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    
    # Make white background transparent
    # White is roughly > 240 in all channels
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    img_bgra[mask == 255, 3] = 0
    
    # Crop to bounding box of non-transparent pixels so scaling is accurate
    coords = cv2.findNonZero((mask < 255).astype(np.uint8))
    if coords is not None:
        hx, hy, hw, hh = cv2.boundingRect(coords)
        img_bgra = img_bgra[hy:hy+hh, hx:hx+hw]
    
    return img_bgra

def overlay_transparent(background, overlay, x, y):
    h, w = overlay.shape[0], overlay.shape[1]
    bh, bw = background.shape[0], background.shape[1]
    
    if x >= bw or y >= bh or x + w <= 0 or y + h <= 0:
        return background
        
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(bw, x + w)
    y2 = min(bh, y + h)
    
    ox1 = max(0, -x)
    oy1 = max(0, -y)
    ox2 = ox1 + (x2 - x1)
    oy2 = oy1 + (y2 - y1)
    
    overlay_crop = overlay[oy1:oy2, ox1:ox2]
    bg_crop = background[y1:y2, x1:x2]
    
    alpha = overlay_crop[:, :, 3] / 255.0
    alpha = np.expand_dims(alpha, axis=2)
    
    res = bg_crop * (1 - alpha) + overlay_crop[:, :, :3] * alpha
    background[y1:y2, x1:x2] = res
    return background

def draw_hat(frame, landmarks, hat_img, w, h):
    if hat_img is None:
        return frame
        
    left_ear = landmarks.landmark[234]
    right_ear = landmarks.landmark[454]
    
    lx, ly = int(left_ear.x * w), int(left_ear.y * h)
    rx, ry = int(right_ear.x * w), int(right_ear.y * h)
    
    # Calculate distance and angle between ears
    dist = math.hypot(rx - lx, ry - ly)
    angle = math.degrees(math.atan2(ry - ly, rx - lx))
    
    # Calculate head height (chin to top of forehead)
    top = landmarks.landmark[10]
    chin = landmarks.landmark[152]
    face_h = math.hypot(chin.x * w - top.x * w, chin.y * h - top.y * h)
    
    # Hat width: scale to fit the entire visible width of the head (including the wide bald area from the original curly hair)
    # 2.3x the ear-to-ear distance covers the wide sides completely
    hat_w = int(dist * 2.3)
    
    # Hat height: make it tall enough to sit proportionally on the large bald head
    hat_h = int(face_h * 1.3)
    
    # Resize hat without preserving original aspect ratio
    hat_resized = cv2.resize(hat_img, (hat_w, hat_h))
    
    # Rotate hat
    center = (hat_w // 2, hat_h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate bounding box of rotated image to prevent cropping
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int((hat_h * sin) + (hat_w * cos))
    new_h = int((hat_h * cos) + (hat_w * sin))
    
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    
    hat_rotated = cv2.warpAffine(hat_resized, M, (new_w, new_h), borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    
    # Calculate position
    # The center between the ears
    cx = (lx + rx) / 2
    cy = (ly + ry) / 2
    
    # Shift up so the bottom sits naturally across the forehead, above the eyebrows
    shift_y = hat_h * 0.45
    
    # Adjust for face rotation
    shift_x_rot = shift_y * math.sin(math.radians(angle))
    shift_y_rot = shift_y * math.cos(math.radians(angle))
    
    pos_x = int(cx + shift_x_rot - new_w / 2)
    pos_y = int(cy - shift_y_rot - new_h / 2)
    
    return overlay_transparent(frame, hat_rotated, pos_x, pos_y)

def main():
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
        
    hat_img_path = r"C:\Users\ryani_jvpdg6k\.gemini\antigravity-ide\brain\3efe0573-ca40-490b-9262-6b5e3516070c\bobble_hat_1789588103543.jpg"
    hat_img = load_hat_image(hat_img_path)
    
    show_hat = False
        
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'face_landmarker.task')
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1)
        
    seg_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hair_segmenter.tflite')
    seg_base_options = python.BaseOptions(model_asset_path=seg_model_path)
    seg_options = vision.ImageSegmenterOptions(
        base_options=seg_base_options,
        output_category_mask=True)
        
    print("Press SPACE to toggle the bobble hat.")
    print("Press ESC or 'q' to exit.")
        
    with vision.FaceLandmarker.create_from_options(options) as landmarker, \
         vision.ImageSegmenter.create_from_options(seg_options) as segmenter:
        
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                break
                
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
            
            # Detect face landmarks and segment hair
            detection_result = landmarker.detect(mp_image)
            segmentation_result = segmenter.segment(mp_image)
            
            if segmentation_result.category_mask is not None:
                image = remove_hair(image, segmentation_result.category_mask)

            if detection_result.face_landmarks:
                for face_landmarks in detection_result.face_landmarks:
                    h, w, _ = image.shape
                    
                    # Convert to structure similar to old API for the drawing functions
                    class DummyLandmarks:
                        pass
                    class DummyLandmarkList:
                        def __init__(self, landmarks):
                            self.landmark = landmarks
                    
                    dummy_landmarks = DummyLandmarkList(face_landmarks)
                    
                    # Apply the bobble hat if enabled
                    if show_hat:
                        image = draw_hat(image, dummy_landmarks, hat_img, w, h)
            
            # Flip the image horizontally for a selfie-view display.
            cv2.imshow('Bald & Hat Filter', cv2.flip(image, 1))
            
            key = cv2.waitKey(5) & 0xFF
            if key == 27 or key == ord('q'): # ESC or q
                break
            elif key == 32: # SPACE
                show_hat = not show_hat
                
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
import cv2, os, numpy as np
from pdf2image import convert_from_path

def deskew(image):
    gray = image if len(image.shape)==2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(gray > 0))
    angle = 0.0
    if coords.size > 0:
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45: angle = -(90 + angle)
        else: angle = -angle
    (h, w) = image.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def preprocess_image(path):
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    desk = deskew(gray)
    thr = cv2.threshold(desk, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    den = cv2.medianBlur(thr, 3)
    out_path = f"cleaned_{os.path.basename(path)}"
    cv2.imwrite(out_path, den)
    return out_path

def preprocess_input(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    out_paths = []
    if ext == ".pdf":
        pages = convert_from_path(file_path, dpi=300)
        for i, page in enumerate(pages):
            ip = f"page_{i+1}.png"
            page.save(ip, "PNG")
            out_paths.append(preprocess_image(ip))
    else:
        out_paths.append(preprocess_image(file_path))
    return out_paths

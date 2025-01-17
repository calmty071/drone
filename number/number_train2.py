import cv2
import numpy as np
import os
from flask import Flask, render_template, make_response
import matplotlib.pyplot as plt
import math

# import pytesseract
# from PIL import Image
####빨간색 객체를 숫자로 지정####
# 숫자를 하나만 검출할 필요는 없지?
# pytesseract.pytesseract.tesseract_cmd=R'C:\Program Files\Tesseract-OCR\tesseract.exe'

### 1. 캠을 통한 영상 송출 및 캡쳐 except web streaming
cap = cv2.VideoCapture(0)

n = 0

# 딜레이 타임
del_time = 1000

# 찾을 숫자
num = 0

# 현재 폴더 위치를 얻는 함수
now_dir = os.path.dirname(os.path.abspath(__file__))

# 붉은 부분만 검출하기 위한 초기값들
hsv = 0
color_range = 8  # 빨간색으로 인식할 범위
threshold_S = 30  # 채도 하한값
threshold_V = 30  # 명도 하한값

lower_red1 = np.array([hsv - color_range + 180, threshold_S, threshold_V])
upper_red1 = np.array([180, 255, 255])
lower_red2 = np.array([0, threshold_S, threshold_V])
upper_red2 = np.array([hsv, 255, 255])
lower_red3 = np.array([hsv, threshold_S, threshold_V])
upper_red3 = np.array([hsv + color_range, 255, 255])


# functions
def load_train_data(file_name):
    with np.load(file_name) as data:
        train = data['train']
        train_labels = data['train_labels']
    return train, train_labels


def resize120(image):
    global n
    gray_resize = cv2.resize(image, (50, 70))
    save_file = '/number/up_image/%dnumber.jpg' % n
    while True:
        if os.path.exists(now_dir + save_file):
            n += 1
            save_file = '/number/up_image/%dnumber.jpg' % n
        else:
            break
    cv2.imwrite(now_dir + save_file, gray_resize)
    # 최종적으로는 (1 x 3500) 크기로 반환합니다.
    return gray_resize.reshape(-1, 3500).astype(np.float32)


def check(test, train, train_labels):
    knn = cv2.ml.KNearest_create()
    knn.train(train, cv2.ml.ROW_SAMPLE, train_labels)
    # 가장 가까운 5개의 글자를 찾아, 어떤 숫자에 해당하는지 찾는다.
    ret, result, neighbours, dist = knn.findNearest(test, k=5)
    return result

def show_learning_img(learning_num):
    saved_add = now_dir + '/number/num_img/%d.jpg' % learning_num
    num_img = cv2.imread(saved_add, cv2.IMREAD_COLOR)
    x = num_img.shape[1]
    y = num_img.shape[0]
    dx = int(x / 5)
    w = int(x / 4)
    h = int(y / 4)
    i = times // 5
    j = times % 5
    nx = dx * j
    ny = h * i
    img_piece = num_img[ny:(ny + h), nx:(nx + w)]
    cv2.imshow('learning_img', img_piece)
    cv2.waitKey(1)

times = 0
print(now_dir)
while True:
    show_learning_img(num)
    ret, frame = cap.read()
    if not ret:
        print("can't open camera")
        break

    height, width, channel = frame.shape

    # 원본 영상을 HSV 영상으로 변환
    img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # 범위 값으로 HSV 이미지에서 마스크를 생성합니다.
    img_mask1 = cv2.inRange(img_hsv, lower_red1, upper_red1)
    img_mask2 = cv2.inRange(img_hsv, lower_red2, upper_red2)
    img_mask3 = cv2.inRange(img_hsv, lower_red3, upper_red3)
    img_mask = img_mask1 | img_mask2 | img_mask3

    # 마스크 이미지로 원본 이미지에서 범위값에 해당되는 영상 부분을 획득합니다.
    img_result = cv2.bitwise_and(frame, frame, mask=img_mask)
    img_result = cv2.bitwise_not(img_result)  # 색반전
    img_gray = cv2.cvtColor(img_result, cv2.COLOR_BGR2GRAY)

    # 블러 처리를 통한 노이즈 제거
    img_blurred = cv2.GaussianBlur(img_gray, ksize=(15, 15), sigmaX=0)
    # e Thresholding
    ret, thresh = cv2.threshold(img_blurred, 200, 255, cv2.THRESH_BINARY_INV)
    # thresh = cv2.adaptiveThreshold(img_blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 19, 9)

    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    # temp_result = np.zeros((height, width, channel), dtype=np.uint8)

    contours_dict = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # frame= cv2.rectangle(frame, (x, y), (x+w, y+h), (0,0,255), 3)
        contours_dict.append({'contour': contour, 'x': x, 'y': y, 'w': w, 'h': h, 'cx': x + (w / 2), 'cy': y + (h / 2)})

    Min_area = 300
    Min_width, Min_height = 10, 40
    min_ratio, max_ratio = 0.1, 1

    # 여기서 걸러진 것을 모두 '숫자' 라 가정
    possible_contours = []
    cnt = 0
    for d in contours_dict:
        area = d['w'] * d['h']
        ratio = d['w'] / d['h']

        if area > Min_area and d['w'] > Min_width and d['h'] > Min_height and min_ratio < ratio < max_ratio:
            d['idx'] = cnt
            cnt += 1
            possible_contours.append(d)

    for contour in possible_contours:
        x, y, w, h = cv2.boundingRect(contour['contour'])
        frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
    # 송출 영상은 이에 해당함
    cv2.waitKey(del_time)
    '''
    cv2.imshow('masked', img_result)
    cv2.imshow('blurr', img_blurred)qqq
    cv2.imshow('thresh', thresh)
    '''
    cv2.imshow('img', frame)


    key_input = cv2.waitKey(100) # waitKey 함수로 프레임 조절 가능, 영상 송출 및 연산속도 느릴 시 숫자 키울것
    if key_input == ord('q'):
        break
    else:
        try:
            result = []
            for contour in possible_contours:
                # 이미지 크롭
                num_img = thresh[contour['y']:contour['y'] + contour['h'], contour['x']:contour['x'] + contour['w']]
                clearance_x = int(contour['h'] * 0.3)
                clearance_y = int(contour['h'] * 0.3)

                # 이미지에 여백을 준다
                num_img = cv2.copyMakeBorder(num_img, top=clearance_y, bottom=clearance_y, left=clearance_x,
                                             right=clearance_x, borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0))

                # Adaptive Thresholding // 한번 더 이 작업을 수행하여 숫자의 형태를 분명하게 해준다.
                num_img_blurred = cv2.GaussianBlur(num_img, ksize=(5, 5), sigmaX=0)  # 노이즈 블러
                ret, num_thresh = cv2.threshold(num_img_blurred, 127, 255, cv2.THRESH_BINARY)
                # num_thresh = cv2.adaptiveThreshold(num_img_blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 19, 9)

                cv2.imwrite(now_dir + '/number.jpg', num_thresh)
                # plt.imshow(cv2.cvtColor(num_img, cv2.COLOR_BGR2RGB))
                # plt.show()

                # KNN 머신러닝데이터로 대조하여 결과 출력
                FILE_NAME = now_dir + '/number/up_trained.npz'
                train, train_labels = load_train_data(FILE_NAME)

                # KNN
                test = resize120(num_thresh)
                result.append(int(check(test, train, train_labels)))
                '''
                #tesseract
                image = Image.open(now_dir+'/number.jpg')
                dd = pytesseract.image_to_string(image, lang=None)
                print(dd)
                '''
                print(result)
            times += 1
            continue
        except:
            times += 1
            continue
    '''
    #사각형 중심이 이미지의 중앙에 가장 가까운 것을 '숫자' 로 인식한다.
    diff = 1000
    for d in possible_contours:
        d_diff = math.sqrt((d['cx']-width/2)**2+(d['cy']-height/2)**2)
        if d_diff < diff:
            diff = d_diff
            n_contour = d


    try:   
        clearance_x = int(n_contour['h']*0.3)
        clearance_y = int(n_contour['h']*0.3)

        frame = cv2.rectangle(frame, (n_contour['x'], n_contour['y']), (n_contour['x']+n_contour['w'], n_contour['y']+n_contour['h']), (255, 0, 0), 3)

    except:
    '''


cap.release()
cv2.destroyAllWindows()
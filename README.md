# ARgym_project
IDE选择VsCode，python版本选择3.12
python库的要求
import cv2
import numpy as np
import time
import pose_module as pm
from PIL import ImageFont, ImageDraw, Image  
import pyttsx3
import math
import mediapipe as mp
import autopy as ap
上述引用分别对应opencv、numpy、time、与主运行文件在一个文件夹下的pose_module文件以及pillow和pyttsx3，math和mediapipe库。
安装语句
pip install opencv-python
pip install numpy
pip install time
pip install pillow
pip install pyttsx3
pip install math(一般会自带不需要安装)
pip install mediapipe(python3.10版本以上使用pip安装)
pip install pyinstaller(将main程序打包成exe文件)
本程序未使用到C相关的程序，因此included_files中无venv.py文件。
Lib中的文件在运行虚拟环境时需要手动导入。
lib 文件夹中包含所有通过 pip install 安装的依赖库。

Project with .venv, requirements.txt, and src/main.py.

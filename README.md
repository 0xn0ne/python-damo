# python-damo

**注意**：提倡正版 100 块钱 1400 天即为 3.8 年，平均每天 0.07 分钱，不调用还不收费

Python 版本大漠插件调用 API，需自备大漠插件，功能还比较少仅加了识图，鼠标点击功能，以后用到再说

## 快速开始

### 依赖

- 大漠插件：<https://www.52hsxx.com/>
- Python 32位 >= 3.9

进入项目目录，使用以下命令安装依赖库

```bash
pip3 install pillow pywin32
```

或者使用 PIP 的 requirement 参数安装依赖库

```bash
pip3 install -r requirements.txt
```

### 基础用法

函数前面带 x 的为魔改函数，主要调整默认值，执行逻辑

```python
from engine import DMEngine

# 可选步骤，申请管理员权限运行
DMEngine.run_as_admin()
# 初始化引擎，或者不使用 reg_code 和 ver_info 参数，在脚本目录下任意位置放 reg_code.txt 文件分行贴入注册码和附加码，脚本会自动识别
engine = DMEngine.load_dm(
    reg_code='<注册码，不带尖括号>',
    ver_info='<附加码，不带尖括号>',
)
# 如果不想使用引擎，可以使用单独的 DM 对象
image = DMImage.load_dm(
    reg_code='<注册码，不带尖括号>',
    ver_info='<附加码，不带尖括号>',
    'image_name',
)

# 创建 DMImage 对象，image_name 为图片路径，可以是单个，也可以是多个
image = engine.gen_image('image_name')
# 搜索图片，默认全屏搜索，返回 DMCoord 对象
image.xfind()
#<__main__.DMCoord object at 0x0370BC00, x=25, y=125>
# 搜索图片，在 100, 100 到 400, 400 的区域内搜索，与 image_name 图片相似度 0.7 的坐标
image.xfind(100, 100, 400, 400, sim=0.7)
# 和xfind一样但是返回内容不同，默认全屏搜索，返回多个图片搜索结果
image.xfind_mul()
#[(0, <__main__.DMCoord object at 0x0371BBE8>), (1, <__main__.DMCoord object at 0x0371BED0>)]
# 搜索并等待 8.5 秒图片出现
image.xwait(delay=8.5)
#<__main__.DMCoord object at 0x0370BC00, x=25, y=125>
# 和xwait一样但是返回内容不同，默认全屏搜索，返回多个图片搜索结果
image.xwait_mul(delay=8.5)

# 创建 DMCoord 对象，参数分别为 x 轴 200，y 轴 100
coord = engine.gen_coord(200, 100)
# 左键点击 1 下
coord.xclick()
# 右键点击 1 下
coord.xclick(butn='R')

# 组合使用，搜索图片，并左键点击，休眠 3 秒，中键点击
image.xfind().xclick().sleep(3).xclick(butn='M')
```

## Q&A

- Q：还缺少哪些默认函数？
- A：很多，可以自查源代码，使用 VSCODE 的大纲视图可以快速浏览现在有什么函数

- Q：大漠插件的目录怎么配置？
- A：参考 load_dm() 的函数说明，配置 path_plugin 参数即可，默认搜索脚本所在的当前目录

- Q：需要先注册大漠插件吗？
- A：可以注册可以不注册，不注册需要使用 DmReg.dll 文件，只要 dll 文件在脚本目录下，脚本会自动搜索

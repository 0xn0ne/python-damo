#!/bin/python3
# _*_ coding:utf-8 _*_
#
# dm.py
# 依赖大漠插件的 DmReg.dll，dm.dll 文件，大漠插件 py 版
# 很多函数懒得写了

import ctypes
import pathlib
import random
import re
import sys
import time
from typing import Iterable, Self, Tuple, Union

from PIL import Image, ImageGrab, UnidentifiedImageError
from win32com.client import CDispatch, Dispatch


def get_files(filepath: Union[str, pathlib.Path], pattern: str):
    if not isinstance(filepath, pathlib.Path):
        filepath = pathlib.Path(filepath)
    files = [i for i in filepath.glob(pattern)]
    if not files:
        raise RuntimeError('未找到 {}'.format(pattern))
    return files


def get_file(filepath, pattern, index=0):
    ret = get_files(filepath, pattern)
    if ret:
        return ret[index]
    return None


def image_convert_to_24bit(image_path: Union[pathlib.Path, str]):
    if isinstance(image_path, str):
        image_path = pathlib.Path(image_path)
    image_24bit = None
    try:
        image_24bit = Image.open(image_path.absolute().__str__()).convert('RGB')
    except PermissionError:
        # PermissionError: [Errno 13] Permission denied...
        return
    except UnidentifiedImageError:
        # PIL.UnidentifiedImageError: cannot identify image file...
        return
    image_path = image_path.with_stem(image_path.stem + '_24bit')
    image_24bit.save(image_path.absolute().__str__())
    return image_path


def images_convert_to_24bit(images_path: Iterable[Union[pathlib.Path, str]]) -> Image:
    images_path = [pathlib.Path(i) for i in images_path if isinstance(i, str)]
    ret = []
    for image_path in images_path:
        if image_path.is_file():
            ret.append(image_convert_to_24bit(image_path))
            continue
        for filepath in image_path.glob('**/*'):
            ret.append(image_convert_to_24bit(filepath))


class DMBase:

    def __init__(
        self,
        cls_or_dpt: Union[CDispatch, Self],
    ):
        self._raw = getattr(cls_or_dpt, '_raw', None)
        if not self._raw:
            self._raw = cls_or_dpt
        if not self._raw:
            raise RuntimeError('未找到插件或插件注册失败')

    def reg(self, reg_code: str, ver_info: str):
        if not ctypes.windll.shell32.IsUserAnAdmin():
            raise RuntimeError('请以管理员权限运行')
        code = self._raw.Reg(reg_code, ver_info)
        message = {
            -1: '无法连接网络',
            -2: '进程没有以管理员方式运行',
            0: '注册失败，未知错误',
            1: '成功',
            2: '余额不足',
            3: '绑定了本机器，但是账户余额不足50元',
            4: '注册码错误',
            5: '你的机器或者IP在黑名单列表中或者不在白名单列表中',
            6: '非法使用插件',
            7: '你的帐号因为非法使用被封禁',
            8: 'ver_info不在你设置的附加白名单中，或者余额不足被系统拉黑',
            77: '机器码或者IP因为非法使用而被封禁',
            -8: '超过版本附加信息长度，请检查大漠版本，尽量用7.xx以后的版本',
            -9: '版本附加信息里包含了非法字母',
        }
        if code != 1:
            raise RuntimeError('注册失败，错误代码：{}，信息：{}'.format(code, message[code]))
        return code

    def ver(self):
        return self._raw.Ver()

    @classmethod
    def load_dm(
        cls,
        reg_code: str = None,
        ver_info: str = None,
        path_plugin: Union[str, pathlib.Path] = '.',
        path_dmraw='**/dm.dll',
        path_dmreg='**/DmReg.dll',
        *args,
        **kwargs,
    ) -> Self:
        if not isinstance(path_plugin, pathlib.Path):
            path_plugin = pathlib.Path(path_plugin)
        path_dmraw = get_file(path_plugin, path_dmraw)
        path_dmreg = get_file(path_plugin, path_dmreg)
        try:
            obj = Dispatch('dm.dmsoft')
            instance = cls(obj, *args, **kwargs)
        except:
            # 先将大漠插件目录下面的 “DmReg.dll” 注册
            # 注册方法参考大漠插件目录下的“不注册调用dm.dll的方法 v15.0/说明.txt”
            regobj = ctypes.windll.LoadLibrary(path_dmreg.absolute().__str__())
            # 这个地方不知道为什么有时会抽风，把 SetDllPathW 改为 SetDllPathA 然后再试着改回 SetDllPathW 可以调用成功
            regobj.SetDllPathW(path_dmraw.absolute().__str__(), 0)
            obj = Dispatch('dm.dmsoft')
            instance = cls(obj, *args, **kwargs)
        if reg_code is None or ver_info is None:
            # 尝试寻找 reg_code 文件并读取
            for file_code_path in path_plugin.glob('**/reg_code.txt'):
                if not file_code_path.is_file():
                    continue
                contents = [i for i in re.split(r'[\s\|]+', file_code_path.read_text()) if i]
                if len(contents) < 2:
                    continue
                reg_code, ver_info = contents[0], contents[1]
            if not reg_code and not ver_info:
                # 找图找色都需要注册，不注册会导致后续大量函数调用异常
                return instance
        instance.reg(reg_code, ver_info)
        return instance

    @staticmethod
    def run_as_admin(path_py: Union[str, pathlib.Path] = sys.executable) -> bool:
        """切换管理员权限运行当前脚本

        Args:
            path_py (Union[str, pathlib.Path], optional): Python 解释器路径，必须是 32 位的解释器，默认：sys.executable
        """
        if isinstance(path_py, str):
            path_py = pathlib.Path(path_py)
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
        # 当前窗口非管理员权限的情况下会启动新的CMD窗口，并以管理员权限运行，当前命令行窗口会被关闭
        ctypes.windll.shell32.ShellExecuteW(
            None, 'runas', sys.executable, '{} {}'.format(__file__, ' '.join(sys.argv)), None, 1
        )
        sys.exit(0)

    def sleep(self, mins: int = 1, maxs: int = None):
        """休眠函数方便模拟延迟，当 maxs 参数为 None 时会使用 mins 的值休眠固定时间，当 maxs 参数不为 None 时会使用 mins 到  maxs 之间的值休眠随机时间

        Args:
            mins (int): 最小休眠时间，单位：秒，默认：1
            maxs (int): 最大休眠时间，单位：秒，默认：None

        Returns:
            Self: 当前类
        """
        seconds = mins
        if maxs is not None:
            seconds = mins + (maxs - mins) * random.random()
        time.sleep(seconds)
        return self


class DMCoord(DMBase):
    # Keyboard And Mouse
    def __init__(self, dm: CDispatch = None, *, x: int = 0, y: int = 0):
        super().__init__(dm)
        self.x = x
        self.y = y

    def move_to(self, x_offset: int = 0, y_offset: int = 0):
        """把鼠标移动到目的点 xy 轴坐标

        Args:
            x_offset (int): X偏移坐标
            y_offset (int): Y偏移坐标

        Returns:
            int: 返回 0 失败，返回 1 成功
        """
        return self._raw.MoveTo(self.x + x_offset, self.y + y_offset)

    def xclick(self, x_offset: int = 0, y_offset: int = 0, butn: str = 'L', mode: str = 'C'):
        """鼠标点击操作

        Args:
            x_offset (int, optional): 在 x 轴的点击偏移距离，默认：0
            y_offset (int, optional): 在 y 轴的点击偏移距离，默认：0
            butn (str, optional): 使用指定按键点击，L 为左键，R 为右键，M 为中键，D 为双击，默认：'L'.
            mode (str, optional): 鼠标点击模式，C 为常规模式，D 为按下按键，U 为放开按键，默认：'C'.

        Raises:
            RuntimeError: 点击失败的情况会抛出异常，但目前没发现点击失败，等后续发现补充

        Returns:
            DMCoord: 返回当前 DMCoord 对象
        """
        butn_map = {
            'L': '_left',
            'R': '_right',
            'M': '_middle',
            'D': '_double',
            'LEFT': '_left',
            'RIGHT': '_right',
            'MIDDLE': '_middle',
            'DOUBLE': '_double',
        }
        mode_map = {
            'C': '',
            'D': '_down',
            'U': '_up',
            'CLICK': '',
            'DOWN': '_down',
            'UP': '_up',
        }
        self.move_to(x_offset, y_offset)
        if butn.upper() in butn_map:
            butn = butn_map[butn.upper()]
        if mode.upper() in mode_map:
            mode = mode_map[mode.upper()]
        ret = getattr(self, 'click{}{}'.format(butn, mode))()
        if not ret:
            raise RuntimeError('点击失败，返回：{}'.format(ret))
        return self

    def click_left(self):
        return self._raw.LeftClick()

    def click_double(self):
        return self._raw.DoubleClick()

    def click_left_down(self):
        return self._raw.LeftDown()

    def click_left_up(self):
        return self._raw.LeftUp()

    def click_middle(self):
        return self._raw.MiddleClick()

    def click_middle_down(self):
        return self._raw.MiddleDown()

    def click_middle_up(self):
        return self._raw.MiddleUp()

    def click_right(self):
        return self._raw.RightClick()

    def click_right_down(self):
        return self._raw.RightDown()

    def click_right_up(self):
        return self._raw.RightUp()

    def __str__(self) -> str:
        return '{}, x={}, y={}>'.format(super().__str__()[:-1], self.x, self.y)


class DMImage(DMBase):
    def __init__(self, dm: Union[CDispatch, Self], *, images: str):
        super().__init__(dm)
        self.images = images
        self.scr_size = ImageGrab.grab().size

    def get_size(self):
        return Image.open(self.images).size

    def load(self) -> int:
        """预先加载指定的图片，可以在操作任何和图片相关的函数时将省去了加载图片的时间。调用此函数后没必要调用FreePic，插件自己会自动释放

        此函数不是必须调用的，所有和图形相关的函数只要调用过一次，图片会自动加入缓存。如果想对一个已经加入缓存的图片进行修改，那么必须先用FreePic释放此图片在缓存中占用的内存，然后重新调用图片相关接口，就可以重新加载此图片

        支持多文件“1.bmp|2.bmp|3.bmp”、通配符“*.bmp”的方式加载

        Returns:
            int: 返回 0 失败，返回 1 成功
        """
        return self._raw.LoadPic(self.images)

    def free(self):
        """释放指定的图片，一般此函数不必要调用，除非需要节省内存

        支持多文件“1.bmp|2.bmp|3.bmp”、通配符“*.bmp”的方式加载

        Returns:
            int: 返回 0 失败，返回 1 成功
        """
        return self._raw.FreePic(self.images)

    def find_ex(
        self,
        xl: int = 0,
        yl: int = 0,
        xr: int = None,
        yr: int = None,
        delta_color: str = '000000',
        sim: float = 0.9,
        dir: int = 0,
    ) -> str:
        if xr is None:
            xr = self.scr_size[0]
        if yr is None:
            yr = self.scr_size[1]
        return self._raw.FindPicEx(xl, yl, xr, yr, self.images, delta_color, sim, dir)

    def find(
        self,
        xl: int = 0,
        yl: int = 0,
        xr: int = None,
        yr: int = None,
        delta_color: str = '000000',
        sim: float = 0.9,
        dir: int = 0,
    ) -> Tuple[int, int, int]:
        if xr is None:
            xr = self.scr_size[0]
        if yr is None:
            yr = self.scr_size[1]
        return self._raw.FindPic(xl, yl, xr, yr, self.images, delta_color, sim, dir)

    def xfind_mul(
        self,
        xl: int = 0,
        yl: int = 0,
        xr: int = None,
        yr: int = None,
        delta_color: str = '000000',
        sim: float = 0.9,
        dir: int = 0,
    ) -> Iterable[Tuple[int, DMCoord]]:
        ret = []
        result = self.find_ex(xl, yl, xr, yr, delta_color, sim, dir)
        if not result:
            return ret
        for item in result.split('|'):
            item = item.split(',')
            ret.append((int(item[0]), DMCoord(self, x=int(item[1]), y=int(item[2]))))
        return ret

    def xwait_mul(
        self,
        xl: int = 0,
        yl: int = 0,
        xr: int = None,
        yr: int = None,
        seconds: float = 3,
        delta_color: str = '000000',
        sim: float = 0.9,
        dir: int = 0,
    ) -> Iterable[Tuple[int, DMCoord]]:
        ret = []
        stime = time.time()
        while time.time() - stime < seconds:
            ret = self.xfind_mul(xl, yl, xr, yr, delta_color, sim, dir)
            if ret:
                return ret
            time.sleep(0.1)
        return ret

    def xfind(
        self,
        xl: int = 0,
        yl: int = 0,
        xr: int = None,
        yr: int = None,
        delta_color: str = '000000',
        sim: float = 0.9,
        dir: int = 0,
    ) -> DMCoord:
        ret = self.xfind_mul(xl, yl, xr, yr, delta_color, sim, dir)
        if not ret:
            raise RuntimeError('未找到图片 {} 坐标'.format(self.images))

        return ret[0][1]

    def xwait(
        self,
        xl: int = 0,
        yl: int = 0,
        xr: int = None,
        yr: int = None,
        seconds: float = 3,
        delta_color: str = '000000',
        sim: float = 0.9,
        dir: int = 0,
    ) -> DMCoord:
        ret = self.xwait_mul(xl, yl, xr, yr, seconds, delta_color, sim, dir)
        if not ret:
            raise RuntimeError('未找到图片 {} 坐标'.format(self.images))
        return ret[0][1]


class DMClient(DMBase):
    def __init__(self, dm: Union[CDispatch, Self], *, hwnd: int):
        super().__init__(dm)
        self.hwnd = hwnd

    def get_rect(self, hwnd: int):
        """获取指定窗口在屏幕上的位置

        Args:
            hwnd (int): 指定的窗口句柄

        Returns:
            Tuple[int, int, int, int, int]: 第1个返回值是否成功，第2个返回值左上角x坐标，第3个返回值左上角y坐标，第4个返回值宽度，第5个返回值高度
        """
        return self._raw.GetClientRect(hwnd)

    def get_size(self, hwnd: int) -> Tuple[int, int, int]:
        """获取指定窗口的宽度和高度

        Args:
            hwnd (int): 指定的窗口句柄

        Returns:
            Tuple[int, int, int]: 第1个返回值是否成功，第2个返回值宽度，第3个返回值高度
        """
        ret = self._raw.GetClientSize(hwnd)
        return ret

    def to_screen(self) -> Tuple[int, int, int]:
        """把窗口坐标转换为屏幕坐标

        Args:
            hwnd (int): 指定的窗口句柄

        Returns:
            Tuple[int, int, int]: 未知，调用报错“仅支持VT_I2和VT_I4类型!,当前类型:1”未试出来，当前注解的类型是猜的
        """
        return self._raw.ClientToScreen(self.hwnd)


class DMWindow(DMBase):
    def set_display_input(self, mode: str = 'screen') -> Union[int]:
        return self._raw.SetDisplayInput(mode)

    def bind(
        self, hwnd: int, display: str = 'normal', mouse: str = 'normal', keypad: str = 'normal', mode: int = 0
    ) -> int:
        """获取当前对象已经绑定的窗口句柄. 无绑定返回0

        Returns:
            int: 窗口句柄
        """
        return self._raw.BindWindow(hwnd, display, mouse, keypad, mode)

    def get_bind(self) -> int:
        """获取当前对象已经绑定的窗口句柄. 无绑定返回0

        Returns:
            int: 窗口句柄
        """
        return self._raw.GetBindWindow()

    def enum_process(self, name: str) -> str:
        """根据指定进程名，枚举系统中符合条件的进程PID，并且按照进程打开顺序排序

        Args:
            name (str): 进程名，比如qq.exe

        Returns:
            str: 返回所有匹配的进程PID，并按打开顺序排序，格式“pid1,pid2,pid3”
        """
        return self._raw.EnumProcess(name)

    def enum(self, parent: int, title: str, _class: str, filter: int = 1) -> str:
        """根据指定条件，枚举系统中符合条件的窗口，可以枚举到按键自带的无法枚举到的窗口

        Args:
            parent (int): 获得的窗口句柄是该窗口的子窗口的窗口句柄，取0时为获得桌面句柄
            title (str): 窗口标题。此参数是模糊匹配
            _class (str): 窗口类名。此参数是模糊匹配
            filter (int, optional): 取值定义，1：匹配窗口标题，参数title有效；2：匹配窗口类名，参数_class有效；4：只匹配指定父窗口的第一层孩子窗口；8：匹配父窗口为0的窗口，即顶级窗口；16：匹配可见的窗口；32：匹配出的窗口按照窗口打开顺序依次排列。这些值可以相加，如4+8+16就是类似于任务管理器中的窗口列表。默认：1

        Returns:
            str: 返回所有匹配的窗口句柄字符串，格式“hwnd1,hwnd2,hwnd3”
        """
        return self._raw.EnumWindow(parent, title, _class, filter)

    def enum_by_process(self, pname: str, title: str, _class: str, filter: int = 1) -> str:
        """根据指定进程以及其它条件，枚举系统中符合条件的窗口，可以枚举到按键自带的无法枚举到的窗口

        Args:
            pname (str): 进程映像名。比如svchost.exe。此参数是精确匹配，但不区分大小写
            title (str): 窗口标题。此参数是模糊匹配
            _class (str): 窗口类名。此参数是模糊匹配
            filter (int, optional): 取值定义，1：匹配窗口标题，参数title有效；2：匹配窗口类名，参数_class有效；4：只匹配指定父窗口的第一层孩子窗口；8：匹配父窗口为0的窗口，即顶级窗口；16：匹配可见的窗口；32：匹配出的窗口按照窗口打开顺序依次排列。这些值可以相加，如4+8+16就是类似于任务管理器中的窗口列表。默认：1

        Returns:
            str: 返回所有匹配的窗口句柄字符串，格式“hwnd1,hwnd2,hwnd3”
        """
        return self._raw.EnumWindowByProcess(pname, title, _class, filter)

    def enum_by_process_id(self, pid: int, title: str, _class: str, filter: int = 1) -> str:
        """根据指定进程PID以及其它条件，枚举系统中符合条件的窗口，可以枚举到按键自带的无法枚举到的窗口

        Args:
            pid (int): 进程PID
            title (str): 窗口标题。此参数是模糊匹配
            _class (str): 窗口类名。此参数是模糊匹配
            filter (int, optional): 取值定义，1：匹配窗口标题，参数title有效；2：匹配窗口类名，参数_class有效；4：只匹配指定父窗口的第一层孩子窗口；8：匹配父窗口为0的窗口，即顶级窗口；16：匹配可见的窗口。这些值可以相加，如4+8+16就是类似于任务管理器中的窗口列表。默认：1

        Returns:
            str: 返回所有匹配的窗口句柄字符串，格式“hwnd1,hwnd2,hwnd3”
        """
        return self._raw.EnumWindowByProcessId(pid, title, _class, filter)

    def enum_by_process_id(
        self, spec1: str, spec2: str, flag1: int = 0, flag2: int = 0, type1: int = 0, type2: int = 0
    ) -> int:
        """根据两组设定条件来查找指定窗口

        Args:
            spec1 (str): 查找串1，内容取决于flag1的值
            spec2 (str): 参考spec1
            flag1 (int): spec1内容类型的定义，0是标题；1是程序名字，如：notepad；2是类名；3是程序路径，不包含盘符；4是父句柄，十进制表达的串；5是父窗口标题；6是父窗口类名；7是顶级窗口句柄，十进制表达的串；8是顶级窗口标题；9是顶级窗口类名，默认：0
            flag2 (int): 参考flag1，默认：0
            type1 (int): 值为 0 精确判断，值为 1 模糊判断，默认：0
            type2 (int): 参考type1，默认：0

        Returns:
            str: 整形数表示的窗口句柄，没找到返回 0
        """
        return self._raw.EnumWindowSuper(spec1, flag1, type1, spec2, flag2, type2)

    def find(self, _class: str = '', title: str = '') -> int:
        """查找符合类名或者标题名的顶层可见窗口

        Args:
            _class (str, optional): 窗口类名，如果为空则匹配所有。这里的匹配是模糊匹配。默认：''.
            title (str, optional): 窗口标题，如果为空则匹配所有。这里的匹配是模糊匹配。默认：''.

        Returns:
            int: 整形数表示的窗口句柄，没找到返回 0
        """
        return self._raw.FindWindow(_class, title)

    def find_by_process(self, pname: str, _class: str = '', title: str = '') -> int:
        """根据指定的进程名字，来查找可见窗口

        Args:
            pname (str): 进程映像名。比如svchost.exe。此参数是精确匹配，但不区分大小写
            _class (str, optional): 窗口类名，如果为空则匹配所有。这里的匹配是模糊匹配。默认：''.
            title (str, optional): 窗口标题，如果为空则匹配所有。这里的匹配是模糊匹配。默认：''.

        Returns:
            int: 整形数表示的窗口句柄，没找到返回 0
        """
        return self._raw.FindWindowByProcess(pname, _class, title)

    def find_by_process(self, pid: int, _class: str = '', title: str = '') -> int:
        """根据指定的进程ID，来查找可见窗口

        Args:
            pid (int): 进程PID
            _class (str, optional): 窗口类名，如果为空则匹配所有。这里的匹配是模糊匹配。默认：''.
            title (str, optional): 窗口标题，如果为空则匹配所有。这里的匹配是模糊匹配。默认：''.

        Returns:
            int: 整形数表示的窗口句柄，没找到返回 0
        """
        return self._raw.FindWindowByProcessId(pid, _class, title)

    def find_ex(self, parent_hwnd: int = 0, _class: str = '', title: str = '') -> int:
        """查找符合类名或者标题名的顶层可见窗口，如果指定了parent，则在parent的第一层子窗口中查找

        Args:
            parent_hwnd (int): 父窗口句柄，如果为空，则匹配所有顶层窗口
            _class (str, optional): 窗口类名，如果为空则匹配所有。这里的匹配是模糊匹配。默认：''.
            title (str, optional): 窗口标题，如果为空则匹配所有。这里的匹配是模糊匹配。默认：''.

        Returns:
            int: 整形数表示的窗口句柄，没找到返回 0
        """
        return self._raw.FindWindowEx(parent_hwnd, _class, title)

    def find_super(self, spec1: str, spec2: str, flag1: int = 0, flag2: int = 0, type1: int = 0, type2: int = 0) -> int:
        """根据两组设定条件来查找指定窗口

        Args:
            spec1 (str): 查找串1，内容取决于flag1的值
            spec2 (str): 参考spec1
            flag1 (int): spec1内容类型的定义，0是标题；1是程序名字，如：notepad；2是类名；3是程序路径，不包含盘符；4是父句柄，十进制表达的串；5是父窗口标题；6是父窗口类名；7是顶级窗口句柄，十进制表达的串；8是顶级窗口标题；9是顶级窗口类名，默认：0
            flag2 (int): 参考flag1，默认：0
            type1 (int): 值为 0 精确判断，值为 1 模糊判断，默认：0
            type2 (int): 参考type1，默认：0

        Returns:
            int: 整形数表示的窗口句柄，没找到返回 0
        """
        return self._raw.FindWindowSuper(spec1, flag1, type1, spec2, flag2, type2)

    def get_foreground_focus(self) -> int:
        """获取顶层活动窗口中具有输入焦点的窗口句柄

        Returns:
            int: 返回整型表示的窗口句柄
        """
        return self._raw.GetForegroundFocus()

    def get_foreground(self) -> int:
        """获取顶层活动窗口，可以获取到按键自带插件无法获取到的句柄

        Returns:
            int: 返回整型表示的窗口句柄
        """
        return self._raw.GetForegroundWindow()

    def get_mouse_point(self) -> int:
        """获取鼠标指向的可见窗口句柄，可以获取到按键自带的插件无法获取到的句柄

        Returns:
            int: 返回整型表示的窗口句柄
        """
        return self._raw.GetMousePointWindow()

    def get_point(self, x: int = None, y: int = None) -> int:
        """获取给定坐标的可见窗口句柄，可以获取到按键自带的插件无法获取到的句柄

        Args:
            x (int): 屏幕x坐标
            y (int): 屏幕y坐标

        Returns:
            int: 窗口句柄
        """
        return self._raw.GetPointWindow(x, y)

    def get_process_info(self, pid: int) -> str:
        """获取给定坐标的可见窗口句柄，可以获取到按键自带的插件无法获取到的句柄

        Args:
            pid (int): 进程PID

        Returns:
            str: 格式“进程名|进程路径|cpu|内存”
        """
        return self._raw.GetProcessInfo(pid)

    def get_special(self, flag: int = 0) -> int:
        """获取特殊窗口

        Args:
            flag (int): 为 0 获取桌面窗口，为 1 获取任务栏窗口

        Returns:
            int: 返回整型表示的窗口句柄
        """
        return self._raw.GetSpecialWindow(flag)

    def xget_point(self, coord: DMCoord = None, x: int = None, y: int = None) -> int:
        """获取给定坐标的可见窗口句柄，可以获取到按键自带的插件无法获取到的句柄

        Args:
            coord (DMCoord, optional): 如果传入则默认优先使用 DMCoord 的 x 和 y 坐标，默认：None
            x (int, optional): 屏幕 x 坐标，默认：None
            y (int, optional): 屏幕 y 坐标，默认：None

        Raises:
            RuntimeError: 未指定 x 和 y 坐标，也未传入 DMCoord 对象时会报错

        Returns:
            int: 窗口句柄
        """
        if coord:
            x = coord.x
            y = coord.y
        if x is None or y is None:
            raise RuntimeError('坐标未指定')
        return self._raw.GetPointWindow(x, y)

    def set_path(self, dir_path: Union[pathlib.Path, str]) -> int:
        if isinstance(dir_path, pathlib.Path):
            dir_path = dir_path.absolute().__str__()
        return self._raw.SetPath(dir_path)


class DMEngine(DMBase):
    def gen_image(self, images: str) -> DMImage:
        return DMImage(self, images=images)

    def gen_coord(self, x: int, y: int) -> DMCoord:
        return DMCoord(self, x=x, y=y)

    def gen_window(self) -> DMWindow:
        return DMWindow(self)

    def gen_client(self, hwnd: int) -> DMClient:
        return DMClient(self, hwnd=hwnd)


if __name__ == '__main__':
    pass
    print('[*] DM Loading...')
    DMEngine.run_as_admin()
    engine = DMEngine.load_dm()
    print('[+] DM Running...')
    # imgobj = engine.gen_image('switch.bmp|save.bmp')

    # print(imgobj.xfind_mul(sim=0.8))
    # crdobj = engine.gen_coord(200, 100)
    # crdobj.xclick()
    # crdobj.xclick(butn='R').sleep(3).xclick()

    # STEAM++ 自动点击成就
    while True:
        print('[*] waiting...')
        imgobj = engine.gen_image('switch.bmp')
        ret = imgobj.xwait(seconds=900, sim=0.7).xclick(30, 70)
        print('[+] found: {}'.format(ret))
        imgobj = engine.gen_image('save.bmp')
        imgobj.xwait(seconds=3, sim=0.7).xclick(12, 12)
        sleep_time = random.randint(1800, 6000)
        print('[*] sleep: {} s'.format(sleep_time))
        time.sleep(sleep_time)

    # dmw = engine.gen_window()
    # ret = dmw.find(title='任务管理器')
    # dmc = engine.gen_client(ret)
    # dmc.to_screen()

    # images_convert_to_24bit(['save_button.png', 'switch_button.png'])

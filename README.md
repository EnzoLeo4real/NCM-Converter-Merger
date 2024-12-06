# NCM-Converter-Merger

## 项目背景

这是一个基于 [anonymous5l/ncmdump](https://github.com/anonymous5l/ncmdump) 和[allenfrostline/pyNCMDUMP](https://github.com/allenfrostline/pyNCMDUMP)的二次开发项目。原项目实现了将网易云音乐的加密 `.ncm` 文件转换为普通音频格式（如 `flac` 和 `mp3`）的功能。

在此基础上，本项目添加了音频文件拼接功能，可以将转换后的多个音频文件合并为单个 `.flac` 文件。这个新功能主要是为了方便音乐电台博主制作 Playlist 歌单视频：当需要为完整歌单制作音频频谱动画时，使用合并后的单个音频文件会比处理多个单曲文件更加高效。B站Playlist歌单视频参考频道：https://www.bilibili.com/video/BV1iXzZYcE7a/?spm_id_from=333.1387.homepage.video_card.click&vd_source=7cb66437a25651c06c65f0140cd884bb。

## 主要功能

1. 将网易云音乐的 `.ncm` 格式文件转换为 `.flac` 或 `.mp3` 格式
2. 支持批量转换多个文件
3. 支持多进程并行处理以提高转换效率
4. 支持将转换后的音频文件按顺序拼接为单个 `.flac` 文件
5. 支持混合格式（`.flac` 和 `.mp3`）的音频文件拼接

## 依赖

- Python3
- 通过 requirements.txt 安装 Python 依赖:
  ```bash
  pip install -r requirements.txt
  ```
- [ffmpeg](https://ffmpeg.org/) - 如果需要使用合并功能,需要安装 ffmpeg:
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: 从 [ffmpeg官网](https://ffmpeg.org/download.html) 下载并配置环境变量

## 使用方法

使用此工具需要基本的 Python3 终端操作知识(以下示例中的长短参数可互换):

```
$ python3 ncmdump.py --help

usage: ncmdump.py [-h] [-w] [-m] [-o OUTPUT] paths [paths ...]

pyNCMDUMP命令行工具

positional arguments:
  paths                 一个或多个源文件路径

optional arguments:
  -h, --help           显示帮助信息并退出
  -w , --workers       并行转换时的工作进程数（默认：1）
  -m, --merge          合并所有转换后的.flac文件
  -o, --output OUTPUT  指定合并后的输出文件名（默认：merged.flac）
```

### 基本转换示例(单进程模式):

```
$ python ncmdump.py A b.ncm
  _   _  _____ __  __         _____                          _                   __  __                          
 | \ | |/ ____|  \/  |       / ____|                        | |                 |  \/  |                         
 |  \| | |    | \  / |______| |     ___  _ ____   _____ _ __| |_ ___ _ __ ______| \  / | ___ _ __ __ _  ___ _ __ 
 | . ` | |    | |\/| |______| |    / _ \| '_ \ \ / / _ \ '__| __/ _ \ '__|______| |\/| |/ _ \ '__/ _` |/ _ \ '__|
 | |\  | |____| |  | |      | |___| (_) | | | \ V /  __/ |  | ||  __/ |         | |  | |  __/ | | (_| |  __/ |   
 |_| \_|\_____|_|  |_|       \_____\___/|_| |_|\_/ \___|_|   \__\___|_|         |_|  |_|\___|_|  \__, |\___|_|   
                                                                                                  __/ |          
                                                                                                 |___/                                                     
                                          NCM-Converter-Merger                     
                        https://github.com/EnzoLeo4real/NCM-Converter-Merger.git  
使用单进程模式运行NCM-Converter-Merger
  // ... 转换过程输出 ...
所有操作已完成
```

### 并行转换示例(4个工作进程):

```
$ python ncmdump.py A b.ncm --workers 4

  // ... 程序头部输出 ...
使用4个并行进程运行NCM-Converter-Merger
  // ... 转换过程输出 ...
所有操作已完成
```

### 转换并合并文件示例:

```
$ python ncmdump.py A b.ncm -m -o combined.flac

  // ... 程序头部输出 ...
使用单进程模式运行NCM-Converter-Merger
  // ... 转换过程输出 ...
成功拼接文件到: "combined.flac"
所有操作已完成
```

### 并行转换并合并文件:

```
$ python ncmdump.py A b.ncm -w 4 -m -o combined.flac
$ 示例：python .\ncmdump.py D:\Is\your\path -w 5 -m -o D:\is\your\path\playlist001.flac
```

## 注意事项

1. 拼接功能支持 `.flac` 和 `.mp3` 格式的文件混合拼接
2. 使用拼接功能需要系统已安装 ffmpeg
3. 如果输出目录下已存在同名文件,程序会跳过该文件的转换
4. 在拼接时，所有音频文件会按照转换的顺序进行拼接
5. 为保证音质，mp3 文件会被临时转换为 flac 格式后再进行拼接
6. 建议在制作视频频谱时使用 `.flac` 格式，以保证最好的音质效果

## 致谢

- 感谢 [anonymous5l](https://github.com/anonymous5l) 编写的原始版本 [ncmdump](https://github.com/anonymous5l/ncmdump) (C++版本)
- 感谢 [allenfrostline](https://github.com/allenfrostline)编写的python版本[pyNCMDUMP](https://github.com/allenfrostline/pyNCMDUMP).(python版本)
- 感谢 [ffmpeg](https://ffmpeg.org/) 提供的强大音频处理功能

## 许可证

本项目遵循与原项目相同的开源协议。详见 [LICENSE](LICENSE.txt) 文件。

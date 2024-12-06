import os
import json
import base64
import struct
import logging
import binascii
from glob import glob
from tqdm.auto import tqdm
from textwrap import dedent
from Crypto.Cipher import AES
from multiprocessing import Pool
import subprocess
import shutil


class TqdmLoggingHandler(logging.StreamHandler):
    """Avoid tqdm progress bar interruption by logger's output to console"""
    # see logging.StreamHandler.eval method:
    # https://github.com/python/cpython/blob/d2e2534751fd675c4d5d3adc208bf4fc984da7bf/Lib/logging/__init__.py#L1082-L1091
    # and tqdm.write method:
    # https://github.com/tqdm/tqdm/blob/f86104a1f30c38e6f80bfd8fb16d5fcde1e7749f/tqdm/std.py#L614-L620

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg, end=self.terminator)
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
handler = TqdmLoggingHandler()
fmt = '%(levelname)7s [%(asctime)s] %(message)s'
datefmt = '%Y-%m-%d %H:%M:%S'
handler.setFormatter(logging.Formatter(fmt, datefmt))
log.addHandler(handler)


def dump_single_file(filepath):
    try:

        filename = filepath.split('/')[-1]
        if not filename.endswith('.ncm'): return
        filename = filename[:-4]
        for ftype in ['mp3', 'flac']:
            fname = f'{filename}.{ftype}'
            if os.path.isfile(fname):
                log.warning(f'Skipping "{filepath}" due to existing file "{fname}"')
                return

        log.info(f'Converting "{filepath}"')

        # hex to str
        core_key = binascii.a2b_hex('687A4852416D736F356B496E62617857')
        meta_key = binascii.a2b_hex('2331346C6A6B5F215C5D2630553C2728')
        unpad = lambda s: s[0:-(s[-1] if isinstance(s[-1], int) else ord(s[-1]))]
        with open(filepath, 'rb') as f:
            header = f.read(8)
            
            # str to hex
            assert binascii.b2a_hex(header) == b'4354454e4644414d'
            f.seek(2, 1)
            key_length = f.read(4)
            key_length = struct.unpack('<I', bytes(key_length))[0]
            key_data = f.read(key_length)
            key_data_array = bytearray(key_data)
            for i in range(0, len(key_data_array)):
                key_data_array[i] ^= 0x64
            key_data = bytes(key_data_array)
            cryptor = AES.new(core_key, AES.MODE_ECB)
            key_data = unpad(cryptor.decrypt(key_data))[17:]
            key_length = len(key_data)
            key_data = bytearray(key_data)
            key_box = bytearray(range(256))

            c = 0
            last_byte = 0
            key_offset = 0
            for i in range(256):
                swap = key_box[i]
                c = (swap + last_byte + key_data[key_offset]) & 0xff
                key_offset += 1
                if key_offset >= key_length:
                    key_offset = 0
                key_box[i] = key_box[c]
                key_box[c] = swap
                last_byte = c

            meta_length = f.read(4)
            meta_length = struct.unpack('<I', bytes(meta_length))[0]
            meta_data = f.read(meta_length)
            meta_data_array = bytearray(meta_data)
            for i in range(0, len(meta_data_array)):
                meta_data_array[i] ^= 0x63
            meta_data = bytes(meta_data_array)
            meta_data = base64.b64decode(meta_data[22:])
            cryptor = AES.new(meta_key, AES.MODE_ECB)
            meta_data = unpad(cryptor.decrypt(meta_data)).decode('utf-8')[6:]
            meta_data = json.loads(meta_data)

            crc32 = f.read(4)
            crc32 = struct.unpack('<I', bytes(crc32))[0]
            f.seek(5, 1)
            image_size = f.read(4)
            image_size = struct.unpack('<I', bytes(image_size))[0]
            image_data = f.read(image_size)
            target_filename = filename + '.' + meta_data['format']

            with open(target_filename, 'wb') as m:
                chunk = bytearray()
                while True:
                    chunk = bytearray(f.read(0x8000))
                    chunk_length = len(chunk)
                    if not chunk:
                        break
                    for i in range(1, chunk_length + 1):
                        j = i & 0xff
                        chunk[i - 1] ^= key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
                    m.write(chunk)
        log.info(f'Converted file saved at "{target_filename}"')
        return target_filename

    except KeyboardInterrupt:
        log.warning('Aborted')
        quit()


def list_filepaths(path):
    if os.path.isfile(path):
        return [path]
    elif os.path.isdir(path):
        return [fp for p in glob(f'{path}/*') for fp in list_filepaths(p)]
    else:
        raise ValueError(f'path not recognized: {path}')


def check_ffmpeg():
    """检查系统是否安装了ffmpeg"""
    if shutil.which('ffmpeg') is None:
        log.error("未找到ffmpeg。请先安装ffmpeg后再使用合并功能。")
        return False
    return True


def merge_audio_files(audio_files, output_file):
    """按顺序拼接音频文件（支持 mp3 和 flac 混合）"""
    if not audio_files:
        log.warning("没有找到可以拼接的音频文件")
        return False
        
    try:
        # 创建临时目录
        temp_dir = 'temp_audio_files'
        os.makedirs(temp_dir, exist_ok=True)
        
        # 将所有音频转换为临时 flac 文件
        temp_files = []
        inputs = []
        filter_parts = []
        
        for i, audio_file in enumerate(audio_files):
            # 获取文件格式
            file_ext = os.path.splitext(audio_file)[1].lower()
            
            if file_ext == '.mp3':
                # 如果是 mp3，先转换为 flac
                temp_flac = os.path.join(temp_dir, f'temp_{i}.flac')
                log.info(f'转换 {audio_file} 为 FLAC 格式...')
                subprocess.run([
                    'ffmpeg', '-i', audio_file,
                    '-c:a', 'flac', '-compression_level', '8',
                    temp_flac
                ], check=True)
                temp_files.append(temp_flac)
                current_file = temp_flac
            else:
                # 如果是 flac，直接使用
                current_file = audio_file
            
            inputs.extend(['-i', current_file])
            filter_parts.append(f'[{i}:0]')
        
        # 构建 filter_complex 字符串
        filter_complex = f"{''.join(filter_parts)}concat=n={len(audio_files)}:v=0:a=1[out]"
        
        # 使用 ffmpeg 进行拼接
        cmd = ['ffmpeg', '-y']  # -y 覆盖已存在的输出文件
        cmd.extend(inputs)
        cmd.extend(['-filter_complex', filter_complex, '-map', '[out]', output_file])
        
        log.info('开始拼接音频文件...')
        subprocess.run(cmd, check=True)
        
        # 清理临时文件
        if temp_files:
            log.info('清理临时文件...')
            for temp_file in temp_files:
                os.remove(temp_file)
            os.rmdir(temp_dir)
        
        log.info(f'成功拼接文件到: "{output_file}"')
        return True
        
    except subprocess.CalledProcessError as e:
        log.error(f'拼接文件失败: {str(e)}')
        return False
    except Exception as e:
        log.error(f'拼接过程中发生错误: {str(e)}')
        return False
    finally:
        # 确保临时目录被清理
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def dump(*paths, n_workers=None, merge=False, output_file='merged.flac'):
    """
    转换并可选择性地合并文件
    :param paths: 输入路径
    :param n_workers: 并行工作进程数
    :param merge: 是否合并转换后的文件
    :param output_file: 合并后的输出文件名
    """
    header = dedent(r'''
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
    ''')
    for line in header.split('\n'):
        log.info(line)

    converted_files = []
    all_filepaths = [fp for p in paths for fp in list_filepaths(p)]
    
    if n_workers > 1:
        log.info(f'使用{n_workers}个并行进程运行pyNCMDUMP')
        with Pool(processes=n_workers) as p:
            converted_files = list(filter(None, p.map(dump_single_file, all_filepaths)))
    else:
        log.info('使用单进程模式运行pyNCMDUMP')
        for fp in tqdm(all_filepaths, leave=False):
            result = dump_single_file(fp)
            if result:
                converted_files.append(result)
    
    if merge and converted_files:
        # 现在支持所有音频文件
        audio_files = [f for f in converted_files if f.endswith(('.flac', '.mp3'))]
        if audio_files:
            if check_ffmpeg():
                merge_audio_files(audio_files, output_file)
        else:
            log.warning("未找到可以拼接的音频文件")
    
    log.info('所有操作已完成')


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description='pyNCMDUMP命令行工具')
    parser.add_argument(
        'paths',
        metavar='paths',
        type=str,
        nargs='+',
        help='一个或多个源文件路径'
    )
    parser.add_argument(
        '-w', '--workers',
        metavar='',
        type=int,
        help='并行转换时的工作进程数（默认：1）',
        default=1
    )
    parser.add_argument(
        '-m', '--merge',
        action='store_true',
        help='合并所有转换后的.flac文件'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='merged.flac',
        help='指定合并后的输出文件名（默认：merged.flac）'
    )
    
    args = parser.parse_args()
    dump(*args.paths, n_workers=args.workers, merge=args.merge, output_file=args.output)

#!/usr/bin/env python2

from lxml import etree
from pprint import pprint
import argparse
import os
import re
import subprocess
import tempfile
import traceback

try:
    # for mypy
    from typing import * # NOQA (for flake8)
except:
    pass

def video_info(video_file):
    # type: (str) -> dict
    data = {
        'error': False,
        'output': '',
        } # type: Dict[str, Any]

    cmd = [
        'MP4Box',
        '-info',
        video_file,
    ]
    output = ''
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        data['output'] += output
        regex = re.compile(r'RFC6381 Codec Parameters: (.+)$', re.MULTILINE)
        codec_params = regex.findall(output)
        if not codec_params:
            print '%s: MP4Box failure' % video_file
            data['error'] = True
            return data
        for codec_param in codec_params:
            if codec_param.startswith('mp4a'):
                data['audio_codec_id'] = codec_param
            elif codec_param.startswith('avc') or codec_param.startswith('mp4v'):
                data['video_codec_id'] = codec_param
        if 'video_codec_id' not in data:
            print '%s: could not get video_codec_id' % video_file
            data['error'] = True
            return data
        if 'audio_codec_id' not in data:
            if len(codec_params) > 1:
                print '%s: could not get audio_codec_id' % video_file
                data['error'] = True
                return data
            else:
                # file without audio track
                data['audio_codec_id'] = ''
    except:
        pprint([traceback.format_exc(), output])
        data['error'] = True
        return data

    cmd = [
        'mediainfo',
        '-f',
        '--Output=XML',
        video_file,
    ]
    output = ''
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        data['output'] += output
        # lxml's XML parsing is broken with mediainfo-17.10, so use HTML instead
        # the downside is that the tag names are modified by the parser
        root = etree.HTML(output)
        general = root.xpath('//track[@type="General"]')[0]
        for bitrate in general.findall('overallbitrate'):
            if ' ' not in bitrate.text:
                data['bitrate'] = bitrate.text
        if 'bitrate' not in data:
            print '%s: could not get bitrate' % video_file
            data['error'] = True
            return data
        for framerate in general.findall('framerate'):
            if ' ' not in framerate.text:
                data['framerate'] = framerate.text
        if 'framerate' not in data:
            print '%s: could not get framerate' % video_file
            data['error'] = True
            return data

        video = root.xpath('//track[@type="Video"]')[0]
        for width in video.findall('width'):
            if ' ' not in width.text:
                data['width'] = width.text
        if 'width' not in data:
            print '%s: could not get width' % video_file
            data['error'] = True
            return data
        for height in video.findall('height'):
            if ' ' not in height.text:
                data['height'] = height.text
        if 'height' not in data:
            print '%s: could not get height' % video_file
            data['error'] = True
            return data

        return data
    except:
        print traceback.format_exc()
        pprint(output)
        data['error'] = True
        return data

def convert_to_mp4(in_name, out_name, height=None):
    # type: (str, str, int) -> Dict[str, Any]
    data = {
        'error': False,
        'output': '',
        } # type: Dict[str, Any]
    cmd = [
        'ffmpeg', '-y', '-i', in_name,
        '-c:a', 'libfdk_aac',
        '-vbr', '3',
        '-c:v', 'libx264',
        '-crf', '25',
        #'-threads', '4',
        '-movflags', 'faststart',
        '-profile:v', 'baseline',
        '-ar', '44100',
        out_name,
    ]
    if height is not None:
        for param in ['-sws_flags', 'lanczos', '-vf', 'scale=-2:%d' % height]:
            cmd.insert(-1, param)
    try:
        data['output'] += subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except:
        data['error'] = True
        pprint(traceback.format_exc(), data['output'])
    return data

def generate_ts_and_m3u8(source_name, ts_name, m3u8_obj):
    # type: (str, str, IO) -> Dict[str, Any]
    """
    ffmpeg-3.4 would actually write to m3u8_obj.name + '.tmp', then move that file over m3u8_obj.name
    messing with NamedTemporaryFile's delete-on-close behavior. Avoid this by introducing our own temp file.
    """
    data = {
        'error': False,
        'output': '',
        } # type: Dict[str, Any]
    tmpf = tempfile.NamedTemporaryFile(suffix='.m3u8')
    cmd = [
        'ffmpeg', '-y', '-i', source_name,
        '-hls_time', '10',
        '-hls_list_size', '10',
        '-hls_flags', 'single_file',
        '-hls_segment_filename', ts_name,
        '-c', 'copy', tmpf.name,
    ]
    try:
        data['output'] += subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except:
        data['error'] = True
        print traceback.format_exc()
        pprint(data['output'])
    with open(tmpf.name, 'rb') as t:
        m3u8_obj.write(t.read())
    tmpf.close()
    return data

def write_entry_to_master_m3u8(master_obj, data, individual_m3u8_name):
    # type: (IO, Dict[str, Any], str) -> None
    master_obj.write('#EXT-X-STREAM-INF:AVERAGE-BANDWIDTH=%(bitrate)s,BANDWIDTH=%(bitrate)s,CODECS="%(audio_codec_id)s,%(video_codec_id)s",RESOLUTION=%(width)sx%(height)s,FRAME-RATE=%(framerate)s\n' % data)
    master_obj.write('%s\n' % individual_m3u8_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='E.g.: ./%(prog)s video.mkv 720 480')
    parser.add_argument('in_file', help='input video file')
    parser.add_argument('height', type=int, nargs='*', help='resize the video to these heights and add them to the master HLS list')
    args = parser.parse_args()

    if args.in_file.lower().endswith('.mp4'):
        orig_mp4_name = args.in_file
    else:
        orig_mp4_name = re.sub(r'\.[^.]+$', '.mp4', args.in_file)

    # the master HLS playlist will have the same name as the input file, with a different extension
    master_m3u8_name = re.sub(r'\.[^.]+$', '.m3u8', orig_mp4_name)
    streams = [(
        None,
        orig_mp4_name,
        re.sub(r'\.[^.]+$', '_orig.ts', orig_mp4_name),
        re.sub(r'\.[^.]+$', '_orig.m3u8', orig_mp4_name)
    )] # type: List[Tuple[int, str, str, str]]
    for height in args.height:
        streams.append((
            height,
            re.sub(r'\.[^.]+$', '_%dp.mp4' % height, orig_mp4_name),
            re.sub(r'\.[^.]+$', '_%dp.ts' % height, orig_mp4_name),
            re.sub(r'\.[^.]+$', '_%dp.m3u8' % height, orig_mp4_name)
        ))
    with open(master_m3u8_name, 'wb') as master_m3u8:
        master_m3u8.write('#EXTM3U\n')
        for height, mp4_name, ts_name, m3u8_name in streams:
            if height is not None or mp4_name != args.in_file:
                # MP4Box only works properly with mp4 files
                data = convert_to_mp4(args.in_file, mp4_name, height)
                if data['error']:
                    pprint(data)
                    exit(1)
            with open(m3u8_name, 'wb') as m3u8:
                data = generate_ts_and_m3u8(mp4_name, ts_name, m3u8)
                if data['error']:
                    pprint(data)
                    exit(1)
            data = video_info(mp4_name)
            if data['error']:
                pprint(data)
                exit(1)
            write_entry_to_master_m3u8(master_m3u8, data, m3u8_name)
            # the intermediary mp4 files are no longer needed, so we might as well delete them
            if mp4_name != args.in_file:
                os.remove(mp4_name)


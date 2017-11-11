## description

generate\_HLS.py is a proof-of-concept HLS v4 playlist generator used to
demonstrate the steps needed to produce all the fields in the master m3u8 file.

## usage

This will generate additional 720p and 480p streams from video.mp4, the
corresponding .ts and .m3u8 files and a master playlist in video.m3u8:

```sh
./generate_HLS.py video.mp4 720 480
```

You're supposed to adapt the code to your own needs. Be aware that HLS v4
byteranges require your file server to accept the "HEAD" and "OPTIONS" HTTP
headers, besides the usual "GET" requests. Switching to HLS v3 and its myriad
of little files can be done by removing the "-hls\_flags single\_file" ffmpeg
option.

You might also want to change the audio quality for lower resolution streams,
if the bitrate reduction from the video alone is not enough for your needs.

## requirements

- [ffmpeg][1] (tested with 3.4)
- MP4Box from [gpac][2] (tested with 0.7.1)
- [mediainfo][3] (tested with 17.10)

## license

generate\_HLS.py is licensed under BSD-2. See the included file LICENSE for
details.

## homepage

https://github.com/stefantalpalaru/generate_HLS

## similar projects

- [HLS-Stream-Creator][4] - a Bash script

[1]: http://ffmpeg.org/
[2]: http://gpac.wp.mines-telecom.fr/
[3]: https://mediaarea.net/en/MediaInfo
[4]: https://github.com/bentasker/HLS-Stream-Creator


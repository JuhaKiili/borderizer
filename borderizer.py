from PIL import Image, ImageSequence
import argparse
import glob
import os
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('files', type=str, default=['*.png','*.gif'], nargs='+', help='Which files to borderize. Can use wildcards like *.png.')
parser.add_argument('--rgb', nargs='+', default=['0','0','0'], help='Border color. RGB values as 0-255.')
parser.add_argument('--postfix', type=str, default='brdr', help='Postfix for output filenames.')
args = parser.parse_args()

def generate_gif(input, output, fps, scale=None, speed=1, start=None, length=None, n_colors=256, scale_algo='lanczos'):
    palette_png = tempfile.mktemp(suffix='.png')
    filter_string = ','.join(filter(None, [
        ('scale=%s:flags=%s' % (scale, scale_algo) if scale else None),
        ('setpts=\'%.2f*PTS\'' % (1 / speed) if speed != 1 else None),
        'fps=%d' % fps,
    ]))
    pre_input_args = []
    if start:
        pre_input_args.extend(['-ss', start])
    if length:
        pre_input_args.extend(['-t', length])

    subprocess.check_call(['ffmpeg'] + pre_input_args + [
        '-i', input,
        '-vf', '%s,palettegen=max_colors=%d' % (filter_string, n_colors),
        palette_png,
    ])
    subprocess.check_call(['ffmpeg'] + pre_input_args + [
        '-i', input,
        '-i', palette_png,
        '-filter_complex', '%s[x];[x][1:v]paletteuse=diff_mode=rectangle' % filter_string,
        '-f', 'gif',
        output,
    ])
    os.unlink(palette_png)

def borderize(path):
    old_image = Image.open(path)

    if ".gif" in path:
        mypalette = old_image.getpalette()
        frames = []
        duration = 0
        try:
            while 1:
                old_image.putpalette(mypalette)
                new_frame = Image.new("RGB", old_image.size)
                new_frame.paste(old_image)
                duration += old_image.info['duration']
                frames.append(new_frame)
                old_image.seek(old_image.tell() + 1)

        except EOFError:
            pass # end of sequence
    else:
        frames = [old_image]

    new_frames = []

    for frame in frames:
        pixels = frame.load()

        R = int(args.rgb[0])
        G = int(args.rgb[1])
        B = int(args.rgb[2])
        for x in range(frame.size[0]):
            pixels[x, 0] = R, G, B
            pixels[x, frame.size[1]-1] = R, G, B
        for y in range(frame.size[1]):
            pixels[0, y] = R, G, B
            pixels[frame.size[0]-1, y] = R, G, B

        new_frames.append(frame)

    output_path = "{0}_{2}.{1}".format(*path.rsplit('.', 1) + [args.postfix])

    if len(new_frames) > 1:
        os.makedirs("tmp")

        index=0
        for fr in new_frames:
            fr.save("tmp/frame_%05d.png" % index)
            index += 1

        generate_gif('./tmp/frame_%05d.png', output_path, len(new_frames) / duration * 1000)
        subprocess.call(['rm', '-rf', './tmp'])
    else:
        new_frames[0].save(output_path)

for item in args.files:
    if "*" in item:
        for f in glob.glob(item):
            borderize(f)
    else:
        borderize(item)


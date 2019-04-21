# -*- coding: utf-8 -*- 
import Image,ImageDraw
def add_corners(im,rad=None,boxed=True):
    w, h = im.size
    if not rad:
        rad=w/15
    rad=rad<6 and 6 or rad
    if boxed:
        w=w+rad*2
        h=h+rad*2
        _im=Image.new('RGB', (w,h),(255,255,255))
        _im.paste(im,(rad,rad))
        im=_im
    
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
    alpha = Image.new('L', im.size, 255)
    
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    
    return im